"""Check a deployed app's access boundaries with two fresh, disposable workspaces.

Uses one fictional PDF. Saves check outcomes, never cookies, keys or uploaded text.
This is a focused regression check, not a penetration test or security guarantee.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from smoke_live import Client


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    url = urlsplit(base)
    if url.scheme != "https" or url.username or url.password or url.path or url.query or url.fragment:
        parser.error("Supply an HTTPS origin without credentials or a path.")
    output = Path(args.out)
    if output.exists():
        parser.error("Use a new report path; existing evidence is preserved.")
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "status": "running",
        "scope": "Two disposable workspaces and one authored PDF; no existing users or real API keys",
        "checks": [],
        "limitations": [
            "Not a full security audit or proof that a leak is impossible",
            "No cloud-admin, log-drain, backup-purge or account-permission audit",
            "No live Gemini request or verification of the API key owner's billing/data-sharing settings",
        ],
    }
    anonymous, owner, other = Client(base), Client(base), Client(base)
    created = []

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")

    def check(name, passed, detail=""):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})
        save()
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        if not passed:
            raise AssertionError(name)

    def status(name, result, expected):
        check(name, result[0] == expected, f"HTTP {result[0]}")
        return result[1]

    try:
        health = status("Health endpoint responds", anonymous.request("GET", "/api/health"), 200)
        report["health"] = health
        check("Database and local models ready", health.get("database") == "connected" and health.get("models_ready"))
        status("Anonymous document access denied", anonymous.request("GET", "/api/documents"), 401)
        status("Mutation without app header denied", anonymous.request("POST", "/api/workspace", headers={"X-Veritas-Request": ""}), 403)
        status("Foreign-origin mutation denied", anonymous.request("POST", "/api/workspace", headers={"Origin": "https://untrusted.example"}), 403)
        for path in ["/.env", "/.git/config"]:
            status("Private configuration path not served: " + path, anonymous.request("GET", path), 404)
        for label, client in [("Owner", owner), ("Other", other)]:
            result = client.request("POST", "/api/workspace")
            if result[0] == 200:
                created.append((label, client))
            status(label + " workspace created", result, 200)
            cookie = result[2].get("Set-Cookie", "").lower()
            check(label + " cookie has Secure, HttpOnly and SameSite=Strict", all(flag in cookie for flag in ["secure", "httponly", "samesite=strict"]))
            check(label + " response is not cacheable", "no-store" in result[2].get("Cache-Control", ""))
        source = (Path(__file__).resolve().parents[1] / "samples" / "cedar-trial-report.pdf").read_bytes()
        doc = status("Fictional PDF stored in owner workspace", owner.upload("privacy-check-fictional.pdf", source), 201)["id"]
        pdf = owner.request("GET", f"/api/documents/{doc}/pdf")
        status("Owner can read original PDF", pdf, 200)
        check("PDF bytes match upload", hashlib.sha256(pdf[1]).digest() == hashlib.sha256(source).digest())
        check("Document responses use no-store", "no-store" in pdf[2].get("Cache-Control", ""))
        check("PDF response has sandbox policy", pdf[2].get("Content-Security-Policy") == "sandbox")
        for suffix in ["pdf", "pages/1"]:
            status("Other workspace cannot read " + suffix, other.request("GET", f"/api/documents/{doc}/{suffix}"), 404)
        body = {"question": "The Cedar trial enrolled 120 adults.", "document_ids": [doc]}
        status("Other workspace cannot query selected document", other.request("POST", "/api/verify", body), 404)
        run = status("Local claim check produces a saved result", owner.request("POST", "/api/verify", body), 200)
        status("Other workspace cannot read saved answer", other.request("GET", f"/api/runs/{run['id']}"), 404)
        status("Other workspace cannot delete owner's PDF", other.request("DELETE", f"/api/documents/{doc}"), 404)
        status("Owner deletes test PDF", owner.request("DELETE", f"/api/documents/{doc}"), 204)
        status("Deleted PDF is no longer available through API", owner.request("GET", f"/api/documents/{doc}/pdf"), 404)
        runs = status("Owner history can be checked after deletion", owner.request("GET", "/api/runs"), 200)
        check("Document deletion clears saved source text from history", runs["runs"] == [])
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        raise
    finally:
        for label, client in created:
            try:
                response = client.request("DELETE", "/api/workspace")
                report["checks"].append({"name": label + " disposable workspace removed", "passed": response[0] == 204, "detail": f"HTTP {response[0]}"})
                print(("PASS " if response[0] == 204 else "FAIL ") + label + " cleanup", flush=True)
                if response[0] != 204:
                    report["status"] = "failed"
            except Exception as error:
                report["checks"].append({"name": label + " cleanup", "passed": False, "detail": type(error).__name__})
                report["status"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["passed"] = sum(c["passed"] for c in report["checks"])
        report["total"] = len(report["checks"])
        save()
        print(f"Result: {report['status']}; {report['passed']}/{report['total']} checks", flush=True)
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
