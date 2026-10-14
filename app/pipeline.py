"""A bounded retrieve -> rerank -> draft -> verify workflow with an evidence log."""

import hashlib
from collections import Counter
from time import perf_counter
from uuid import uuid4

from .config import (
    CONTRADICTION_THRESHOLD,
    EMBEDDING_MODEL,
    NLI_MODEL,
    RERANK_MODEL,
    SUPPORT_THRESHOLD,
)
from .db import connection
from .generation import SYSTEM, generate
from .ml import embed, rerank
from .verification import check_claims, extractive_claims


def retrieve(workspace_id, question, document_ids):
    vector = embed([question])[0]
    with connection() as db:
        records = db.execute(
            """SELECT c.id,c.document_id,c.page_number,c.start_offset,c.end_offset,c.text,
                      d.name,d.sha256,p.printed_label,1-(c.embedding <=> %s) AS similarity
               FROM chunks c JOIN documents d ON d.id=c.document_id
               JOIN pages p ON p.document_id=c.document_id AND p.page_number=c.page_number
               WHERE d.workspace_id=%s AND d.id=ANY(%s::uuid[])
               ORDER BY c.embedding <=> %s LIMIT 20""",
            (vector, workspace_id, document_ids, vector),
        ).fetchall()
    return [dict(r, id=str(r["id"]), document_id=str(r["document_id"])) for r in records]


def run_pipeline(
    workspace_id,
    question,
    document_ids,
    variant="verified",
    provider="extractive",
    key=None,
    model=None,
    candidates=None,
    cached_draft=None,
):
    started = perf_counter()
    timings = {}
    stage = perf_counter()
    candidates = (
        candidates if candidates is not None else retrieve(workspace_id, question, document_ids)
    )
    timings["retrieval_ms"] = round((perf_counter() - stage) * 1000, 2)
    stage = perf_counter()
    ranked = candidates if variant == "rag" else rerank(question, candidates)
    context = ranked[:5]
    timings["rerank_ms"] = round((perf_counter() - stage) * 1000, 2)
    # Uncalibrated relevance scores are a conservative operational gate, not answer accuracy.
    relevant = bool(context)
    if provider == "extractive" and context:
        relevant = (
            context[0].get("rerank_score", 1) >= 0.0001 and context[0].get("similarity", 1) >= 0.20
        )
    stage = perf_counter()
    if cached_draft is not None:
        draft, generation = cached_draft
        generation = dict(generation, reused_draft=True)
    elif not relevant:
        draft, generation = (
            [],
            {"provider": provider, "model": "not called", "usage": {}},
        )
    elif provider == "extractive":
        draft, generation = (
            extractive_claims(context),
            {"provider": "extractive", "model": "source excerpts", "usage": {}},
        )
    else:
        draft, generation = generate(question, context, provider, key, model)
    timings["generation_ms"] = round((perf_counter() - stage) * 1000, 2)
    stage = perf_counter()
    claims = check_claims(draft, context, verify=variant == "verified")
    timings["verification_ms"] = round((perf_counter() - stage) * 1000, 2)
    kept = [c for c in claims if c["verdict"] in ("supported", "conflict", "not_checked")]
    counts = dict(Counter(c["verdict"] for c in claims))
    abstained = not kept
    result = {
        "id": str(uuid4()),
        "question": question,
        "variant": variant,
        "generation": generation,
        "answer": "\n\n".join(c["text"] for c in kept)
        if kept
        else "Available documents do not provide sufficient evidence to answer this question.",
        "answer_kind": "source_excerpts" if provider == "extractive" else "generated",
        "abstained": abstained,
        "claims": claims,
        "counts": counts,
        "evidence": context,
        "timings": timings,
        "latency_ms": round((perf_counter() - started) * 1000, 2),
        "audit": {
            "embedding_model": EMBEDDING_MODEL,
            "reranker_model": RERANK_MODEL if variant != "rag" else None,
            "verifier_model": NLI_MODEL if variant == "verified" else None,
            "prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
            "support_threshold": SUPPORT_THRESHOLD,
            "contradiction_threshold": CONTRADICTION_THRESHOLD,
            "candidate_count": len(candidates),
            "context_count": len(context),
            "corpus": [{"id": p["document_id"], "sha256": p["sha256"]} for p in context],
            "human_evaluated": False,
        },
        "notes": [
            "Checks compare claims with uploaded sources; they do not prove real-world truth.",
            "Model scores are not calibrated accuracy percentages.",
        ],
    }
    return result, (draft, generation)


def run_claim_check(workspace_id, claim, document_ids):
    """Check a user's statement with local models; no generative API is required."""
    started = perf_counter()
    candidates = retrieve(workspace_id, claim, document_ids)
    context = rerank(claim, candidates)[:5]
    draft = [
        {
            "text": claim,
            "citations": [{"chunk_id": p["id"], "quote": p["text"]} for p in context[:3]],
        }
    ]
    claims = check_claims(draft, context)
    verdict = claims[0]["verdict"] if claims else "insufficient"
    return {
        "id": str(uuid4()),
        "question": claim,
        "variant": "claim_check",
        "answer": claim
        if verdict in ("supported", "conflict")
        else "Available documents do not provide sufficient evidence to support this claim.",
        "answer_kind": "claim_check",
        "abstained": verdict not in ("supported", "conflict"),
        "claims": claims,
        "counts": dict(Counter(c["verdict"] for c in claims)),
        "evidence": context,
        "generation": {
            "provider": "local",
            "model": "user-supplied claim",
            "usage": {},
        },
        "timings": {},
        "latency_ms": round((perf_counter() - started) * 1000, 2),
        "audit": {
            "embedding_model": EMBEDDING_MODEL,
            "reranker_model": RERANK_MODEL,
            "verifier_model": NLI_MODEL,
            "human_evaluated": False,
            "support_threshold": SUPPORT_THRESHOLD,
            "contradiction_threshold": CONTRADICTION_THRESHOLD,
        },
        "notes": ["This checks source support, not real-world truth."],
    }
