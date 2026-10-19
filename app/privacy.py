"""Server-enforced disclosure review and content-free privacy receipts."""

import hashlib
import json
import re
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import vault
from .auth import current_account, profile, workspace
from .db import connection
from .ml import rerank
from .security import audit, rate_limit, token_hash

router = APIRouter(prefix="/api/privacy", tags=["Privacy"])


class Preferences(BaseModel):
    cloud_enabled: bool
    save_history: bool


def preferences(wid):
    with connection() as db:
        return db.execute("SELECT cloud_enabled,save_history,privacy_version FROM workspaces WHERE id=%s", (wid,)).fetchone()


def require_cloud(wid):
    pref = preferences(wid)
    if not pref or not pref["cloud_enabled"]:
        raise HTTPException(403, "External AI is blocked. Enable it in Privacy center only if you want to review and share selected text with Google.")
    return pref


@router.get("")
def status(account=Depends(current_account)):
    wid = account["workspace_id"]
    with connection() as db:
        totals = db.execute("SELECT count(*) AS documents,coalesce(sum(byte_count),0) AS bytes,count(*) FILTER(WHERE NOT encrypted) AS legacy_documents FROM documents WHERE workspace_id=%s", (wid,)).fetchone()
        runs = db.execute("SELECT count(*) AS answers,count(*) FILTER(WHERE NOT encrypted) AS legacy_answers FROM runs WHERE workspace_id=%s", (wid,)).fetchone()
        sessions = db.execute("SELECT count(*) AS n FROM sessions WHERE account_id=%s AND expires_at>now() AND last_seen>now()-interval '30 minutes'", (account["id"],)).fetchone()["n"]
        events = db.execute("SELECT id,event,created_at FROM privacy_events WHERE workspace_id=%s AND created_at>now()-interval '30 days' ORDER BY created_at DESC LIMIT 30", (wid,)).fetchall()
    return {
        "account": profile(account), "storage": {**totals, **runs},
        "active_sessions": sessions, "events": events,
        "vault_configured": vault.configured(),
        "encrypted_content": totals["legacy_documents"] == 0 and runs["legacy_answers"] == 0,
        "end_to_end_encrypted": False,
        "limits": [
            "The app server decrypts your documents to search and verify evidence.",
            "Search vectors, file sizes, page numbers and timestamps are database metadata, not application-encrypted.",
            "Automatic masking can miss names, addresses and other sensitive details. Review every external-AI preview.",
            "Deleting active data does not instantly remove provider backups or data already sent to Google.",
        ],
    }


@router.put("/preferences")
def update_preferences(body: Preferences, wid=Depends(workspace)):
    with connection() as db:
        db.execute("UPDATE workspaces SET cloud_enabled=%s,save_history=%s,privacy_version=privacy_version+1 WHERE id=%s", (body.cloud_enabled, body.save_history, wid))
        db.execute("DELETE FROM disclosure_consents WHERE workspace_id=%s", (wid,))
        audit(db, wid, "external_ai_enabled" if body.cloud_enabled else "external_ai_blocked")
        audit(db, wid, "answer_history_enabled" if body.save_history else "answer_history_disabled")
    return {"cloud_enabled": body.cloud_enabled, "save_history": body.save_history}


@router.delete("/history", status_code=204)
def clear_history(wid=Depends(workspace)):
    with connection() as db:
        db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (wid,))
        db.execute("DELETE FROM runs WHERE workspace_id=%s", (wid,))
        audit(db, wid, "answer_history_deleted")


@router.get("/export")
def export_data(account=Depends(current_account)):
    wid = str(account["workspace_id"])
    rate_limit(wid + ":export", 6)
    with connection() as db:
        documents = db.execute("SELECT id,name,page_count,byte_count,created_at,encrypted FROM documents WHERE workspace_id=%s", (wid,)).fetchall()
        runs = db.execute("SELECT id,question,result,encrypted FROM runs WHERE workspace_id=%s ORDER BY created_at", (wid,)).fetchall()
        pages = db.execute("SELECT p.*,d.encrypted FROM pages p JOIN documents d ON d.id=p.document_id WHERE d.workspace_id=%s ORDER BY p.document_id,p.page_number", (wid,)).fetchall()
        audit(db, wid, "data_exported")
    for doc in documents:
        if doc.pop("encrypted"):
            doc["name"] = vault.unseal_text(doc["name"], f"{wid}:document:{doc['id']}:name")
        doc["pdf_download"] = f"/api/documents/{doc['id']}/pdf"
    for page in pages:
        if page.pop("encrypted"):
            page["text"] = vault.unseal_text(page["text"], f"{wid}:page:{page['document_id']}:{page['page_number']}")
    answers = []
    for run in runs:
        answers.append(json.loads(vault.unseal_text(run["result"]["sealed"], f"{wid}:run:{run['id']}:result")) if run["encrypted"] else run["result"])
    return {"account": profile(account), "documents": documents, "pages": pages, "answers": answers,
            "note": "This export contains private text. PDF download links require your signed-in account. Keep downloaded files safe."}


