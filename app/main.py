"""HTTP boundaries: private workspaces, bounded uploads, real persistence and errors."""

import hashlib
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, field_validator

from . import config
from .db import connection
from .documents import chunk_pages, extract_pdf, sha256
from .generation import ProviderError
from .ml import embed
from .pipeline import retrieve, run_claim_check, run_pipeline

logger = logging.getLogger("veritas")
app = FastAPI(
    title="VeritasAI",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
COOKIE = "veritas_workspace"


@app.middleware("http")
async def boundaries(request: Request, call_next):
    request_id = str(uuid4())
    if request.url.path == "/api/documents" and request.method == "POST":
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > config.MAX_FILE_BYTES + 100_000:
            return JSONResponse(
                {"detail": "The upload is too large. Each PDF must be at most 4 MB."},
                status_code=413,
            )
    if request.method in {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    } and request.url.path.startswith("/api/"):
        if request.headers.get("x-veritas-request") != "1":
            return JSONResponse(
                {"detail": "Please use the VeritasAI app to make this request."},
                status_code=403,
            )
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != f"{request.url.scheme}://{request.headers.get('host')}":
            # The development proxy sends the same Host header; production stays same-origin.
            return JSONResponse(
                {"detail": "This request came from an untrusted origin."},
                status_code=403,
            )
    try:
        response = await call_next(request)
    except Exception:
        # Do not log document text, provider keys, database URLs or exception strings.
        logger.error("request_failed request_id=%s path=%s", request_id, request.url.path)
        response = JSONResponse(
            {"detail": "Something went wrong. Please retry.", "request_id": request_id},
            status_code=500,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


def rate_limit(bucket, maximum=30, seconds=3600):
    window = int(time.time()) // seconds
    with connection() as db:
        count = db.execute(
            """INSERT INTO rate_limits(bucket,window_id,count) VALUES(%s,%s,1)
                ON CONFLICT(bucket,window_id) DO UPDATE SET count=rate_limits.count+1 RETURNING count""",
            (bucket, window),
        ).fetchone()["count"]
    if count > maximum:
        raise HTTPException(
            429,
            "Too many requests. Please wait before trying again.",
            headers={"Retry-After": str(seconds)},
        )


def workspace(request: Request):
    token = request.cookies.get(COOKIE, "")
    if len(token) != 64:
        raise HTTPException(401, "Open a workspace before continuing.")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        found = db.execute("SELECT id FROM workspaces WHERE token_hash=%s", (digest,)).fetchone()
    if not found:
        raise HTTPException(401, "This workspace has expired. Open a new workspace.")
    return str(found["id"])


@app.get("/api/health")
def health():
    try:
        with connection() as db:
            db.execute("SELECT 1 FROM schema_migrations LIMIT 1").fetchone()
        present = all(
            (config.MODEL_DIR / name / filename).exists()
            for name, filename in [
                ("embedding", "model.safetensors"),
                ("reranker", "model_quantized.onnx"),
                ("verifier", "model_quantized.onnx"),
            ]
        )
        return {
            "status": "ok" if present else "models_missing",
            "database": "connected",
            "models_ready": present,
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
            "ollama_available": bool(os.getenv("OLLAMA_URL")) and not config.PRODUCTION,
            "limits": {"file_mb": 4, "pages": 80, "documents": 20},
        }
    except Exception:
        return JSONResponse(
            {
                "status": "unavailable",
                "database": "not_ready",
                "detail": "The database is not ready. Please try again shortly.",
            },
            503,
        )


@app.post("/api/workspace")
def create_workspace(request: Request, response: Response):
    if request.cookies.get(COOKIE):
        try:
            return {"id": workspace(request)}
        except HTTPException:
            pass
    # A global ceiling also bounds workspace creation when IP identity is unavailable.
    rate_limit("new_workspaces", 80)
    token = secrets.token_hex(32)
    identity = str(uuid4())
    with connection() as db:
        db.execute(
            "INSERT INTO workspaces(id,token_hash) VALUES(%s,%s)",
            (identity, hashlib.sha256(token.encode()).hexdigest()),
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=config.PRODUCTION,
        samesite="strict",
        max_age=60 * 60 * 24 * 90,
        path="/",
    )
    return {"id": identity}


@app.get("/api/documents")
def list_documents(wid=Depends(workspace)):
    with connection() as db:
        rows = db.execute(
            "SELECT id,name,sha256,page_count,byte_count,created_at FROM documents WHERE workspace_id=%s ORDER BY created_at DESC",
            (wid,),
        ).fetchall()
    return {"documents": rows}


@app.post("/api/documents", status_code=201)
def upload_document(file: UploadFile = File(...), wid=Depends(workspace)):
    rate_limit(wid + ":upload", 30)
    data = file.file.read(config.MAX_FILE_BYTES + 1)
    try:
        pages = extract_pdf(data)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    digest = sha256(data)
    with connection() as db:
        existing = db.execute(
            "SELECT id FROM documents WHERE workspace_id=%s AND sha256=%s",
            (wid, digest),
        ).fetchone()
    if existing:
        return {"id": str(existing["id"]), "duplicate": True}
    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(422, "This PDF does not contain enough readable text to search.")
    if len(chunks) > 2000:
        raise HTTPException(
            422,
            "This document has too many text fragments. Split it into smaller PDFs.",
        )
    vectors = embed([c["text"] for c in chunks])
    did = str(uuid4())
    name = Path((file.filename or "Document.pdf").replace("\\", "/")).name[:180]
    with connection() as db:
        # Serialize quota checks + writes. This is a bounded research installation.
        db.execute("SELECT pg_advisory_xact_lock(81726354)")
        usage = db.execute(
            "SELECT count(*) AS n,coalesce(sum(byte_count),0) AS bytes FROM documents WHERE workspace_id=%s",
            (wid,),
        ).fetchone()
        total = db.execute("SELECT coalesce(sum(byte_count),0) AS bytes FROM documents").fetchone()[
            "bytes"
        ]
        chunk_count = db.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"]
        if (
            usage["n"] >= config.MAX_DOCUMENTS
            or usage["bytes"] + len(data) > config.MAX_WORKSPACE_BYTES
        ):
            raise HTTPException(
                413,
                "This workspace is full. Remove a document before uploading another.",
            )
        if total + len(data) > config.MAX_TOTAL_BYTES or chunk_count + len(chunks) > 20_000:
            raise HTTPException(
                507,
                "This installation has reached its storage allowance. Contact its owner.",
            )
        exists = db.execute(
            "SELECT id FROM documents WHERE workspace_id=%s AND sha256=%s",
            (wid, digest),
        ).fetchone()
        if exists:
            return {"id": str(exists["id"]), "duplicate": True}
        db.execute(
            "INSERT INTO documents(id,workspace_id,name,sha256,page_count,byte_count,pdf) VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (did, wid, name, digest, len(pages), len(data), data),
        )
        for page in pages:
            db.execute(
                "INSERT INTO pages(document_id,page_number,printed_label,text) VALUES(%s,%s,%s,%s)",
                (did, page["page_number"], page["printed_label"], page["text"]),
            )
        with db.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO chunks(id,document_id,page_number,start_offset,end_offset,text,embedding,embedding_model) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                [
                    (
                        c["id"],
                        did,
                        c["page_number"],
                        c["start_offset"],
                        c["end_offset"],
                        c["text"],
                        vector,
                        config.EMBEDDING_MODEL,
                    )
                    for c, vector in zip(chunks, vectors)
                ],
            )
    return {
        "id": did,
        "name": name,
        "pages": len(pages),
        "chunks": len(chunks),
        "warnings": [
            f"Page {p['page_number']} contains no readable text." for p in pages if not p["text"]
        ],
    }


def owned_document(db, wid, did):
    document = db.execute(
        "SELECT id,name,sha256,page_count FROM documents WHERE id=%s AND workspace_id=%s",
        (did, wid),
    ).fetchone()
    if not document:
        raise HTTPException(404, "Document not found in this workspace.")
    return document


@app.get("/api/documents/{did}/pdf")
def get_pdf(did: UUID, wid=Depends(workspace)):
    with connection() as db:
        owned_document(db, wid, did)
        data = db.execute(
            "SELECT pdf FROM documents WHERE id=%s AND workspace_id=%s", (did, wid)
        ).fetchone()["pdf"]
    return Response(
        bytes(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="document.pdf"',
            "Content-Security-Policy": "sandbox",
        },
    )


@app.get("/api/documents/{did}/pages/{page_number}")
def get_page(did: UUID, page_number: int, wid=Depends(workspace)):
    with connection() as db:
        document = owned_document(db, wid, did)
        page = db.execute(
            "SELECT page_number,printed_label,text FROM pages WHERE document_id=%s AND page_number=%s",
            (did, page_number),
        ).fetchone()
    if not page:
        raise HTTPException(404, "Page not found.")
    return {**page, "document": document}


@app.delete("/api/documents/{did}", status_code=204)
def delete_document(did: UUID, wid=Depends(workspace)):
    with connection() as db:
        db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (wid,))
        owned_document(db, wid, did)
        db.execute("DELETE FROM documents WHERE id=%s AND workspace_id=%s", (did, wid))
        # Saved evidence contains text too. Remove all workspace runs so deletion is complete.
        db.execute("DELETE FROM runs WHERE workspace_id=%s", (wid,))
    return Response(status_code=204)


