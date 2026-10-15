"""Citation integrity first, semantic support second. Keep rejected claims auditable."""

import re

from .config import CONTRADICTION_THRESHOLD, SUPPORT_THRESHOLD
from .documents import normalize
from .ml import infer_relations


def citation_for(passage, quote, relation="supports"):
    quote = normalize(quote)
    location = passage["text"].find(quote) if len(quote) >= 12 else -1
    valid = location >= 0
    return {
        "chunk_id": str(passage["id"]),
        "document_id": str(passage["document_id"]),
        "document_name": passage["name"],
        "document_sha256": passage["sha256"],
        "page_number": passage["page_number"],
        "printed_label": passage.get("printed_label"),
        "quote": quote,
        "integrity": valid,
        "relation": relation,
        "start_offset": passage["start_offset"] + location if valid else None,
        "end_offset": passage["start_offset"] + location + len(quote) if valid else None,
    }


def check_claims(claims, context, verify=True):
    by_id = {str(p["id"]): p for p in context}
    result = []
    for index, raw in enumerate(claims[:8]):
        text = normalize(str(raw.get("text", "")))[:650]
        if not text:
            continue
        citations = []
        for ref in raw.get("citations", [])[:3]:
            passage = by_id.get(str(ref.get("chunk_id", "")))
            if passage:
                citations.append(citation_for(passage, str(ref.get("quote", ""))))
            else:
                citations.append(
                    {
                        "chunk_id": str(ref.get("chunk_id", "")),
                        "quote": str(ref.get("quote", ""))[:950],
                        "integrity": False,
                        "relation": "unknown",
                        "reason": "Unknown or unselected evidence.",
                    }
                )
        verdict = "not_checked"
        evidence = []
        explanation = "Semantic verification is off for this comparison variant."
        if verify:
            valid = [c for c in citations if c["integrity"]]
            if not valid or any(not c["integrity"] for c in citations):
                verdict, explanation = (
                    "insufficient",
                    "A citation is missing or its quote does not match the retrieved page.",
                )
            else:
                relations = infer_relations([(c["quote"], text) for c in valid])
                support = max((r.get("entailment", 0) for r in relations), default=0)
                # Match the whole retrieved passage for contradictions to avoid misleading short quotes.
                other_relations = infer_relations([(p["text"], text) for p in context])
                conflicts = [
                    (p, r)
                    for p, r in zip(context, other_relations)
                    if r.get("contradiction", 0) >= CONTRADICTION_THRESHOLD
                ]
                for c, r in zip(valid, relations):
                    c["support_score"] = round(r.get("entailment", 0), 4)
                    c["relation"] = (
                        "supports"
                        if r.get("entailment", 0) >= SUPPORT_THRESHOLD
                        else "insufficient"
                    )
                if support >= SUPPORT_THRESHOLD and conflicts:
                    verdict, explanation = (
                        "conflict",
                        "Possible disagreement found. Check population, date and context before treating these as contradictory findings.",
                    )
                elif support >= SUPPORT_THRESHOLD:
                    verdict, explanation = (
                        "supported",
                        "The cited text supports this claim according to the local language model. Please review the evidence.",
                    )
                elif conflicts:
                    verdict, explanation = (
                        "contradicted",
                        "Retrieved text appears to contradict this claim. It has been withheld from the answer.",
                    )
                else:
                    verdict, explanation = (
                        "insufficient",
                        "The cited text does not provide strong enough support for this claim.",
                    )
                for p, relation in conflicts[:2]:
                    item = citation_for(p, p["text"], "contradicts")
                    item["contradiction_score"] = round(relation["contradiction"], 4)
                    evidence.append(item)
        result.append(
            {
                "id": f"c{index + 1}",
                "text": text,
                "verdict": verdict,
                "explanation": explanation,
                "citations": citations,
                "counter_evidence": evidence,
            }
        )
    return result


def extractive_claims(context):
    """Return source excerpts without pretending they are generated explanations."""
    claims = []
    for p in context[:3]:
        sentences = re.split(r"(?<=[.!?])\s+", p["text"])
        quote = next((s for s in sentences if 35 < len(s) <= 500), p["text"][:500])
        claims.append({"text": quote, "citations": [{"chunk_id": str(p["id"]), "quote": quote}]})
    return claims


def claim_check_draft(claim, context):
    """Find exact supporting sentences without discarding surrounding counterevidence.

    A whole paragraph can confuse the NLI model when it describes several groups.
    Rank bounded sentence quotes for support; check_claims still checks every full
    retrieved passage for contradiction. No threshold is lowered for this path.
    """
    candidates = []
    for passage in context[:5]:
        sentences = re.split(r"(?<=[.!?])\s+", passage["text"])
        quotes = [s for s in sentences[:12] if len(s) >= 20]
        for quote in quotes or [passage["text"]]:
            candidates.append({"chunk_id": passage["id"], "quote": quote})
    relations = infer_relations([(item["quote"], claim) for item in candidates])
    ranked = sorted(
        zip(candidates, relations), key=lambda item: item[1].get("entailment", 0), reverse=True
    )
    return [{"text": claim, "citations": [item for item, _ in ranked[:3]]}]
