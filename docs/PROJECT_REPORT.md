# VeritasAI: implementation and preliminary evaluation

**Prepared:** 14 October 2026  
**Release:** 0.1.0, research prototype  
**Owner:** Sankalp Gupta

## 1. What the project solves

An answer is hard to trust when you cannot find the sentence that supports it. VeritasAI connects each displayed claim to an uploaded document, its physical PDF page, and a matching piece of extracted text. A separate model checks whether that text supports the claim. Claims that fail this check remain visible in the audit trail but are withheld from the main answer.

This is source-support checking. A wrong paper can still support a wrong claim. A small language model can also misread an otherwise correct paper. The interface makes these limits visible instead of calling every answer “verified truth.”

## 2. Delivery status

| Requested output | Current state |
|---|---|
| React website with multiple PDF uploads | Implemented; production frontend build passes. Browser visual QA remains pending. |
| Python/FastAPI API and PostgreSQL vector search | Implemented and integration-tested with real SQL and local models. |
| Persistent cloud database | Dedicated `veritas` database and schema provisioned in Neon. Not yet exercised by a live web deployment. |
| Questions with exact sources, pages and quotes | Implemented. Source-excerpt mode works without a generative API key. |
| AI-written answers | Gemini and self-hosted Ollama adapters implemented. No live provider run was available during this release. |
| Claim-level checking and possible disagreements | Implemented with exact quote checks and local NLI inference. |
| Research dashboard and graphs | Actual 24-pair fixture results included. Full RAG quality comparison is not yet measured. |
| Reproducible experiments | Collection, blind review export, scoring and graph scripts included. |
| Easy setup and explanations | README, user guide, architecture, file guide and design decisions included. |
| Research manuscript | Preliminary draft included; no claim of a completed novel research result. |
| GitHub repository | Published at https://github.com/Sankalp-gupta1/veritas-ai; setup configuration restored after the initial manual upload. |
| Public deployment | Blocked by the connected Vercel team's 403 response to project creation. Render is not connected. |

## 3. A user's journey

The browser creates a private workspace using an unguessable cookie. The user uploads PDFs or explicitly imports the included fictional examples. The app reads physical pages, creates bounded text passages, computes embeddings, and saves the originals, extracted text and vectors in PostgreSQL.

The user selects documents and can choose one of three activities:

1. **Source excerpts:** retrieve relevant passages and display checked extracts. No text-generating API is required.
2. **Check a claim:** test a user's statement against local document evidence. No text-generating API is required.
3. **AI-written answer:** let Gemini or a local Ollama model draft short claims, then apply the evidence checks.

A citation opens the original PDF and highlights the quote in extracted page text. Users can reopen saved results, download an evidence record, compare retrieval methods, or delete documents. Deleting a document also clears saved workspace answers because those answers contain copies of source text.

## 4. Architecture and important choices

React talks to a same-origin FastAPI application. PostgreSQL stores every durable record, including the original PDF bytes. pgvector performs exact cosine search over a bounded corpus. This keeps document ownership, vectors and source deletion in one database transaction system.

Three small local models have different jobs: POTION creates embeddings, TinyBERT reranks question–passage pairs, and DeBERTa classifies evidence–claim relationships. Pinned model revisions and file hashes are recorded in the included manifest. Optional Gemini generation happens after retrieval; the key never belongs in frontend source or a repository.

The server derives page numbers and offsets from stored passages. It does not trust a model to invent citation metadata. Offsets identify normalized extracted text, not PDF pixel coordinates. A quote must match exactly after normalization before semantic checking can support the claim.

The verifier checks individual claims against cited quotes, then scans the retrieved context for possible counterevidence. It uses initial thresholds of 0.80 for support and 0.85 for contradiction. These are operational thresholds, not calibrated probabilities. Support is currently established by a single cited quote; reasoning that requires several passages jointly remains a limitation.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [DECISIONS.md](DECISIONS.md) for the complete explanation.

## 5. What was actually tested

The test suite exercises PDF parsing, real model inference, citation provenance, source isolation, deletion, API error handling and experiment scoring. The API integration fixture uses PGlite, a PostgreSQL build running in WebAssembly, with the pgvector extension and a PostgreSQL socket adapter. It executes the migration and queries; it is not an in-memory dictionary pretending to be a database. It is still not the same runtime as native PostgreSQL or hosted Neon.

