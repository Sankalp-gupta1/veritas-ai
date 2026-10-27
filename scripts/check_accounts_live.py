"""Check the deployed account release using only newly created fictional data.

No real user cookies, emails, passwords or documents are read. The output report
contains check names and status only. No Gemini request is made. Test accounts
are deleted in finally blocks; a failed cleanup makes the check fail.
"""

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

from smoke_live import Client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if url.scheme != "https" or url.username or url.password or url.query or url.fragment or url.path:
        parser.error("Use the HTTPS production or protected-preview URL.")
    if Path(args.out).exists():
        parser.error("Choose a new report path to preserve previous evidence.")
    base = args.base_url.rstrip("/")
    clients = [Client(base), Client(base)]
    secrets_by_client, checks, accounts = {}, [], []

    def check(name, condition):
        checks.append({"check": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def call(client, method, path, data=None):
        status, body, headers = client.request(method, path, data=data)
        return status, body, headers

    try:
        status, _, _ = call(clients[0], "GET", "/api/documents")
        check("Anonymous document access denied", status == 401)
        for index, client in enumerate(clients):
            password = secrets.token_urlsafe(30)
            data = {"email": f"veritas-check-{uuid4().hex}@example.com", "password": password, "confirm_password": password}
            status, body, headers = call(client, "POST", "/api/auth/register", data)
            check(f"Account {index+1} created", status == 201)
            secrets_by_client[index] = data
            accounts.append(index)
            check(f"Account {index+1} has private defaults", not body["account"]["cloud_enabled"] and not body["account"]["save_history"])
            cookie = headers.get("Set-Cookie", "").lower()
            check(f"Account {index+1} secure cookie", all(flag in cookie for flag in ("secure", "httponly", "samesite=strict")))
            check(f"Account {index+1} recovery code supplied", len(body["recovery_code"]) >= 40)
        alice, bob = clients
        sample = Path(__file__).resolve().parents[1] / "samples/cedar-trial-report.pdf"
        status, body, _ = alice.upload(sample.name, sample.read_bytes())
        check("Fictional PDF uploaded", status == 201)
        did = body["id"]
        for path in (f"/api/documents/{did}/pdf", f"/api/documents/{did}/pages/1"):
            status, _, _ = call(bob, "GET", path)
            check(f"Other account denied {path.rsplit('/',1)[-1]}", status == 404)
        status, data, _ = call(bob, "GET", "/api/documents")
        check("Other account has no documents", status == 200 and data["documents"] == [])
        status, data, _ = call(alice, "GET", "/api/privacy")
        check("Current content encrypted", status == 200 and data["encrypted_content"] and data["vault_configured"])
        body = {"question": "The Cedar trial enrolled 120 adults.", "document_ids": [did]}
        status, result, _ = call(alice, "POST", "/api/verify", body)
        check("Real local claim check works", status == 200 and result["claims"][0]["verdict"] == "supported")
        check("Default answer not saved", result["privacy"]["history_saved"] is False)
        status, history, _ = call(alice, "GET", "/api/runs")
        check("Default history empty", status == 200 and history["runs"] == [])
        cloud = {**body, "provider": "gemini"}
        status, _, _ = call(alice, "POST", "/api/ask", cloud)
        check("Direct Gemini request blocked", status == 403)
        status, _, _ = call(alice, "PUT", "/api/privacy/preferences", {"cloud_enabled": True, "save_history": True})
        check("Explicit preference update works", status == 200)
        status, preview, _ = call(alice, "POST", "/api/privacy/preview", cloud)
        check("Disclosure preview generated locally", status == 200 and bool(preview["payloads"]))
        check("Disclosure hides source filename", "cedar-trial-report.pdf" not in json.dumps(preview))
        status, _, _ = call(alice, "POST", "/api/ask", cloud)
        check("Enabled Gemini still requires approval", status == 409)
        status, _, _ = call(alice, "PUT", "/api/privacy/preferences", {"cloud_enabled": False, "save_history": True})
        check("External AI can be blocked again", status == 200)
        status, result, _ = call(alice, "POST", "/api/verify", body)
        check("History opt-in saves encrypted result", status == 200 and result["privacy"]["history_saved"])
        status, reopened, _ = call(alice, "GET", f"/api/runs/{result['id']}")
        check("Owner can reopen answer", status == 200 and reopened["question"] == body["question"])
        status, _, _ = call(bob, "GET", f"/api/runs/{result['id']}")
        check("Other account cannot reopen answer", status == 404)
        status, result, _ = call(alice, "POST", "/api/verify", {**body, "temporary": True})
        check("Temporary answer overrides saved history", status == 200 and not result["privacy"]["history_saved"])
        status, exported, _ = call(alice, "GET", "/api/privacy/export")
        check("Owner export includes own documents", status == 200 and len(exported["documents"]) == 1)
        status, _, _ = call(alice, "DELETE", f"/api/documents/{did}")
        check("Document deletion works", status == 204)
        status, history, _ = call(alice, "GET", "/api/runs")
        check("Deletion also removes saved evidence", status == 200 and history["runs"] == [])
        status, _, _ = call(alice, "POST", "/api/auth/logout-all")
        check("Sign out everywhere works", status == 204)
        status, _, _ = call(alice, "GET", "/api/documents")
        check("Revoked session cannot read data", status == 401)
        status, _, _ = call(alice, "POST", "/api/auth/login", secrets_by_client[0])
        check("Account signs back in", status == 200)
    finally:
        for index in accounts:
            status, _, _ = call(clients[index], "DELETE", "/api/auth/account", {"password": secrets_by_client[index]["password"]})
            if status == 401:
                call(clients[index], "POST", "/api/auth/login", secrets_by_client[index])
                status, _, _ = call(clients[index], "DELETE", "/api/auth/account", {"password": secrets_by_client[index]["password"]})
            checks.append({"check": f"Test account {index+1} removed", "passed": status == 204})
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "base_url": base,
                  "checks": checks, "passed": sum(c["passed"] for c in checks), "total": len(checks),
                  "note": "Fictional accounts only; no live Gemini call; not a penetration test."}
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(f"Checks: {report['passed']}/{report['total']}. Report: {out}")
        if not all(c["passed"] for c in checks):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
