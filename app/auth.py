"""Email/password accounts, opaque revocable sessions and recovery codes.

Email is a sign-in identifier, not a verified identity. There is no pretend email
delivery: recovery uses a high-entropy code shown once to the account owner.
"""

import secrets
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field, SecretStr, field_validator

from . import config, vault
from .db import connection
from .security import audit, housekeeping, rate_limit, token_hash
from .storage_upgrade import encrypt_workspace

router = APIRouter(prefix="/api/auth", tags=["Account"])
COOKIE = "__Host-veritas_session" if config.PRODUCTION else "veritas_session"
LEGACY_COOKIE = "veritas_workspace"
PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        try:
            return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
        except EmailNotValidError as error:
            raise ValueError("Enter a valid email address.") from error


class Registration(Credentials):
    confirm_password: SecretStr
    import_workspace: bool = False


class PasswordChange(BaseModel):
    current_password: SecretStr
    password: SecretStr
    confirm_password: SecretStr


class PasswordProof(BaseModel):
    password: SecretStr


class Recovery(Registration):
    recovery_code: SecretStr


def validate_password(password, confirmation):
    value = password.get_secret_value()
    if len(value) < 15 or len(value) > 128:
        raise HTTPException(422, "Use a passphrase between 15 and 128 characters.")
    if not secrets.compare_digest(value.encode(), confirmation.get_secret_value().encode()):
        raise HTTPException(422, "The passwords do not match.")
    if len(set(value)) < 5 or value.casefold() in {
        "password123456789", "123456789012345", "qwertyuiopasdfgh", "letmeinletmein123",
    }:
        raise HTTPException(422, "Choose a less predictable passphrase.")
    return value


def password_matches(hashed, value):
    if len(value) > 128:
        return False
    try:
        return PASSWORDS.verify(hashed, value)
    except (VerificationError, InvalidHashError):
        return False


def set_session(db, account_id, response):
    token = secrets.token_hex(32)
    housekeeping(db)
    db.execute("INSERT INTO sessions(token_hash,account_id,expires_at) VALUES(%s,%s,now()+interval '7 days')",
               (token_hash(token), account_id))
    response.set_cookie(COOKIE, token, httponly=True, secure=config.PRODUCTION,
                        samesite="strict", max_age=7*24*3600, path="/")
    response.delete_cookie(LEGACY_COOKIE, path="/")


