"""Metric arithmetic and refusal to score missing human labels, using authored data."""

import csv
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def scorer(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "research"))
    import score_experiment

    return score_experiment


def test_abstaining_on_everything_does_not_get_perfect_factual_score(scorer):
    metrics = scorer.aggregate(
        [
            {
                "kept_claims": 0,
                "unsupported": 0,
                "cited_supported": 0,
                "covered": 0,
                "required": 2,
                "answerable": True,
                "abstained": True,
                "latency_ms": 100,
            },
            {
                "kept_claims": 0,
                "unsupported": 0,
                "cited_supported": 0,
                "covered": 0,
                "required": 0,
                "answerable": False,
                "abstained": True,
                "latency_ms": 200,
            },
        ]
    )
    assert metrics["unsupported_claim_rate"] is None
    assert metrics["citation_set_support_rate"] is None
    assert metrics["answer_fact_coverage"] == 0
    assert metrics["correct_abstention_rate"] == 1
    assert metrics["false_abstention_rate"] == 1
    assert metrics["latency_p50_ms"] == 150


def test_scorer_requires_review_then_computes_supported_fact_coverage(
    scorer, tmp_path, monkeypatch
):
    """The labels below are unit-test inputs, not human research annotations."""
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "questions": {
                    "questions": [
                        {"id": "q1", "answerable": True, "facts": {"f1": "One required fact."}}
                    ]
                }
            }
        )
    )
    runs = []
    rows = []
    for variant in ("rag", "rerank", "verified"):
        claims = [
            {
                "id": "c1",
                "verdict": "supported" if variant == "verified" else "not_checked",
                "citations": [{"integrity": True}],
            }
        ]
        runs.append(
            {
                "id": variant,
                "variant": variant,
                "question_id": "q1",
                "claims": claims,
                "abstained": False,
                "latency_ms": 10,
            }
        )
        rows.append(
            {
                "item_id": scorer.item_id(variant, "c1"),
                "gold_label": "",
                "citation_set_supports": "yes",
                "covered_fact_ids": "f1",
                "reviewer": "unit-test",
            }
        )
    (tmp_path / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in runs))

    def save_reviews():
        with (tmp_path / "claims_for_review.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    save_reviews()
    monkeypatch.setattr(sys, "argv", ["score_experiment.py", str(tmp_path)])
    with pytest.raises(ValueError, match="independent labels"):
        scorer.main()
    assert not (tmp_path / "scored_metrics.json").exists()
    for row in rows:
        row["gold_label"] = "supported"
    save_reviews()
    scorer.main()
    metrics = json.loads((tmp_path / "scored_metrics.json").read_text())
    assert metrics["variants"]["verified"]["answer_fact_coverage"] == 1
    assert metrics["variants"]["rag"]["unsupported_claim_rate"] == 0
    assert metrics["paired_verified_minus_reranked_unsupported_rate_ci95"] == [0, 0]
    assert (tmp_path / "rag_comparison.png").stat().st_size > 0
