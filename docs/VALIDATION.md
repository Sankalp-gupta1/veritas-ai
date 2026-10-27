# What was actually tested

**Original public-release review:** 15 October 2026
**Latest account/privacy work:** 27 October 2026
**Website:** https://veritas-ai-v8lw.vercel.app/
**Reviewed application commit:** `9804b4d2ce28dc07bc9c429d3fecfca9ef08cf5b`

This record separates automated tests, real website checks and research measurements. Passing software tests does not prove that every answer is correct.

## Account and privacy upgrade — 19–27 October 2026

**Release state: branch implementation, not verified on the production website.** The new code is on [`privacy-accounts`](https://github.com/Sankalp-gupta1/veritas-ai/tree/privacy-accounts). Vercel access for the project returned 403; on 27 October the connected account listed no accessible teams. The database migration and production vault secret have not been applied by this upgrade. The older live results below do not test the new account system.

The initial account commit `374241b6ce882c8c947b7c71338d44f5bf115978` passed [GitHub CI run 39202087501](https://github.com/Sankalp-gupta1/veritas-ai/actions/runs/39202087501): **31 Python tests in 11.01 seconds, 12 React tests and the production build**, with a native PostgreSQL 17/pgvector service.

**Final application commit `5b352a71b4e277e2abca3f91755db7eccf10dc7b` passed [GitHub CI run 40434683240](https://github.com/Sankalp-gupta1/veritas-ai/actions/runs/40434683240): 32 Python tests in 12.33 seconds, 12 React tests and the production build.** Both migrations ran successfully on native PostgreSQL 17/pgvector in CI. The job status and decoded logs were inspected. [Machine-readable record](evidence/account-ci-2026-10-27.json).

The production alias was also checked on 27 October: its health response reported connected PostgreSQL and ready models, with no server Gemini key. It did not expose the new account/vault readiness fields, consistent with the earlier release remaining live. This was a read-only health request, not a repeated upload or privacy walkthrough.

The final local check on 27 October passed **24 Python tests**, with **8 database tests skipped** because this shell could not connect to a disposable PostgreSQL server. **12 React tests and the TypeScript/Vite production build passed.** These are automated implementation checks, not a live account walkthrough. The extra Python test covers security/no-cache headers on rejected requests.

| Area | What automated tests exercise |
|---|---|
| Accounts | Password confirmation, Argon2 hashes, encrypted email, private defaults, login/logout, recovery-code rotation and session expiry |
| Ownership | Separate accounts cannot read each other's originals, pages or history; old cookies cannot authorize private routes |
| Content encryption | Original PDF recovery, encrypted text/name/result records, fresh nonces, tamper rejection and row binding |
| External AI gate | Default block, exact-payload approval binding, cross-account/tampered approval rejection and one-use replay prevention |
| Privacy choices | History off by default, opt-in, temporary-answer override, export and source-aware deletion |
| Legacy upgrade | Explicit ownership claim encrypts the old workspace transactionally and invalidates its old token |
| Browser components | Matching passwords, recovery acknowledgement, clearing private state and explicit sharing approval |

Provider calls in these tests use controlled responses and fictional keys. They do not measure Gemini privacy or model quality. A live-check script, `scripts/check_accounts_live.py`, is included for a configured release; it has not yet passed against production. A local browser rendering attempt could not start: the environment had no Chromium executable, and its browser download returned an invalid archive. No new desktop/mobile screenshots or browser-flow pass are claimed. Component tests still ran successfully.

A disposable Neon branch was created for a migration rehearsal. Automatic approval review failed with a model-capacity error before the SQL ran. No successful Neon migration is claimed. See [deployment steps](DEPLOYMENT.md) for the remaining release gates.

## Historical checks of the earlier anonymous-workspace release

The following records retain their original dates, counts and limits. Their scripts apply to that earlier release.

## Privacy review — 16 October 2026

Reviewed the data flow at application commit `bea266a8426b7af9e5f82d29fac5869f76c20eff`, then added the privacy explanations and browser-key handling change described below. The review covered the code, official provider policies and a focused live run. It did not inspect existing users' documents or use a real Gemini key.

**30/30 live assertions passed.** [Raw result](evidence/privacy-live-2026-10-16.json). Both fresh test workspaces were deleted. The live server reported connected PostgreSQL, ready local models and no configured server Gemini key.

| Check | Observed result |
|---|---|
| Authentication and request origin | Anonymous document access rejected; missing app header and foreign-origin mutations rejected |
| Workspace separation | Other workspace could not read the PDF, page or saved answer, query the selected document, or delete it |
| Cookie and caching controls | Secure, HttpOnly and SameSite=Strict cookies; no-store API and PDF responses |
| Original-file delivery | Downloaded bytes matched the fictional upload; PDF response included a sandbox policy |
| Deletion | Owner deleted the PDF; it became unavailable and saved source text was cleared from history |
| Sensitive static paths | Configuration and Git metadata paths returned 404 |
| Cleanup | Both disposable workspaces returned HTTP 204 on deletion |

The interface previously attached an entered Gemini key to local requests as well as Gemini requests. The update sends it only for Gemini generation, reducing unnecessary transfer to the backend. It also explains server storage in the sidebar/settings and removes an unsupported “documents are safe” assurance from provider network errors.

Local validation after this change: **10 React tests passed**, including three key-handling cases; **6 provider tests passed**, including exact outbound payload checks with a fictional key. These controlled tests do not establish Google's internal data handling. After publication, [GitHub CI run 38863177373](https://github.com/Sankalp-gupta1/veritas-ai/actions/runs/38863177373) for commit `f42766a3830a533f4af9c0d556897d67c2c636d8` passed **23 Python tests in 6.12 seconds, 10 React tests and the production build**, using native PostgreSQL/pgvector. The historical runs below retain their original counts and dates.

Vercel reported a successful deployment for this commit. A desktop browser confirmed the live sidebar storage label and the settings notices for server storage, lack of end-to-end encryption, and Gemini transfers. The key field stayed empty. [Screenshot of the live settings](evidence/privacy-settings-2026-10-16.jpg).

Reproduce the live check with a fresh report path:

```bash
python scripts/check_privacy_live.py --base-url https://veritas-ai-v8lw.vercel.app --out tmp/privacy-check.json
```

This checks exposed application boundaries, not backup erasure, cloud permissions, log drains, a complete dependency/secret-history audit or resistance to every attack. The result does not prove that a leak is impossible. See [the privacy guide](PRIVACY.md).

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
- A complete security audit, restricted runtime database role or production-grade upload isolation. Account recovery in the new branch is tested separately above and is not a completed hosted recovery walkthrough.

Testing was limited to fictional data. No existing user's private documents were used. Do not describe this prototype as fully production-hardened or universally accurate.
