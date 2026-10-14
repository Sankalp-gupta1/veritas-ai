"""Run against a disposable PostgreSQL database. Never run on a shared production DB."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import pipeline
from app.main import app

pytestmark = pytest.mark.skipif(
    not os.getenv("VERITAS_INTEGRATION_TEST"),
    reason="Set VERITAS_INTEGRATION_TEST=1 with a disposable test database",
)
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"X-Veritas-Request": "1"}


@pytest.fixture
def clients():
    with (
        TestClient(app, headers=HEADERS) as alice,
        TestClient(app, headers=HEADERS) as bob,
    ):
        assert alice.post("/api/workspace").status_code == 200
        assert bob.post("/api/workspace").status_code == 200
        yield alice, bob
        assert alice.delete("/api/workspace").status_code == 204
        assert bob.delete("/api/workspace").status_code == 204


def upload(client, name="cedar-trial-report.pdf"):
    return client.post(
        "/api/documents",
        files={"file": (name, (ROOT / "samples" / name).read_bytes(), "application/pdf")},
    )


def test_real_upload_retrieve_verify_history_delete_and_isolation(clients):
    alice, bob = clients
    created = upload(alice)
    assert created.status_code == 201, created.text
    did = created.json()["id"]
    duplicate = upload(alice)
    assert duplicate.status_code == 201 and duplicate.json()["duplicate"]
    assert len(alice.get("/api/documents").json()["documents"]) == 1
    assert bob.get("/api/documents").json()["documents"] == []
    assert bob.get(f"/api/documents/{did}/pdf").status_code == 404
    assert bob.get(f"/api/documents/{did}/pages/1").status_code == 404
    assert bob.delete(f"/api/documents/{did}").status_code == 404
    payload = {
        "question": "The Cedar trial enrolled 120 adults.",
        "document_ids": [did],
    }
    assert bob.post("/api/verify", json=payload).status_code == 404
    result = alice.post("/api/verify", json=payload)
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["claims"][0]["verdict"] == "supported", result
    citation = result["claims"][0]["citations"][0]
    page = alice.get(f"/api/documents/{did}/pages/{citation['page_number']}").json()
    assert page["text"][citation["start_offset"] : citation["end_offset"]] == citation["quote"]
    assert alice.get(f"/api/runs/{result['id']}").status_code == 200
    assert bob.get(f"/api/runs/{result['id']}").status_code == 404
    answer = alice.post(
        "/api/ask",
        json={
            "question": "How many adults were enrolled in the Cedar trial?",
            "document_ids": [did],
        },
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["answer_kind"] == "source_excerpts"
    assert not answer.json()["abstained"], answer.json()
    insufficient = alice.post(
        "/api/verify",
        json={
            "question": "The Cedar trial was funded by a pharmaceutical company.",
            "document_ids": [did],
        },
    )
    assert insufficient.json()["claims"][0]["verdict"] == "insufficient"
    assert alice.delete(f"/api/documents/{did}").status_code == 204
    assert alice.get("/api/runs").json()["runs"] == []
    assert alice.get(f"/api/documents/{did}/pdf").status_code == 404


def test_csrf_bad_upload_unknown_ids_and_missing_key(clients):
    alice, bob = clients
    assert alice.post("/api/workspace", headers={"X-Veritas-Request": ""}).status_code == 403
    assert (
        alice.post("/api/workspace", headers={"Origin": "https://attacker.example"}).status_code
        == 403
    )
    assert (
        alice.post(
            "/api/documents",
            files={"file": ("fake.pdf", b"not pdf", "application/pdf")},
        ).status_code
        == 422
    )
    did = upload(alice).json()["id"]
    result = alice.post(
        "/api/ask",
        json={
            "question": "How many adults were enrolled in the Cedar trial?",
            "document_ids": [did],
            "provider": "gemini",
        },
    )
    assert result.status_code == 422
    assert "API key" in result.json()["detail"]
    assert alice.get("/api/runs").json()["runs"] == []
    assert alice.get(f"/api/documents/{did}/pages/900").status_code == 404


def test_comparison_reuses_draft_and_withholds_invented_citation(clients, monkeypatch):
    """A controlled generator tests the experiment wiring, not provider quality."""
    alice, _ = clients
    did = upload(alice).json()["id"]
    calls = []

    def controlled_generator(question, context, provider, key, model):
        calls.append([p["id"] for p in context])
        passage = next(p for p in context if "120 adults" in p["text"])
        return [
            {
                "text": "The Cedar trial enrolled 120 adults.",
                "citations": [{"chunk_id": passage["id"], "quote": passage["text"]}],
            },
            {
                "text": "The Cedar trial enrolled 900 adults.",
                "citations": [
                    {"chunk_id": passage["id"], "quote": "The trial enrolled 900 adults."}
                ],
            },
        ], {"provider": "controlled-test", "model": "authored-test-output", "usage": {}}

    monkeypatch.setattr(pipeline, "generate", controlled_generator)
    response = alice.post(
        "/api/compare",
        json={
            "question": "How many adults were enrolled in the Cedar trial?",
            "document_ids": [did],
            "provider": "gemini",
        },
    )
    assert response.status_code == 200, response.text
    baseline, reranked, verified = response.json()["results"]
    assert len(calls) == 2
    assert [c["text"] for c in reranked["claims"]] == [c["text"] for c in verified["claims"]]
    assert reranked["evidence"] == verified["evidence"]
    assert verified["generation"]["reused_draft"] is True
    assert "900 adults" in baseline["answer"] and "900 adults" in reranked["answer"]
    assert "900 adults" not in verified["answer"]
    assert verified["claims"][0]["verdict"] == "supported"
    assert verified["claims"][1]["verdict"] == "insufficient"
    assert len(alice.get("/api/runs").json()["runs"]) == 3
