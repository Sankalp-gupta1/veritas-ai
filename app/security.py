"""Shared security boundaries without logging user input or credentials."""

import hashlib
import time
from uuid import uuid4

from fastapi import HTTPException

from .db import connection


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def rate_limit(bucket, maximum=30, seconds=3600):
    window = int(time.time()) // seconds
    with connection() as db:
        count = db.execute(
            """INSERT INTO rate_limits(bucket,window_id,count) VALUES(%s,%s,1)
               ON CONFLICT(bucket,window_id) DO UPDATE SET count=rate_limits.count+1
               RETURNING count""", (bucket, window),
        ).fetchone()["count"]
    if count > maximum:
        raise HTTPException(429, "Too many attempts. Please wait before trying again.",
                            headers={"Retry-After": str(seconds - int(time.time()) % seconds)})


def audit(db, wid, event):
    # Fixed event names only: no questions, excerpts, emails, IPs or keys.
    db.execute("INSERT INTO privacy_events(id,workspace_id,event) VALUES(%s,%s,%s)",
               (str(uuid4()), wid, event))
    db.execute("DELETE FROM privacy_events WHERE workspace_id=%s AND created_at < now()-interval '30 days'", (wid,))


def housekeeping(db):
    # Expiry is enforced on reads even if cleanup has not run yet.
    db.execute("DELETE FROM sessions WHERE expires_at < now() OR last_seen < now()-interval '30 minutes'")
    db.execute("DELETE FROM disclosure_consents WHERE expires_at < now()")
    db.execute("DELETE FROM rate_limits WHERE window_id < %s", (int(time.time()) // 3600 - 48,))
