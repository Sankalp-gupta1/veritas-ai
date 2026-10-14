"""Score independently annotated experiments. Empty or invalid annotations fail closed."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from run_experiment import item_id


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def aggregate(rows):
    claims = sum(r["kept_claims"] for r in rows)
    return {
        "questions": len(rows),
        "retained_claims": claims,
        "unsupported_claim_rate": ratio(sum(r["unsupported"] for r in rows), claims),
        "citation_set_support_rate": ratio(sum(r["cited_supported"] for r in rows), claims),
        "answer_fact_coverage": ratio(
            sum(r["covered"] for r in rows), sum(r["required"] for r in rows)
        ),
        "correct_abstention_rate": ratio(
            sum(r["abstained"] and not r["answerable"] for r in rows),
            sum(not r["answerable"] for r in rows),
        ),
        "false_abstention_rate": ratio(
            sum(r["abstained"] and r["answerable"] for r in rows),
            sum(r["answerable"] for r in rows),
        ),
        "latency_p50_ms": float(np.percentile([r["latency_ms"] for r in rows], 50)),
        "latency_p95_ms": float(np.percentile([r["latency_ms"] for r in rows], 95)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    root = Path(args.directory)
    config = json.loads((root / "config.json").read_text())
    questions = {q["id"]: q for q in config["questions"]["questions"]}
    reviews = {r["item_id"]: r for r in csv.DictReader((root / "claims_for_review.csv").open())}
    runs = [
        json.loads(line) for line in (root / "predictions.jsonl").read_text().splitlines() if line
    ]
    per_variant = {v: [] for v in ["rag", "rerank", "verified"]}
    for run in runs:
        q = questions[run["question_id"]]
        kept = [
            c for c in run["claims"] if c["verdict"] in ("supported", "conflict", "not_checked")
        ]
        unsupported, cited_supported, facts = 0, 0, set()
        for claim in kept:
            row = reviews.get(item_id(run["id"], claim["id"]), {})
            if (
                row.get("gold_label") not in ("supported", "contradicted", "insufficient")
                or row.get("citation_set_supports") not in ("yes", "no")
                or not row.get("reviewer", "").strip()
            ):
                raise ValueError(
                    "Every retained claim needs independent labels, a citation judgment, and a reviewer name."
                )
            unsupported += row["gold_label"] != "supported"
            cited_supported += (
                row["citation_set_supports"] == "yes"
                and bool(claim["citations"])
                and all(c["integrity"] for c in claim["citations"])
            )
            named = {x.strip() for x in row["covered_fact_ids"].split(";") if x.strip()}
            if not named.issubset(q["facts"]):
                raise ValueError("Unknown gold fact ID.")
            if row["gold_label"] == "supported":
                facts.update(named)
        per_variant[run["variant"]].append(
            {
                "question_id": q["id"],
                "kept_claims": len(kept),
                "unsupported": unsupported,
                "cited_supported": cited_supported,
                "covered": len(facts),
                "required": len(q["facts"]),
                "answerable": q["answerable"],
                "abstained": run["abstained"],
                "latency_ms": run["latency_ms"],
            }
        )
    for variant, rows in per_variant.items():
        if len(rows) != len(questions) or {r["question_id"] for r in rows} != set(questions):
            raise ValueError("Every variant must include every question exactly once.")
        rows.sort(key=lambda r: r["question_id"])
    metrics = {variant: aggregate(rows) for variant, rows in per_variant.items()}
    # Paired resampling keeps the same questions in each comparison variant.
    rng = np.random.default_rng(42)
    differences = []
    for _ in range(2000):
        indexes = rng.integers(0, len(questions), len(questions))
        a = aggregate([per_variant["rerank"][i] for i in indexes])["unsupported_claim_rate"]
        b = aggregate([per_variant["verified"][i] for i in indexes])["unsupported_claim_rate"]
        if a is not None and b is not None:
            differences.append(b - a)
    output = {
        "variants": metrics,
        "per_question": per_variant,
        "paired_verified_minus_reranked_unsupported_rate_ci95": np.percentile(
            differences, [2.5, 97.5]
        ).tolist()
        if differences
        else None,
        "bootstrap_samples": 2000,
        "usable_bootstrap_samples": len(differences),
        "seed": 42,
        "warning": "Intervals apply to the supplied question sample. A convenience fixture does not establish external validity. Verified-variant time reuses a cached draft; do not compare it as a standalone full-pipeline latency.",
    }
    (root / "scored_metrics.json").write_text(json.dumps(output, indent=2))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for ax, key, title in [
        (axes[0], "unsupported_claim_rate", "Unsupported retained claims"),
        (axes[1], "answer_fact_coverage", "Required answer facts recovered"),
    ]:
        values = [metrics[v][key] for v in per_variant]
        ax.bar(
            list(per_variant),
            [v or 0 for v in values],
            color=["#b7a9d7", "#8c76bb", "#50405f"],
        )
        for i, value in enumerate(values):
            ax.text(i, 0.02, "N/A" if value is None else f"{value:.1%}", ha="center")
        ax.set_ylim(0, 1)
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"Independently annotated comparison | {len(questions)} questions")
    fig.savefig(root / "rag_comparison.png", dpi=180)
    print("Saved scored_metrics.json and rag_comparison.png from reviewed data.")


if __name__ == "__main__":
    main()