The suite also uses controlled provider responses to test JSON parsing, safe errors, bounded retries and reuse of the same draft between reranked and verified variants. Those responses are test inputs, not live LLM observations or research results. The research scorer checks that withholding every claim does not produce a perfect factual score, and refuses unreviewed outputs.

React component tests check citation interactions and safe rendering of model text. TypeScript and the production build are checked. The CI definition is configured to use native PostgreSQL with pgvector when the source is published; that remote CI run has not happened yet.

The exact release commands and outcomes are recorded in [VALIDATION.md](VALIDATION.md). Docker image execution, real browser flows, live Gemini calls and hosted end-to-end behavior remain unverified.

## 6. Preliminary measurement

The included diagnostic set contains 24 authored evidence–claim pairs: eight supported, eight contradicted and eight insufficient. Labels were fixed before inference. The run used the downloaded quantized DeBERTa model on CPU.

| Class | Precision | Recall | F1 | Examples |
|---|---:|---:|---:|---:|
| Supported | 1.000 | 0.625 | 0.769 | 8 |
| Contradicted | 1.000 | 1.000 | 1.000 | 8 |
| Insufficient | 0.727 | 1.000 | 0.842 | 8 |

**Macro-F1: 0.870.** Three supported claims were incorrectly marked insufficient. There were no false-supported predictions in this particular small fixture set; that is not an estimate of performance on arbitrary PDFs. The measured evaluation took about 1.05 seconds including model loading on the implementation machine. This timing does not measure full upload, retrieval or hosted response time.

![Actual diagnostic results](../research/results/fixture_comparison.png)

The missed claims involved paraphrased age eligibility, a single study location, and a reported sleep duration. They demonstrate the cost of conservative withholding: useful, supported facts can disappear. Raw labels, scores and failures are included in `research/results/fixture_metrics.json`.

## 7. What the research has not established

We have not measured hallucination reduction, citation correctness or answer coverage on independently annotated, held-out questions. The 24 examples are development diagnostics. The small set has author selection bias and does not represent the variety of real scientific language, tables, populations or study designs.

The next controlled experiment compares dense RAG, reranked RAG and verification of the exact reranked draft. Reusing the draft isolates the filtering step. Independent reviewers must label retained claims and required answer facts. Report unsupported-claim rate together with answer coverage and abstention so a system cannot look excellent simply by refusing every question.

ALCE, FActScore, RARR, Self-RAG and SciFact already study related ideas. VeritasAI's current contribution is an inspectable engineering implementation and an evaluation protocol. A research contribution still requires a defensible methodological improvement or empirical finding. See [the protocol](../research/PROTOCOL.md) and [paper draft](../research/PAPER_DRAFT.md).

## 8. Privacy, limits and remaining work

The application uses workspace-scoped SQL queries, hashed capability tokens, SameSite/HttpOnly cookies, same-origin mutation checks, parameterized SQL, explicit upload/storage bounds, and source-aware deletion. A Gemini key entered in settings stays in tab memory and is not persisted by the application. Relevant passages leave the server when an external generator is selected.

The release needs account-based authentication and recovery, a restricted database runtime role, durable access controls suitable for a public service, stronger upload resource isolation, background ingestion and retention cleanup before a broad public launch. Limits also include no OCR, imperfect extraction of tables and columns, English-oriented models, no exhaustive conflict search and no robust multi-hop evidence combination.

These are documented engineering limits, not a completed security audit. See [SECURITY.md](SECURITY.md).

## 9. Next milestones

1. Resolve hosting permissions and validate a real deployed upload-to-deletion workflow using the published repository.
2. Test a real generator using a privately supplied key; verify provider errors and quota behavior in the hosted application.
3. Strengthen identity, database roles, resource isolation, and concurrent-request handling.
4. Collect a licensed corpus, freeze development and held-out splits, and conduct independent annotation.
5. Run the preregistered comparisons, analyze failure cases, and replace this preliminary report with measured end-to-end results.

The code was developed with AI coding assistance. The owner should run it, inspect the included examples and practice changing one retrieval or verification rule before an interview or research presentation.
