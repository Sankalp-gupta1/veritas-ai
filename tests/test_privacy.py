"""Adversarial checks for stored content, masking, disclosure and auth boundaries."""

import base64
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient

from app import privacy, vault
from app.auth import COOKIE, LEGACY_COOKIE, password_matches, validate_password
from app.db import connection
from app.main import app
from app.security import token_hash
from pydantic import SecretStr

HEADERS = {"X-Veritas-Request": "1"}
PASS = "fictional account passphrase for tests!"
integration = pytest.mark.skipif(not os.getenv("VERITAS_INTEGRATION_TEST"), reason="Disposable PostgreSQL database required")


def credentials(email=None, password=PASS):
    return {"email": email or f"test-{uuid4().hex}@example.com", "password": password, "confirm_password": password}


def test_authenticated_encryption_is_random_and_bound_to_row():
    clear = b"private content: do not store in plaintext"
    first = vault.seal(clear, "alice:document:1")
    second = vault.seal(clear, "alice:document:1")
    assert first != second and clear not in first
    assert vault.unseal(first, "alice:document:1") == clear
    with pytest.raises(InvalidTag):
        vault.unseal(first, "bob:document:1")
    with pytest.raises(InvalidTag):
        vault.unseal(first[:-1] + bytes([first[-1] ^ 1]), "alice:document:1")


def test_encryption_fails_closed_without_valid_key(monkeypatch):
    monkeypatch.delenv("VERITAS_VAULT_KEY")
    assert not vault.configured()
    with pytest.raises(RuntimeError):
        vault.seal(b"sensitive", "record")
    monkeypatch.setenv("VERITAS_VAULT_KEY", base64.b64encode(b"short").decode())
    assert not vault.configured()


def test_disclosure_masks_pii_and_names_but_preserves_research_numbers(monkeypatch):
    monkeypatch.setattr(privacy, "rerank", lambda q, rows: rows)
    original = "The 120 adults improved by 12 points in 2024. Contact alice@example.com or 9876543210. api_key=SecretThing12345 access_token=sk-abcdefghijklmnopqrstuvwxyz0123456789"
    evidence = [{"id": "chunk-1", "document_id": "doc-1", "name": "Alice private diagnosis.pdf", "text": original}]
    result = privacy.prepare_disclosure("Can alice@example.com confirm the result?", evidence, "ask")
    payload = json.dumps(result["payloads"])
    for private in ("alice@example.com", "9876543210", "SecretThing12345", "Alice private diagnosis.pdf"):
        assert private not in payload
    assert "120 adults" in payload and "12 points in 2024" in payload
    assert result["payloads"][0]["evidence"][0]["source"] == "Source 1"
    masked = result["outgoing"]["verified"][0]["text"]
    restored = privacy.restore_draft([{"text": masked, "citations": [{"chunk_id": "chunk-1", "quote": masked}]}], result["restore"])
    assert restored[0]["text"] == original and restored[0]["citations"][0]["quote"] == original
    assert privacy.prepare_disclosure("Can alice@example.com confirm the result?", evidence, "ask")["payloads"] == result["payloads"]


def test_validation_errors_never_echo_credentials():
    with TestClient(app, headers=HEADERS) as client:
        secret = "a-secret-that-must-not-appear-in-errors"
        response = client.post("/api/auth/register", json={"email": "not-an-email", "password": secret, "confirm_password": secret})
        assert response.status_code == 422
        assert secret not in response.text and "not-an-email" not in response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert "script-src 'self'" in response.headers["content-security-policy"]