@app.delete("/api/workspace", status_code=204)
def delete_workspace(response: Response, wid=Depends(workspace)):
    with connection() as db:
        db.execute("DELETE FROM workspaces WHERE id=%s", (wid,))
    response.delete_cookie(COOKIE, path="/")
    response.status_code = 204
    return response


class Question(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    document_ids: list[UUID] = Field(min_length=1, max_length=20)
    variant: Literal["rag", "rerank", "verified"] = "verified"
    provider: Literal["extractive", "gemini", "ollama"] = "extractive"
    model: str | None = Field(default=None, max_length=90)

    @field_validator("question")
    @classmethod
    def meaningful_question(cls, value):
        value = value.strip()
        if len(value) < 5 or not any(character.isalpha() for character in value):
            raise ValueError("Write a question or claim containing words.")
        return value


def validate_selection(wid, ids):
    with connection() as db:
        count = db.execute(
            "SELECT count(*) AS n FROM documents WHERE workspace_id=%s AND id=ANY(%s::uuid[])",
            (wid, ids),
        ).fetchone()["n"]
    if count != len(set(ids)):
        raise HTTPException(404, "A selected document is unavailable in your workspace.")


def save_run(wid, result):
    with connection() as db:
        if not db.execute("SELECT id FROM workspaces WHERE id=%s FOR UPDATE", (wid,)).fetchone():
            raise HTTPException(
                410, "This workspace was removed while the answer was being checked."
            )
        referenced = list({p["document_id"] for p in result.get("evidence", [])})
        if referenced:
            remaining = db.execute(
                "SELECT count(*) AS n FROM documents WHERE workspace_id=%s AND id=ANY(%s::uuid[])",
                (wid, referenced),
            ).fetchone()["n"]
            if remaining != len(referenced):
                raise HTTPException(
                    409,
                    "A source was removed while this answer was being checked. Please ask again.",
                )
        db.execute(
            "INSERT INTO runs(id,workspace_id,question,variant,result) VALUES(%s,%s,%s,%s,%s)",
            (result["id"], wid, result["question"], result["variant"], Jsonb(result)),
        )


@app.post("/api/ask")
def ask(body: Question, request: Request, wid=Depends(workspace)):
    rate_limit(wid + ":ask", 30)
    rate_limit("all_questions", 200)
    ids = [str(x) for x in body.document_ids]
    validate_selection(wid, ids)
    try:
        result, _ = run_pipeline(
            wid,
            body.question.strip(),
            ids,
            body.variant,
            body.provider,
            request.headers.get("x-gemini-key"),
            body.model,
        )
    except ProviderError as error:
        raise HTTPException(422, str(error)) from error
    save_run(wid, result)
    return result


@app.post("/api/compare")
def compare(body: Question, request: Request, wid=Depends(workspace)):
    if body.provider == "extractive":
        raise HTTPException(
            422,
            "Connect an AI model to compare RAG answers. Source excerpts are not a generative RAG baseline.",
        )
    rate_limit(wid + ":compare", 6)
    rate_limit("all_comparisons", 30)
    ids = [str(x) for x in body.document_ids]
    validate_selection(wid, ids)
    candidates = retrieve(wid, body.question, ids)
    results, cached = [], None
    try:
        for variant in ["rag", "rerank", "verified"]:
            result, draft = run_pipeline(
                wid,
                body.question,
                ids,
                variant,
                body.provider,
                request.headers.get("x-gemini-key"),
                body.model,
                candidates,
                cached_draft=cached if variant == "verified" else None,
            )
            if variant == "rerank":
                cached = draft
            results.append(result)
    except ProviderError as error:
        raise HTTPException(422, str(error)) from error
    for result in results:
        save_run(wid, result)
    return {
        "results": results,
        "notes": "Reranked and verified variants share the exact same draft. Human judgments are required before claiming quality improvements.",
    }


@app.post("/api/verify")
def verify_statement(body: Question, wid=Depends(workspace)):
    if len(body.question) > 650:
        raise HTTPException(
            422,
            "Keep your claim under 650 characters so it can be checked as one statement.",
        )
    rate_limit(wid + ":verify", 30)
    rate_limit("all_verifications", 200)
    ids = [str(x) for x in body.document_ids]
    validate_selection(wid, ids)
    result = run_claim_check(wid, body.question.strip(), ids)
    save_run(wid, result)
    return result


@app.get("/api/runs")
def runs(wid=Depends(workspace)):
    with connection() as db:
        rows = db.execute(
            "SELECT id,question,variant,created_at,result->'counts' AS counts,result->'latency_ms' AS latency_ms,result->'abstained' AS abstained FROM runs WHERE workspace_id=%s ORDER BY created_at DESC LIMIT 100",
            (wid,),
        ).fetchall()
    return {"runs": rows}


@app.get("/api/runs/{rid}")
def get_run(rid: UUID, wid=Depends(workspace)):
    with connection() as db:
        row = db.execute(
            "SELECT result FROM runs WHERE id=%s AND workspace_id=%s", (rid, wid)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Answer not found.")
    return row["result"]


@app.get("/api/research")
def research_results():
    path = config.ROOT / "research" / "results" / "fixture_metrics.json"
    return (
        json.loads(path.read_text())
        if path.exists()
        else {"status": "not_evaluated", "message": "No evaluation has been run yet."}
    )


@app.get("/api/samples")
def samples():
    manifest = config.ROOT / "samples" / "manifest.json"
    return json.loads(manifest.read_text()) if manifest.exists() else {"documents": []}


@app.get("/api/samples/{name}")
def sample_pdf(name: str):
    allowed = {p.name for p in (config.ROOT / "samples").glob("*.pdf")}
    if name not in allowed:
        raise HTTPException(404, "Sample not found.")
    return FileResponse(config.ROOT / "samples" / name, media_type="application/pdf")


frontend = config.ROOT / "frontend" / "dist"


@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def frontend_shell():
    # Always fetch the current shell. A cached shell can point to hashed bundles
    # from a previous deployment that no longer exist at the production alias.
    index = frontend / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Build the frontend before opening the website.")
    return FileResponse(index, headers={"Cache-Control": "no-store, max-age=0"})


if frontend.exists():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