# Mask obvious identifiers and secrets, not every conceivable personal detail.
PATTERNS = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("API_KEY", re.compile(r"\b(?:AIza[\w-]{25,}|sk-[\w-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b")),
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("PHONE", re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}|[6-9]\d{9})(?!\w)")),
    ("SECRET", re.compile(r"(?i)\b(?:password|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[\"']?[^\s\"',;]{6,}")),
]


def prepare_disclosure(question, candidates, operation, variant="verified"):
    """Return the EXACT user/evidence text that generation will send (plus static instructions)."""
    contexts = {"rag": candidates[:5], "rerank": rerank(question, candidates)[:5]}
    contexts["verified"] = contexts["rerank"]
    variants = ["rag", "rerank"] if operation == "compare" else [variant]
    material = question + "".join(p["text"] for v in variants for p in contexts[v])
    prefix = "VPRIVATE_" + hashlib.sha256(material.encode()).hexdigest()[:12]
    while prefix in material:
        prefix += "X"
    restoration, seen, counts = {}, {}, {}

    def redact(text):
        for category, pattern in PATTERNS:
            def replace(match):
                original = match.group()
                key = (category, original)
                if key not in seen:
                    placeholder = f"[{prefix}_{category}_{len(seen)+1}]"
                    seen[key] = placeholder
                    restoration[placeholder] = original
                    counts[category] = counts.get(category, 0) + 1
                return seen[key]
            text = pattern.sub(replace, text)
        return text

    redacted_question = redact(question)
    sources, outgoing = {}, {}
    for v in variants:
        outgoing[v] = []
        for p in contexts[v]:
            source = sources.setdefault(p["document_id"], f"Source {len(sources)+1}")
            outgoing[v].append({**p, "name": source, "text": redact(p["text"])})
    if operation == "compare":
        outgoing["verified"] = outgoing["rerank"]
    payloads = [{"method": v, "question": redacted_question, "evidence": [
        {"chunk_id": p["id"], "source": p["name"], "text": p["text"]} for p in outgoing[v]
    ]} for v in variants]
    return {"contexts": contexts, "outgoing": outgoing, "question": redacted_question,
            "restore": restoration, "payloads": payloads, "masked": counts}


def disclosure_digest(body, operation, prepared, pref):
    value = {"question": body.question, "documents": sorted(str(x) for x in body.document_ids),
             "model": body.model, "provider": body.provider, "variant": body.variant,
             "operation": operation, "privacy_version": pref["privacy_version"],
             "payloads": prepared["payloads"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def issue_consent(wid, digest):
    token = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute("DELETE FROM disclosure_consents WHERE workspace_id=%s", (wid,))
        db.execute("INSERT INTO disclosure_consents(token_hash,workspace_id,payload_digest,expires_at) VALUES(%s,%s,%s,now()+interval '10 minutes')", (token_hash(token), wid, digest))
    return token


def consume_consent(wid, token, digest):
    with connection() as db:
        row = db.execute("""UPDATE disclosure_consents SET used=true
                            WHERE token_hash=%s AND workspace_id=%s AND payload_digest=%s
                            AND expires_at>now() AND NOT used RETURNING token_hash""",
                         (token_hash(token or ""), wid, digest)).fetchone()
        if not row:
            raise HTTPException(409, "Review the current disclosure preview before sending this request. Previews expire after 10 minutes and can be used once.")
        audit(db, wid, "external_ai_disclosure_approved")


def restore_draft(draft, replacements):
    def restore(text):
        # Later patterns can mask a field that already contains an earlier token.
        # Restore outside-in so the exact original quote is recovered.
        for placeholder, original in reversed(list(replacements.items())):
            text = text.replace(placeholder, original)
        return text
    return [{**claim, "text": restore(claim["text"]), "citations": [
        {**citation, "quote": restore(citation["quote"])} for citation in claim["citations"]
    ]} for claim in draft]
