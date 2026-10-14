"""Real fixture inference, raw predictions, and reproducible comparison graphs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import json
import platform
from datetime import datetime, timezone
from time import perf_counter

import numpy as np

from app.config import CONTRADICTION_THRESHOLD, NLI_MODEL, SUPPORT_THRESHOLD
from app.ml import infer_relations

ROOT = Path(__file__).resolve().parents[1]
LABELS = ["supported", "contradicted", "insufficient"]


def classify(scores):
    if scores.get("contradiction", 0) >= CONTRADICTION_THRESHOLD:
        return "contradicted"
    if scores.get("entailment", 0) >= SUPPORT_THRESHOLD:
        return "supported"
    return "insufficient"


def main():
    source = ROOT / "research/fixtures.json"
    examples = json.loads(source.read_text())["examples"]
    started = perf_counter()
    scores = infer_relations([(x["evidence"], x["claim"]) for x in examples])
    elapsed = (perf_counter() - started) * 1000
    predictions = [dict(x, prediction=classify(s), scores=s) for x, s in zip(examples, scores)]
    matrix = [
        [
            sum(p["label"] == truth and p["prediction"] == predicted for p in predictions)
            for predicted in LABELS
        ]
        for truth in LABELS
    ]
    rows = []
    for label in LABELS:
        tp = sum(p["label"] == label and p["prediction"] == label for p in predictions)
        predicted = sum(p["prediction"] == label for p in predictions)
        actual = sum(p["label"] == label for p in predictions)
        precision = tp / predicted if predicted else 0
        recall = tp / actual if actual else 0
        rows.append(
            {
                "label": label,
                "precision": precision,
                "recall": recall,
                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
                "n": actual,
            }
        )
    result = {
        "status": "complete",
        "evaluation_type": "authored_diagnostic_fixture",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(examples),
        "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "model": NLI_MODEL,
        "thresholds": {
            "support": SUPPORT_THRESHOLD,
            "contradiction": CONTRADICTION_THRESHOLD,
        },
        "macro_f1": sum(x["f1"] for x in rows) / 3,
        "per_class": rows,
        "confusion_matrix": matrix,
        "label_order": LABELS,
        "wall_ms_including_model_load": elapsed,
        "hardware": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "device": "CPU, one ONNX thread",
        },
        "predictions": predictions,
        "failures": [p for p in predictions if p["label"] != p["prediction"]],
        "limitations": [
            "Small, authored, non-blinded diagnostic fixture; not a held-out benchmark.",
            "This measures NLI labels, not full RAG answer quality or hallucination reduction.",
            "No confidence interval is reported: this convenience set is not a representative random sample.",
        ],
    }
    out = ROOT / "research/results"
    out.mkdir(exist_ok=True)
    (out / "fixture_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    x = np.arange(3)
    for offset, key, color in [
        (-0.23, "precision", "#b4a9db"),
        (0, "recall", "#8270bd"),
        (0.23, "f1", "#453659"),
    ]:
        axes[0].bar(
            x + offset,
            [r[key] for r in rows],
            width=0.22,
            label=key.capitalize(),
            color=color,
        )
    axes[0].set_xticks(x, LABELS)
    axes[0].set_ylim(0, 1.1)
    axes[0].set_ylabel("Score")
    axes[0].set_title("Claim classification on authored fixtures", loc="left", fontsize=12)
    axes[0].legend(loc="upper center", ncols=3, fontsize=8)
    axes[1].imshow(matrix, cmap="Purples", vmin=0)
    axes[1].set_xticks(x, LABELS, rotation=20)
    axes[1].set_yticks(x, LABELS)
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Authored label")
    axes[1].set_title("Confusion matrix", loc="left", fontsize=12)
    for i in range(3):
        for j in range(3):
            axes[1].text(
                j,
                i,
                str(matrix[i][j]),
                ha="center",
                va="center",
                color="white" if matrix[i][j] > 4 else "#403548",
            )
    fig.suptitle(
        f"VeritasAI diagnostic run | n={len(examples)} | not a research benchmark",
        fontsize=13,
    )
    fig.savefig(out / "fixture_comparison.png", dpi=180)
    fig.savefig(out / "fixture_comparison.svg")
    print(
        json.dumps(
            {
                "examples": len(examples),
                "macro_f1": result["macro_f1"],
                "failures": len(result["failures"]),
                "milliseconds": round(elapsed),
            }
        )
    )


if __name__ == "__main__":
    main()