@integration
def test_register_confirm_login_logout_recovery_and_private_defaults():
    data = credentials()
    with TestClient(app, headers=HEADERS) as client:
        mismatch = client.post("/api/auth/register", json={**data, "confirm_password": "mismatched passphrase"})
        assert mismatch.status_code == 422
        created = client.post("/api/auth/register", json=data)
        assert created.status_code == 201, created.text
        body = created.json()
        code = body["recovery_code"]
        assert not body["account"]["cloud_enabled"] and not body["account"]["save_history"]
        cookie = created.headers["set-cookie"]
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie
        account = body["account"]
        with connection() as db:
            row = db.execute("SELECT * FROM accounts WHERE id=%s", (account["id"],)).fetchone()
            assert data["email"] not in row["email_encrypted"]
            assert row["password_hash"].startswith("$argon2id$") and PASS not in row["password_hash"]
            assert password_matches(row["password_hash"], PASS)
            assert code not in row["recovery_hash"]
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/documents").status_code == 401
        assert client.post("/api/auth/login", json={**data, "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json=data).status_code == 200
        old_cookie = client.cookies.get(COOKIE)
        assert client.post("/api/auth/logout-all").status_code == 204
        client.cookies.set(COOKIE, old_cookie)
        assert client.get("/api/documents").status_code == 401
        client.cookies.clear()
        new_pass = "replacement fixture passphrase!"
        recovered = client.post("/api/auth/recover", json={**data, "password": new_pass, "confirm_password": new_pass, "recovery_code": code})
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["recovery_code"] != code
        assert client.post("/api/auth/recover", json={**data, "recovery_code": code}).status_code == 403
        assert client.request("DELETE", "/api/auth/account", json={"password": new_pass}).status_code == 204


@integration
def test_server_session_expiry_and_legacy_cookie_cannot_authorize():
    with TestClient(app, headers=HEADERS) as client:
        created = client.post("/api/auth/register", json=credentials()).json()
        aid = created["account"]["id"]
        token = client.cookies.get(COOKIE)
        with connection() as db:
            db.execute("UPDATE sessions SET last_seen=now()-interval '31 minutes' WHERE account_id=%s", (aid,))
        assert client.get("/api/documents").status_code == 401
        assert client.post("/api/workspace").status_code == 401
        client.cookies.clear()
        client.cookies.set(LEGACY_COOKIE, token)
        assert client.get("/api/documents").status_code == 401
        with connection() as db:
            db.execute("DELETE FROM workspaces WHERE id=%s", (created["account"]["workspace_id"],))


@integration
def test_defaults_no_history_encrypted_records_and_disclosure_bypass_denied():
    def upload(client):
        data = (Path(__file__).resolve().parents[1] / "samples/cedar-trial-report.pdf").read_bytes()
        return client.post("/api/documents", files={"file": ("cedar-trial-report.pdf", data, "application/pdf")})
    with TestClient(app, headers=HEADERS) as client, TestClient(app, headers=HEADERS) as other:
        me = client.post("/api/auth/register", json=credentials()).json()["account"]
        other.post("/api/auth/register", json=credentials())
        did = upload(client).json()["id"]
        body = {"question": "The Cedar trial enrolled 120 adults.", "document_ids": [did]}
        result = client.post("/api/verify", json=body)
        assert result.status_code == 200, result.text
        assert not result.json()["privacy"]["history_saved"]
        assert client.get("/api/runs").json()["runs"] == []
        assert client.get(f"/api/runs/{result.json()['id']}").status_code == 404
        with connection() as db:
            d = db.execute("SELECT * FROM documents WHERE id=%s", (did,)).fetchone()
            p = db.execute("SELECT text FROM pages WHERE document_id=%s LIMIT 1", (did,)).fetchone()
            c = db.execute("SELECT text FROM chunks WHERE document_id=%s LIMIT 1", (did,)).fetchone()
            assert d["encrypted"] and bytes(d["pdf"]).startswith(b"VAI1")
            assert "Cedar" not in p["text"] and "Cedar" not in c["text"] and ".pdf" not in d["name"]
        cloud = {**body, "provider": "gemini", "model": "gemini-3.5-flash-lite"}
        assert client.post("/api/ask", json={**cloud, "consent_token": "invented"}).status_code == 403
        assert client.post("/api/privacy/preview", json=cloud).status_code == 403
        client.put("/api/privacy/preferences", json={"cloud_enabled": True, "save_history": True})
        preview = client.post("/api/privacy/preview", json=cloud)
        assert preview.status_code == 200, preview.text
        token = preview.json()["consent_token"]
        assert client.post("/api/ask", json={**cloud, "question": "A changed question about the trial", "consent_token": token}).status_code == 409
        other.put("/api/privacy/preferences", json={"cloud_enabled": True, "save_history": True})
        assert other.post("/api/ask", json={**cloud, "consent_token": token}).status_code == 404
        assert client.post("/api/ask", json=cloud).status_code == 409
        # Missing generator key fails after consuming consent; a token cannot be replayed.
        assert client.post("/api/ask", json={**cloud, "consent_token": token}).status_code == 422
        assert client.post("/api/ask", json={**cloud, "consent_token": token}).status_code == 409
        saved = client.post("/api/verify", json=body).json()
        assert saved["privacy"]["history_saved"]
        with connection() as db:
            row = db.execute("SELECT question,result,encrypted FROM runs WHERE id=%s", (saved["id"],)).fetchone()
            assert row["encrypted"] and "Cedar" not in row["question"] and "Cedar" not in json.dumps(row["result"])
        assert client.get(f"/api/runs/{saved['id']}").json()["question"] == body["question"]
        temporary = client.post("/api/verify", json={**body, "temporary": True}).json()
        assert not temporary["privacy"]["history_saved"]
        assert len(client.get("/api/runs").json()["runs"]) == 1
        exported = client.get("/api/privacy/export")
        assert exported.status_code == 200 and "Cedar" in exported.text
        assert me["email"] not in json.dumps(client.get("/api/privacy").json()["events"])
        assert client.delete("/api/privacy/history").status_code == 204
        assert client.get("/api/runs").json()["runs"] == []
        for c in (client, other):
            assert c.request("DELETE", "/api/auth/account", json={"password": PASS}).status_code == 204


@integration
def test_legacy_claim_encrypts_existing_documents_and_invalidates_old_cookie():
    wid, did = str(uuid4()), str(uuid4())
    token = secrets.token_hex(32)
    with connection() as db:
        db.execute("INSERT INTO workspaces(id,token_hash) VALUES(%s,%s)", (wid, token_hash(token)))
        db.execute("INSERT INTO documents(id,workspace_id,name,sha256,page_count,byte_count,pdf) VALUES(%s,%s,%s,%s,1,12,%s)", (did, wid, "older-private.pdf", "fixture-hash", b"old pdf data"))
        db.execute("INSERT INTO pages(document_id,page_number,text) VALUES(%s,1,%s)", (did, "Existing private text"))
    with TestClient(app, headers=HEADERS) as client, TestClient(app, headers=HEADERS) as old:
        client.cookies.set(LEGACY_COOKIE, token)
        old.cookies.set(LEGACY_COOKIE, token)
        assert client.get("/api/auth/session").json()["legacy_available"]
        assert client.get("/api/documents").status_code == 401
        created = client.post("/api/auth/register", json={**credentials(), "import_workspace": True})
        assert created.status_code == 201, created.text
        assert created.json()["account"]["workspace_id"] == wid
        assert client.get("/api/documents").json()["documents"][0]["name"] == "older-private.pdf"
        assert client.get(f"/api/documents/{did}/pages/1").json()["text"] == "Existing private text"
        assert client.get(f"/api/documents/{did}/pdf").content == b"old pdf data"
        assert old.get("/api/documents").status_code == 401
        assert not old.get("/api/auth/session").json()["legacy_available"]
        with connection() as db:
            row = db.execute("SELECT name,pdf,encrypted FROM documents WHERE id=%s", (did,)).fetchone()
            assert row["encrypted"] and "private" not in row["name"] and bytes(row["pdf"]) != b"old pdf data"
        assert client.request("DELETE", "/api/auth/account", json={"password": PASS}).status_code == 204
