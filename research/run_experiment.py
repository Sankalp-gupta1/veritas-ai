"""Collect actual three-variant runs; export blind annotation rows, never invented labels."""

import argparse
import csv
import hashlib
import json
import os
import secrets
from uuid import uuid4
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def item_id(run_id, claim_id):
    return hashlib.sha256(f"{run_id}:{claim_id}".encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--questions", default="research/questions.example.json")
    parser.add_argument("--pdf-dir", default="samples")
    parser.add_argument("--out", default="research/private-runs/latest")
    parser.add_argument("--provider", choices=["gemini", "ollama"], default="gemini")
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if url.scheme != "https" and url.hostname not in ("localhost", "127.0.0.1"):
        parser.error("Use HTTPS for remote installations.")
    out = Path(args.out)
    if out.exists():
        parser.error("Choose a new output directory; previous experiments must remain immutable.")
    questions = json.loads(Path(args.questions).read_text())
    headers = {"X-Veritas-Request": "1"}
    results, reviews, corpus = [], [], []
    with httpx.Client(base_url=args.base_url, headers=headers, timeout=280) as client:
        password = secrets.token_urlsafe(32)
        account = {"email": f"research-run-{uuid4().hex}@example.com", "password": password, "confirm_password": password}
        client.post("/api/auth/register", json=account).raise_for_status()
        try:
            client.put("/api/privacy/preferences", json={"cloud_enabled": args.provider == "gemini", "save_history": False}).raise_for_status()
            document_ids = []
            for path in sorted(Path(args.pdf_dir).glob("*.pdf")):
                data = path.read_bytes()
                response = client.post("/api/documents", files={"file": (path.name, data, "application/pdf")})
                response.raise_for_status()
                document_ids.append(response.json()["id"])
                corpus.append({"filename": path.name, "sha256": hashlib.sha256(data).hexdigest()})
            if not document_ids:
                raise ValueError("No PDFs found.")
            out.mkdir(parents=True)
            (out / "config.json").write_text(json.dumps({"questions": questions, "corpus": corpus, "provider": args.provider, "privacy": "reviewed masking and source-label substitution"}, indent=2))
            for question in questions["questions"]:
                payload = {"question": question["question"], "document_ids": document_ids, "provider": args.provider}
                if args.provider == "gemini":
                    preview = client.post("/api/privacy/preview?operation=compare", json=payload)
                    preview.raise_for_status()
                    disclosure = preview.json()
                    print("Review the exact text that will be sent to Google:")
                    print(json.dumps(disclosure["payloads"], indent=2, ensure_ascii=False))
                    print(disclosure["notice"])
                    if input("Type SHARE to approve this one request, or anything else to stop: ").strip() != "SHARE":
                        raise RuntimeError("External disclosure cancelled. No comparison was sent.")
                    payload["consent_token"] = disclosure["consent_token"]
                generation_headers = {"X-Gemini-Key": os.environ["GEMINI_API_KEY"]} if args.provider == "gemini" and os.getenv("GEMINI_API_KEY") else {}
                response = client.post("/api/compare", json=payload, headers=generation_headers)
                response.raise_for_status()
                for result in response.json()["results"]:
                    result["question_id"] = question["id"]
                    results.append(result)
                    with (out / "predictions.jsonl").open("a") as stream:
                        stream.write(json.dumps(result) + "\n")
                    for claim in result["claims"]:
                        reviews.append({"item_id": item_id(result["id"], claim["id"]), "question_id": question["id"], "question": question["question"], "claim": claim["text"], "evidence": json.dumps(claim["citations"]), "gold_label": "", "citation_set_supports": "", "covered_fact_ids": "", "reviewer": ""})
                print("Collected", question["id"])
        finally:
            # Remove only this newly-created research account and its data.
            cleanup = client.request("DELETE", "/api/auth/account", json={"password": password})
            if cleanup.status_code == 401:
                client.post("/api/auth/login", json=account).raise_for_status()
                cleanup = client.request("DELETE", "/api/auth/account", json={"password": password})
            cleanup.raise_for_status()
    # Hide model verdicts, scores, variant names and display decisions from annotators.
    for row in reviews:
        evidence = json.loads(row["evidence"])
        row["evidence"] = json.dumps(
            [{k: c.get(k) for k in ["document_name", "page_number", "quote"]} for c in evidence]
        )
    reviews.sort(key=lambda row: row["item_id"])
    columns = [
        "item_id",
        "question_id",
        "question",
        "claim",
        "evidence",
        "gold_label",
        "citation_set_supports",
        "covered_fact_ids",
        "reviewer",
    ]
    with (out / "claims_for_review.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(reviews)
    print("Saved predictions and unlabelled review rows. No quality score has been invented.")


if __name__ == "__main__":
    main()
