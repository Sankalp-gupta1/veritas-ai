# What was actually tested

**Date:** 15 October 2026
**Website:** https://veritas-ai-v8lw.vercel.app/
**Reviewed application commit:** `9804b4d2ce28dc07bc9c429d3fecfca9ef08cf5b`

This record separates automated tests, real website checks and research measurements. Passing software tests does not prove that every answer is correct.

## Chat interface review — 16 October 2026

The interface now uses a centered question box, right-aligned question bubbles, a collapsible sidebar, recent-question shortcuts, and consistent charcoal surfaces. It remains a document research tool: each new question is independent.

[GitHub Actions run 38832182607](https://github.com/Sankalp-gupta1/veritas-ai/actions/runs/38832182607), for application commit `900fcf65fa0734dc689964e3c2592c49f8ac0cd5`, passed **23 Python tests, 7 React tests and the production build**. Five new React interaction tests cover sidebar collapse/source selection, the mobile drawer's focus and Escape behavior, successful submission and history reopening, Shift+Enter/IME handling, and retaining a failed request's draft. These component tests use a controlled API; they do not measure live model quality.

The deployed desktop UI was also checked in Chrome. Sidebar collapse and the source picker worked. Sending the fictional Cedar 12-point claim produced **Possible disagreement**, cleared the composer, and added the result to Recent questions. Its citation opened the actual highlighted PDF text. Settings, history and the evidence lab were inspected; the review found and corrected low-contrast settings text and chart labels.

The production HTML and JavaScript/CSS bundles returned HTTP 200, and health reported connected PostgreSQL and ready local models. The 84 API assertions below belong to the **15 October** run; they were not rerun for a presentation change. Full mobile viewport, screen-reader, real-provider and load testing remain outside this review.

## Automated checks

[GitHub Actions run 38737165149](https://github.com/Sankalp-gupta1/veritas-ai/actions/runs/38737165149) completed successfully against native PostgreSQL 17 with pgvector:

| Check | Result | What it establishes |
|---|---|---|
| Python suite | **23 passed in 7.09 seconds** | Real PDF parsing, local model inference, database integration, privacy, deletion, API errors, experiment scoring and regression coverage. |
| React component tests | **2 passed** | Citation clicks work; model-provided HTML is rendered as text. |
| TypeScript / Vite build | **Passed** | The frontend compiles and production bundles are generated. |
| Local Python lint | **Passed** | Ruff checks selected errors, imports and unused names. |
| Original PDF fixture review | **4 pages inspected** | The authored PDFs render legibly. |

The earlier local integration run used PGlite, a PostgreSQL-WASM build. The linked CI run additionally exercises native PostgreSQL. Provider-error and comparison-wiring tests use controlled responses: they are not live Gemini quality measurements.

## Public website checks

The live HTTP test uses fresh workspaces and only the fictional PDFs in `samples/`. It checks the real production alias, not a mock API. The command and raw results below record the completed run.

**84 of 84 HTTP/API checks passed.** Both workspaces created by the completed run were deleted successfully. [Full JSON result](evidence/live-api-2026-10-15.json).

| Flow | Observed result |
|---|---|
| Homepage and all required bundles | HTTP 200; HTML shell has `no-store`; lazy-loaded research page is available. |
| Database and local models | Healthy; real upload, retrieval, reranking and verification requests succeed. |
| Multiple and duplicate PDFs | Three samples stored; repeating the same PDF returns its existing ID. |
| Exact citations | Every inspected quote matches its physical page's normalized character offsets. |
| Supported / unknown / wrong-number claims | Supported fact retained; unsupported funding and incorrect quantity withheld. |
| Conflicting reports | Both supporting and contradicting evidence retained with `conflict` status. |
| Saved answers and originals | History reopens; a fresh HTTP client with the same cookie sees the PDFs; original bytes match. |
| Workspace privacy | Another workspace cannot read, search or delete these documents or read their saved answers. |
| Request protections | Missing workspace rejected with 401; missing request header and foreign origin rejected with 403. |
| Invalid inputs | Corrupt, encrypted, blank and oversized PDFs rejected; blank questions, empty selection and unknown sources rejected. |
| Missing generator | Clear missing-key error; source excerpts cannot masquerade as a generative comparison. |
| Evidence lab | Real 24-example diagnostic data returned and labelled. |
| Deletion | Removed PDF returns 404; saved source text is cleared from history; unrelated PDFs remain. |

To reproduce from the repository:

```bash
python scripts/smoke_live.py --base-url https://veritas-ai-v8lw.vercel.app --out tmp/my-live-check.json
```

This is 84 assertions across several workflows, not 84 independent model-quality examples. The approximately eight-minute command duration includes network round trips and deliberate sequential checks; it is not a per-answer latency benchmark. An earlier failed run is [preserved here](evidence/initial-conflict-failure-2026-10-15.json). An interrupted retest did not produce a final report and is not counted as a pass.

A completed request log is more useful than a green health badge: uploads perform real PDF extraction, embedding and database writes; subsequent claim checks run retrieval, reranking and NLI on those stored records.

## Desktop browser walkthrough

A real Chrome browser was used to inspect the live page and interact with the app:

- Imported all three sample PDFs through the website.
- Checked the supported 120-adult claim.
- Opened its exact highlighted text, moved to the second page and viewed the original PDF.
- After the fix, checked the 12-point improvement claim with both Cedar reports selected. The UI showed **Possible disagreement** and opened the corrected report under **Evidence to compare**.
- Refreshed the page after the cache fix: the website rendered, and the same three PDFs and two saved results returned.

- Reopened a saved answer and downloaded its evidence JSON; the export parsed successfully and retained the disagreement and counterevidence.
- Selected Gemini without a key: the API-key input is a password field, and the app showed an actionable missing-key error. No real API key was entered. Local source-excerpt mode was restored afterward.
- Opened the research dashboard and checked its charts, sample size and “not independently evaluated” labels.
- Cancelled deletion and confirmed that the test documents stayed. Then deleted the fictional Willow PDF: history became empty and the two Cedar PDFs remained.

This is a desktop walkthrough, not an exhaustive accessibility or cross-browser certification. Browser-extension metadata warnings were observed separately from application errors.

## Bugs found and fixed during the review

1. **A real disagreement was labelled only “contradicted.”** A multi-sentence paragraph mentioned different study groups, causing the local support score to fall below the existing threshold. User-entered claim checking now selects bounded exact sentence quotes for support and retains full paragraphs for counterevidence. Both the real-PDF regression and uploaded-document CI test pass. Thresholds were not lowered; this is still a fallible model.
2. **Some dark-theme screens retained light backgrounds.** The composer, evidence header, history and research cards now use compatible surfaces and readable text. The original document page intentionally remains paper-colored.
3. **A refreshed browser referenced old asset filenames after deployment.** The HTML shell now returns the current file with `Cache-Control: no-store, max-age=0`. A regression test sends old conditional cache headers and requires current HTML with HTTP 200. The deployed header and browser refresh were checked.

4. **Selecting Gemini implied a working connection.** The sidebar said “connected” even with an empty key. The label now says “selected”; saving settings does not claim that provider authentication succeeded.

## Research measurement — a different kind of test

The existing diagnostic experiment has **24 authored claim/evidence pairs**, macro-F1 **0.870445**, and **3 false-insufficient predictions**. Raw predictions and figures remain in `research/results/`. They have not been replaced or inflated because the software review passed.

The sentence-selection fix was developed after seeing a fixture failure. Its regression is therefore a development test, not an independent benchmark. No hallucination-reduction percentage is claimed.

## Not verified / not complete

- Live Gemini or Ollama generation, real provider quotas and generated-answer quality. The public server has no Gemini key configured.
- An independently annotated comparison of the three RAG variants on held-out questions.
- Docker build/execution or a Render deployment.
- Full mobile, keyboard, screen-reader and cross-browser coverage.
- Service-restart durability, cold-start performance, concurrent load and capacity.
- A complete security audit, account recovery, restricted runtime database role or production-grade upload isolation.

Testing was limited to fictional data. No existing user's private documents were used. Do not describe this prototype as fully production-hardened or universally accurate.