def current_account(request: Request):
    token = request.cookies.get(COOKIE, "")
    if len(token) != 64:
        raise HTTPException(401, "Sign in to open your private workspace.")
    with connection() as db:
        row = db.execute(
            """UPDATE sessions s SET last_seen=now() FROM accounts a, workspaces w
               WHERE s.token_hash=%s AND s.account_id=a.id AND w.id=a.workspace_id
                 AND s.expires_at>now() AND s.last_seen>now()-interval '30 minutes'
               RETURNING a.id,a.email_encrypted,a.password_hash,a.workspace_id,a.created_at,
                         w.cloud_enabled,w.save_history,w.privacy_version,s.expires_at""",
            (token_hash(token),),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Your session has ended. Sign in again.")
    return row


def workspace(account=Depends(current_account)):
    return str(account["workspace_id"])


def profile(row):
    return {
        "id": str(row["id"]),
        "email": vault.unseal_text(row["email_encrypted"], f"account:{row['id']}:email"),
        "email_verified": False,
        "workspace_id": str(row["workspace_id"]),
        "cloud_enabled": row.get("cloud_enabled", False),
        "save_history": row.get("save_history", False),
        "idle_timeout_minutes": 30,
    }


def legacy_workspace(db, request):
    token = request.cookies.get(LEGACY_COOKIE, "")
    if len(token) != 64:
        return None
    return db.execute(
        """SELECT w.id FROM workspaces w WHERE token_hash=%s
           AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.workspace_id=w.id) FOR UPDATE""",
        (token_hash(token),),
    ).fetchone()


@router.get("/session")
def session(request: Request):
    try:
        return {"account": profile(current_account(request)), "legacy_available": False}
    except HTTPException as error:
        if error.status_code != 401:
            raise
    with connection() as db:
        legacy = legacy_workspace(db, request)
    return {"account": None, "legacy_available": bool(legacy)}


@router.post("/register", status_code=201)
def register(body: Registration, request: Request, response: Response):
    value = validate_password(body.password, body.confirm_password)
    lookup = vault.fingerprint(body.email, "email-lookup")
    rate_limit("register:" + lookup, 8)
    rate_limit("register:global", 80)
    account_id, wid = str(uuid4()), str(uuid4())
    recovery = secrets.token_urlsafe(32)
    password_hash = PASSWORDS.hash(value)
    try:
        with connection() as db:
            old = legacy_workspace(db, request) if body.import_workspace else None
            if old:
                wid = str(old["id"])
                encrypt_workspace(db, wid)
                # Invalidate the old browser capability after ownership is assigned.
                db.execute("UPDATE workspaces SET token_hash=%s WHERE id=%s",
                           (token_hash(secrets.token_hex(32)), wid))
            else:
                db.execute("INSERT INTO workspaces(id,token_hash) VALUES(%s,%s)",
                           (wid, token_hash(secrets.token_hex(32))))
            row = db.execute(
                """INSERT INTO accounts(id,email_lookup,email_encrypted,password_hash,recovery_hash,workspace_id)
                   VALUES(%s,%s,%s,%s,%s,%s) RETURNING *""",
                (account_id, lookup, vault.seal_text(body.email, f"account:{account_id}:email"),
                 password_hash, token_hash(recovery), wid),
            ).fetchone()
            set_session(db, account_id, response)
            audit(db, wid, "account_created")
    except UniqueViolation as error:
        raise HTTPException(409, "Could not create this account. Try signing in or use another email.") from error
    return {"account": profile(row), "recovery_code": recovery, "imported_workspace": bool(old)}


@router.post("/login")
def login(body: Credentials, response: Response):
    lookup = vault.fingerprint(body.email, "email-lookup")
    rate_limit("login:" + lookup, 15)
    rate_limit("login:global", 300)
    with connection() as db:
        row = db.execute("SELECT a.*,w.cloud_enabled,w.save_history FROM accounts a JOIN workspaces w ON w.id=a.workspace_id WHERE a.email_lookup=%s FOR UPDATE OF a", (lookup,)).fetchone()
        valid = password_matches(row["password_hash"] if row else DUMMY_HASH, body.password.get_secret_value())
        if not valid or not row:
            raise HTTPException(401, "Email or password is incorrect.")
        if PASSWORDS.check_needs_rehash(row["password_hash"]):
            db.execute("UPDATE accounts SET password_hash=%s WHERE id=%s", (PASSWORDS.hash(body.password.get_secret_value()), row["id"]))
        set_session(db, row["id"], response)
        audit(db, row["workspace_id"], "signed_in")
    return {"account": profile(row)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    with connection() as db:
        row = db.execute("DELETE FROM sessions WHERE token_hash=%s RETURNING account_id", (token_hash(request.cookies.get(COOKIE, "")),)).fetchone()
        if row:
            account = db.execute("SELECT workspace_id FROM accounts WHERE id=%s", (row["account_id"],)).fetchone()
            if account:
                audit(db, account["workspace_id"], "signed_out")
    response.delete_cookie(COOKIE, path="/", secure=config.PRODUCTION, httponly=True, samesite="strict")
    response.delete_cookie(LEGACY_COOKIE, path="/")
    response.status_code = 204
    return response


@router.post("/logout-all", status_code=204)
def logout_all(response: Response, account=Depends(current_account)):
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE account_id=%s", (account["id"],))
        audit(db, account["workspace_id"], "all_sessions_revoked")
    response.delete_cookie(COOKIE, path="/", secure=config.PRODUCTION, httponly=True, samesite="strict")
    response.status_code = 204
    return response


@router.post("/password")
def change_password(body: PasswordChange, response: Response, account=Depends(current_account)):
    value = validate_password(body.password, body.confirm_password)
    rate_limit("password:" + str(account["id"]), 10)
    recovery = secrets.token_urlsafe(32)
    with connection() as db:
        row = db.execute("SELECT password_hash FROM accounts WHERE id=%s FOR UPDATE", (account["id"],)).fetchone()
        if not row or not password_matches(row["password_hash"], body.current_password.get_secret_value()):
            raise HTTPException(403, "The current password is incorrect.")
        db.execute("UPDATE accounts SET password_hash=%s,recovery_hash=%s WHERE id=%s", (PASSWORDS.hash(value), token_hash(recovery), account["id"]))
        db.execute("DELETE FROM sessions WHERE account_id=%s", (account["id"],))
        set_session(db, account["id"], response)
        audit(db, account["workspace_id"], "password_changed_sessions_revoked")
    return {"recovery_code": recovery}


@router.post("/recover")
def recover(body: Recovery, response: Response):
    value = validate_password(body.password, body.confirm_password)
    lookup = vault.fingerprint(body.email, "email-lookup")
    rate_limit("recovery:" + lookup, 8)
    rate_limit("recovery:global", 60)
    new_code = secrets.token_urlsafe(32)
    with connection() as db:
        row = db.execute("SELECT * FROM accounts WHERE email_lookup=%s FOR UPDATE", (lookup,)).fetchone()
        valid = secrets.compare_digest(row["recovery_hash"] if row else "0"*64, token_hash(body.recovery_code.get_secret_value()))
        if not row or not valid:
            raise HTTPException(403, "The email and recovery code could not be verified.")
        db.execute("UPDATE accounts SET password_hash=%s,recovery_hash=%s WHERE id=%s", (PASSWORDS.hash(value), token_hash(new_code), row["id"]))
        db.execute("DELETE FROM sessions WHERE account_id=%s", (row["id"],))
        set_session(db, row["id"], response)
        audit(db, row["workspace_id"], "account_recovered_sessions_revoked")
    return {"recovery_code": new_code}


@router.delete("/account", status_code=204)
def delete_account(body: PasswordProof, response: Response, account=Depends(current_account)):
    rate_limit("delete:" + str(account["id"]), 8)
    with connection() as db:
        row = db.execute("SELECT password_hash FROM accounts WHERE id=%s FOR UPDATE", (account["id"],)).fetchone()
        if not row or not password_matches(row["password_hash"], body.password.get_secret_value()):
            raise HTTPException(403, "The password is incorrect.")
        # Cascades to account, sessions, PDFs, pages, vectors, answers and privacy log.
        db.execute("DELETE FROM workspaces WHERE id=%s", (account["workspace_id"],))
    response.delete_cookie(COOKIE, path="/", secure=config.PRODUCTION, httponly=True, samesite="strict")
    response.delete_cookie(LEGACY_COOKIE, path="/")
    response.status_code = 204
    return response
