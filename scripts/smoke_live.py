"""Exercise a deployed VeritasAI using only fresh workspaces and authored PDFs.

No existing user's cookie or records are used. Test workspaces are removed in
finally blocks. The saved report contains check names and outcomes, not cookies.
"""

import argparse
import hashlib
import http.cookiejar
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Client:
    def __init__(self, base_url, jar=None):
        self.base_url = base_url
        self.jar = jar if jar is not None else http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method, path, data=None, headers=None, raw=None):
        outgoing = {"X-Veritas-Request": "1", "Origin": self.base_url}
        if data is not None:
            raw = json.dumps(data).encode()
            outgoing["Content-Type"] = "application/json"
        outgoing.update(headers or {})
        request = urllib.request.Request(
            self.base_url + path, data=raw, headers=outgoing, method=method
        )
        try:
            response = self.opener.open(request, timeout=180)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read()
            media = response.headers.get("Content-Type", "")
            body = json.loads(content) if "application/json" in media else content
            return response.status, body, response.headers

    def upload(self, filename, content):
        boundary = "veritas-" + uuid4().hex
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                "Content-Type: application/pdf\r\n\r\n"
            ).encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )
        return self.request(
            "POST",
            "/api/documents",
            raw=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--out", required=True, help="New JSON report path; existing reports are not overwritten"
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
        parser.error("Use HTTPS for a remote installation.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        parser.error("Provide only the origin, without credentials, a path, or query parameters.")
    output = Path(args.out)
    if output.exists():
        parser.error("Choose a new output file to preserve earlier evidence.")
    report = {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "scope": "Public HTTP/API flows using fictional PDFs and fresh workspaces; not browser-rendering QA",
        "checks": [],
        "limitations": [
            "No browser visual/keyboard/mobile test",
            "No service-restart or load test",
        ],
    }
    anonymous, alice, bob = Client(base), Client(base), Client(base)
    created = []
    started = time.perf_counter()

    def save_report():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")

    def check(name, condition, detail=""):
        report["checks"].append({"name": name, "passed": bool(condition), "detail": detail})
        save_report()
        print(
            ("PASS " if condition else "FAIL ") + name + (": " + detail if detail else ""),
            flush=True,
        )
        if not condition:
            raise AssertionError(name + (": " + detail if detail else ""))

    def status(name, result, expected):
        check(name, result[0] == expected, f"HTTP {result[0]}")
        return result[1]

    def post(client, path, question, ids, **extra):
        return client.request("POST", path, {"question": question, "document_ids": ids, **extra})

    def check_citations(result):
        citations = [
            c
            for claim in result["claims"]
            for c in claim["citations"] + claim["counter_evidence"]
            if c.get("integrity")
        ]
        check("Answer contains inspectable evidence", bool(citations))
        for citation in citations:
            code, page, _ = alice.request(
                "GET", f"/api/documents/{citation['document_id']}/pages/{citation['page_number']}"
            )
            check(
                "Citation quote matches exact physical page offsets",
                code == 200
                and page["text"][citation["start_offset"] : citation["end_offset"]]
                == citation["quote"],
            )
        return citations

    try:
        home = anonymous.request("GET", "/")
        html = status("Public homepage", home, 200).decode()
        check(
            "Homepage shell is not cached across deployments",
            "no-store" in home[2].get("Cache-Control", ""),
        )
        assets = re.findall(r'(?:src|href)="([^"]+)"', html)
        for path in assets:
            if path.startswith("/assets/") or path == "/favicon.svg":
                code, data, headers = anonymous.request("GET", path)
                expected_type = (
                    "javascript"
                    if path.endswith(".js")
                    else "css"
                    if path.endswith(".css")
                    else "image/svg+xml"
                )
                check(
                    "Frontend asset " + path,
                    code == 200 and expected_type in headers.get("Content-Type", "") and bool(data),
                )
                if path.endswith(".js"):
                    research_assets = set(re.findall(r"Research-[A-Za-z0-9_-]+\.js", data.decode()))
                    for filename in research_assets:
                        status(
                            "Lazy-loaded evidence lab bundle",
                            anonymous.request("GET", "/assets/" + filename),
                            200,
                        )
        health = status("Live health endpoint", anonymous.request("GET", "/api/health"), 200)
        check(
            "Database and local models ready",
            health.get("database") == "connected" and health.get("models_ready") is True,
        )
        report["health"] = health
        status("OpenAPI schema", anonymous.request("GET", "/api/openapi.json"), 200)
        status(
            "Unauthenticated document access denied",
            anonymous.request("GET", "/api/documents"),
            401,
        )
        status(
            "Mutation without request header denied",
            anonymous.request("POST", "/api/workspace", headers={"X-Veritas-Request": ""}),
            403,
        )
        status(
            "Cross-origin mutation denied",
            anonymous.request(
                "POST", "/api/workspace", headers={"Origin": "https://untrusted.example"}
            ),
            403,
        )
        for label, client in [("Alice", alice), ("Bob", bob)]:
            result = client.request("POST", "/api/workspace")
            if result[0] == 200:
                created.append(client)
            status(label + " fresh workspace", result, 200)
            cookie_header = result[2].get("Set-Cookie", "").lower()
            check(
                label + " secure workspace cookie",
                all(flag in cookie_header for flag in ["secure", "httponly", "samesite=strict"]),
            )
        check(
            "Fresh workspace is empty",
            status("List new documents", alice.request("GET", "/api/documents"), 200)["documents"]
            == [],
        )
        status("Sample manifest", anonymous.request("GET", "/api/samples"), 200)
        root = Path(__file__).resolve().parents[1]
        sample_files = ["cedar-trial-report.pdf", "cedar-reanalysis.pdf", "willow-observation.pdf"]
        documents, originals = [], {}
        for name in sample_files:
            data = status(
                "Download sample " + name, anonymous.request("GET", "/api/samples/" + name), 200
            )
            check(
                "Sample bytes match versioned fixture " + name,
                hashlib.sha256(data).digest()
                == hashlib.sha256((root / "samples" / name).read_bytes()).digest(),
            )
            result = status("Upload " + name, alice.upload(name, data), 201)
            documents.append(result["id"])
            originals[result["id"]] = data
        check(
            "Three PDFs stored",
            len(
                status("List uploaded documents", alice.request("GET", "/api/documents"), 200)[
                    "documents"
                ]
            )
            == 3,
        )
        primary = documents[0]
        duplicate = status(
            "Duplicate upload", alice.upload(sample_files[0], originals[primary]), 201
        )
        check(
            "Duplicate is not stored twice",
            duplicate.get("duplicate") and duplicate["id"] == primary,
        )
        status(
            "Other workspace cannot open PDF",
            bob.request("GET", f"/api/documents/{primary}/pdf"),
            404,
        )
        status(
            "Other workspace cannot open page",
            bob.request("GET", f"/api/documents/{primary}/pages/1"),
            404,
        )
        status(
            "Other workspace cannot delete PDF",
            bob.request("DELETE", f"/api/documents/{primary}"),
            404,
        )
        status(
            "Other workspace cannot retrieve selected PDF",
            post(bob, "/api/verify", "The Cedar trial enrolled 120 adults.", [primary]),
            404,
        )
        result = status(
            "Verify supported claim",
            post(alice, "/api/verify", "The Cedar trial enrolled 120 adults.", [primary]),
            200,
        )
        check(
            "Supported statement retained",
            result["claims"][0]["verdict"] == "supported" and not result["abstained"],
            result["claims"][0]["verdict"],
        )
        check_citations(result)
        run_id = result["id"]
        status(
            "Other workspace cannot read saved answer",
            bob.request("GET", f"/api/runs/{run_id}"),
            404,
        )
        result = status(
            "Verify unsupported funding claim",
            post(
                alice,
                "/api/verify",
                "The Cedar trial was funded by a pharmaceutical company.",
                [primary],
            ),
            200,
        )
        check(
            "Insufficient evidence withheld",
            result["abstained"] and result["claims"][0]["verdict"] == "insufficient",
            result["claims"][0]["verdict"],
        )
        result = status(
            "Verify conflicting numerical claim",
            post(alice, "/api/verify", "The Cedar trial enrolled 900 adults.", [primary]),
            200,
        )
        check("Incorrect quantity withheld", result["abstained"], result["claims"][0]["verdict"])
        result = status(
            "Check disagreement across two reports",
            post(
                alice,
                "/api/verify",
                "The Cedar sleep-extension group improved its attention score by 12 points.",
                documents[:2],
            ),
            200,
        )
        check(
            "Conflicting sources preserved",
            result["claims"][0]["verdict"] == "conflict"
            and bool(result["claims"][0]["counter_evidence"]),
            result["claims"][0]["verdict"],
        )
        check_citations(result)
        result = status(
            "Ask a source-grounded question",
            post(alice, "/api/ask", "How many adults were enrolled in the Cedar trial?", [primary]),
            200,
        )
        check(
            "Real source excerpts returned",
            result["answer_kind"] == "source_excerpts" and not result["abstained"],
        )
        check_citations(result)
        status("Reopen saved answer", alice.request("GET", f"/api/runs/{run_id}"), 200)
        reloaded = Client(base, alice.jar)
        check(
            "Workspace persists across a fresh HTTP client",
            len(
                status("Reload documents", reloaded.request("GET", "/api/documents"), 200)[
                    "documents"
                ]
            )
            == 3,
        )
        original = status(
            "Open original PDF", alice.request("GET", f"/api/documents/{primary}/pdf"), 200
        )
        check("Original PDF bytes preserved", original == originals[primary])
        status(
            "Invalid page number", alice.request("GET", f"/api/documents/{primary}/pages/9999"), 404
        )
        status("Malformed PDF rejected", alice.upload("bad.pdf", b"not a PDF"), 422)
        from pypdf import PdfReader, PdfWriter

        encrypted = PdfWriter(clone_from=PdfReader(io.BytesIO(originals[primary])))
        encrypted.encrypt("fictional-test-password")
        buffer = io.BytesIO()
        encrypted.write(buffer)
        status("Encrypted PDF rejected", alice.upload("locked.pdf", buffer.getvalue()), 422)
        blank = PdfWriter()
        blank.add_blank_page(width=300, height=300)
        buffer = io.BytesIO()
        blank.write(buffer)
        status(
            "Image-only or blank PDF explains OCR limitation",
            alice.upload("blank.pdf", buffer.getvalue()),
            422,
        )
        status(
            "Oversized PDF rejected",
            alice.upload("oversized.pdf", b"%PDF-" + b"0" * 4_000_000),
            422,
        )
        status("Blank question rejected", post(alice, "/api/ask", "     ", [primary]), 422)
        status(
            "Empty document selection rejected",
            post(alice, "/api/ask", "What does the report say?", []),
            422,
        )
        status(
            "Unknown source rejected",
            post(alice, "/api/ask", "What does the report say?", [str(uuid4())]),
            404,
        )
        status(
            "Extractive mode cannot masquerade as RAG comparison",
            post(alice, "/api/compare", "How many adults were enrolled?", [primary]),
            422,
        )
        if not health["gemini_configured"]:
            result = post(
                alice, "/api/ask", "How many adults were enrolled?", [primary], provider="gemini"
            )
            status("Missing Gemini key gives actionable error", result, 422)
            check("Missing-key message is clear", "API key" in result[1].get("detail", ""))
            report["limitations"].append(
                "No server Gemini key configured; live generation and three-method quality comparison not tested"
            )
        else:
            report["limitations"].append(
                "This smoke command does not use the owner's paid generator key; provider QA is a separate explicit run"
            )
        metrics = status("Evidence lab measurements", alice.request("GET", "/api/research"), 200)
        check(
            "Research data is measured and labelled",
            metrics.get("status") == "complete" and metrics.get("sample_count") == 24,
        )
        status(
            "Delete one uploaded source", alice.request("DELETE", f"/api/documents/{primary}"), 204
        )
        status(
            "Deleted source cannot be downloaded",
            alice.request("GET", f"/api/documents/{primary}/pdf"),
            404,
        )
        check(
            "Deletion clears saved source text from history",
            status("History after deletion", alice.request("GET", "/api/runs"), 200)["runs"] == [],
        )
        check(
            "Unrelated sources remain",
            len(
                status("Remaining documents", alice.request("GET", "/api/documents"), 200)[
                    "documents"
                ]
            )
            == 2,
        )
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = str(error)
        print("Stopped at the first failure:", str(error), flush=True)
    finally:
        report["cleanup"] = []
        for index, client in enumerate(created):
            try:
                code, _, _ = client.request("DELETE", "/api/workspace")
                report["cleanup"].append({"test_workspace": index + 1, "deleted": code == 204})
                if code != 204:
                    report["status"] = "failed"
            except Exception:
                report["cleanup"].append({"test_workspace": index + 1, "deleted": False})
                report["status"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["duration_seconds"] = round(time.perf_counter() - started, 2)
        save_report()
        print("Saved report:", output, flush=True)
    if report.get("status") != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
