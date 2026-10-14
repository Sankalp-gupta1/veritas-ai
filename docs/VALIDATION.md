# Validation record

**Date:** 14 October 2026  
**Scope:** the source package accompanying this record.

## Completed checks

| Check | Actual result | Important boundary |
|---|---|---|
| Python tests | **20 passed** in 3.65 seconds | Includes real PDF, embedding, reranking and NLI calls; provider-response tests use controlled HTTP data. |
| API/database integration | Upload, duplicate handling, retrieval, page offsets, history, deletion and workspace isolation passed | Disposable PGlite PostgreSQL-WASM database with pgvector and a socket adapter, not a hosted concurrency test. |
| Controlled comparison | Two generator calls; verified variant reused reranked draft and withheld an invented quote | A test of wiring with authored generator output, not a live model-quality result. |
| Research scoring | Missing labels rejected; undefined rates remain null; fact coverage and paired interval arithmetic checked | Controlled unit-test labels are not research annotations. |
| React tests | **2 passed** | Citation interaction and inert rendering of model-provided HTML text. |
| TypeScript and production frontend build | **Passed** | `tsc --noEmit` and Vite production build. |
| Python lint | **Passed** | Ruff checks for undefined/unused names, import rules and selected errors. |
| PDF fixtures | All **4 pages** rendered and inspected | Confirms readable fixture layout; does not test the browser PDF viewer. |
| NLI diagnostic experiment | **24 examples**, macro-F1 **0.870445**, **3 errors** | Authored development fixtures; not held-out RAG quality evaluation. |
| Cloud schema | Read-only check confirmed database `veritas`, pgvector **0.8.6**, schema version **1**, **7 tables** | Schema provisioned; no deployed web application is connected and tested. |

## Commands

The implementation environment ran these application checks after installing the pinned packages and models:

```bash
python -m pytest tests -q
npm test --prefix frontend
npm run build --prefix frontend
ruff check app scripts tests research
```

For the full Python suite, `DATABASE_URL` pointed to the disposable PostgreSQL-compatible fixture and `VERITAS_INTEGRATION_TEST=1` was set. Without this flag, API integration tests intentionally skip. Do not interpret a run with skipped integration tests as a completed database check.

To reproduce on native PostgreSQL, create a disposable database with pgvector, apply `python scripts/migrate.py`, download models, and run the tests with that flag. The GitHub Actions definition automates this using PostgreSQL 17 with pgvector once the repository is published.

`python scripts/evaluate.py` produced the included diagnostic results and PNG/SVG figure. Their raw predictions, thresholds and model manifest are kept in `research/results/`.

## Not verified yet

- Live Gemini or Ollama generation, real provider quotas and generated-answer quality.
- Independent human review of the three RAG variants on held-out questions.
- Docker image build and execution; Docker was unavailable in this environment.
- Native PostgreSQL CI run and hosted Neon application traffic.
- Browser visual, keyboard, mobile and accessibility flows; browser automation was unavailable.
- Vercel or Render deployment, public reachability, cold-start performance or capacity under concurrent load.
- Complete security audit, production user accounts, recovery or production-grade upload isolation.

The connected Vercel account returned 403 when asked to create the dedicated project. This is a real deployment blocker. The source is not described as an already live service.
