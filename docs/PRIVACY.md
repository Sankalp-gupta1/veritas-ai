# Where your data goes

**Reviewed: 16 October 2026.** This explains the current VeritasAI application, not every possible installation. The public website runs on Vercel and stores application data in Neon PostgreSQL. The review examined source code, official provider policies and 30 checks on the live API using fictional data. It was not an independent security audit.

## Can we promise that data will never leak?

**No.** Building the website ourselves does not remove hosting providers, database administrators, software vulnerabilities or the AI provider from the data flow. There is no end-to-end encryption: the application must read document text to search it and check claims. Someone with sufficient server or database access can technically read that content.

Using your own Gemini key still means using Google's AI. The key identifies the project making the request; it does not move Google's model onto your computer. A provider receiving data as part of a requested service is different from an unauthorized leak, but it is still a disclosure that you should understand.

VeritasAI checks **whether claims have document evidence**. That is a different problem from **keeping documents confidential**. Neither a citation nor a “supported” label is a privacy guarantee.

## What leaves your device?

| Information | Where it goes in this hosted app | What the application keeps |
|---|---|---|
| Uploaded PDF and its file name | Your browser → Vercel API → Neon database | Original PDF bytes, file name, size, content hash and page count |
| Extracted document text | Processed by models on the app server | Page text, searchable passages and numerical search vectors in PostgreSQL |
| Question or claim | Your browser → app server | Successful results include the question, answer, evidence, model information and timings in saved history |
| Gemini request, when selected | App server → Google Gemini API | The request includes your question, selected passage text, file names and passage IDs. Generated results are saved in your workspace. |
| Key entered in AI settings | This tab's app memory → app server → Google, for Gemini generation | No database field or browser-storage write for this key exists in the reviewed application code |
| Workspace access cookie | Browser and app server | The database stores a hash of the random token, not its original value |
| Request counters | App server → database | Rate-limit bucket identifiers, time windows and counts; these contain no document text |

“Local models” means models running **on the app server**. On the public website, that server is in the cloud, not inside your phone or browser.

### When is Google called?

- **Source excerpts:** no Gemini generation request. Retrieval and ranking run on the server.
- **Check a claim:** no Gemini generation request, even when Gemini is selected in settings. The server uses its local evidence checker.
- **Ask your documents with Gemini:** sends the question and up to five selected passages, including file names, to Google.
- **Compare methods with Gemini:** makes separate baseline and reranked generation requests. Verification reuses the reranked draft. Bounded retries can send a request again.

The current Gemini integration does not upload the raw PDF file to Google. That does **not** make its text harmless: a short passage, question or file name can still contain personal information. Previously saved answers are not included as conversation memory. The application does not fine-tune models on uploads.

Ollama is an optional self-hosting integration and is disabled in the public production configuration. For it to stay on your own machine, both `OLLAMA_URL` and the database must point to infrastructure you control. Choosing a cloud database or remote Ollama endpoint changes that boundary.

## Google's data-use rules

The [Gemini API terms](https://ai.google.dev/gemini-api/terms), checked on 16 October 2026, distinguish these cases:

- **Unpaid services:** Google may use inputs and outputs for product improvement, with human review. The terms warn against submitting sensitive, confidential or personal information.
- **Paid services:** prompts and responses are not used to improve Google's products. Gemini API paid status requires a Cloud project with active billing; owning a key alone does not establish it.
- **Regional exception:** paid-service data-use terms also apply to unpaid services in the EEA, Switzerland and UK.

Separately, Google's [abuse-monitoring policy](https://ai.google.dev/gemini-api/docs/usage-policies) describes retaining prompts, context and outputs for **55 days**, and authorized review of flagged content. A no-training provision does not mean zero retention or zero access.

The review did not inspect any user's Google billing, optional data-sharing settings or agreements. Read the current terms for your project before deciding what to send. No real Gemini key or live Gemini request was used for this audit.

## How the key is handled

The settings key is held in React state. The app does not write it to `localStorage`, `sessionStorage` or its database. Refreshing clears it from application state. The updated interface sends it to the backend only for Gemini generation, not for local excerpts or claim checks.

The browser uses the `X-Gemini-Key` header; the backend uses Google's `x-goog-api-key` header. It is not put in the URL or model prompt. HTTPS protects transport on the public site, but the backend still receives the key in memory.

The reviewed application logger does not intentionally record this key, document bodies or provider error payloads. This review did **not** inspect hosting log drains, crash dumps, every dependency, browser extensions or account permissions. It therefore cannot promise that a credential is impossible to expose. A server-level `GEMINI_API_KEY`, if configured by an installation owner, is a separate secret with a different lifetime.

## Access protection and its limits

The application uses random workspace tokens, hashed token storage, workspace-scoped database queries, parameterized SQL, same-origin checks and private/no-store API responses. Production cookies have `Secure`, `HttpOnly` and `SameSite=Strict`. Original PDFs are served through an authenticated route rather than a public file folder.

[Neon's security documentation](https://neon.com/docs/security/security-overview) describes encrypted database connections and encryption at rest. Those provider-managed controls do not prevent an authorized database role from reading records. This review did not audit the project's exact transport configuration, backup policy or administrative access.

The cookie is effectively your workspace access credential. Browser compromise or cookie theft can defeat that boundary. There is no account recovery, cross-device login, token-rotation screen or database row-level security policy in this prototype. The PDF parser runs inside the API process, with size limits but without a separate sandbox worker.

## What happens when you delete something?

| Action | Current behavior |
|---|---|
| Delete a document in the app | Removes its original PDF, pages and passages/vectors from the active database. Also removes **all saved answers in that workspace**, since they can contain source text. Other uploaded PDFs remain. |
| Delete the workspace through `DELETE /api/workspace` | Removes its workspace record, documents and saved answers, then clears the cookie. There is no whole-workspace delete button yet. |
| Clear cookies or use another browser | Removes access from that browser; it does **not** delete server data. |
| Let the cookie expire | The cookie lasts up to 90 days; this is **not** a database retention deadline. No automatic document cleanup job is implemented. |
| Download an evidence export | The exported copy is outside the app. You must delete or protect it separately. |

Deletion here means removal from the **active application database**. It cannot retract a request already sent to Google or guarantee immediate erasure from hosting logs, backups or provider systems. Their exact purge timelines were not verified. Rate-limit metadata is not linked by the workspace deletion cascade and can remain after deletion.

## What was actually checked?

The [live result](evidence/privacy-live-2026-10-16.json) records **30/30 passing assertions**. Two disposable workspaces and one fictional PDF were used. Checks covered unauthorized access, cross-workspace reads and deletion, original-file integrity, cookie flags, response caching, deletion behavior and cleanup. Both temporary workspaces were removed.

Additional component tests check that the browser sends a fictional key only for Gemini generation. A controlled HTTP test checks the exact outbound provider fields and that the key stays out of the URL, prompt and saved result. These are regression tests, not evidence of Google's internal behavior.

Not assessed: a full penetration test, all dependency vulnerabilities, every Git commit for secrets, provider account permissions, log-drain configuration, backup erasure, live Gemini processing or independent security certification. The tests cannot establish that no breach has ever happened.

See [validation](VALIDATION.md) for the dated software checks and [security notes](SECURITY.md) for implementation details.

## A sensible way to use the prototype

Start with public papers, the authored samples or documents you have permission to process. Remove personal identifiers from text **and file names** before uploading. Avoid passwords, identity documents, confidential contracts and private medical or financial records on this public prototype.

For stronger control, run the app, database and optional model on your own infrastructure; configure access and network restrictions, keep dependencies patched, and set a retention policy. This reduces external transfers but still does not justify a 100% security claim.

An accurate project description is:

> VeritasAI is an evidence-focused research assistant with server-side workspace isolation and optional external AI. Data handling depends on the hosting environment and selected provider. It does not offer a zero-leak guarantee.

## Code behind this explanation

- [API routes and access checks](../app/main.py)
- [Database schema and deletion relationships](../migrations/001_initial.sql)
- [Provider request construction](../app/generation.py)
- [Retrieval and comparison flow](../app/pipeline.py)
- [Browser request handling](../frontend/src/App.tsx) and [AI settings](../frontend/src/SettingsDialog.tsx)
- [Reproducible live privacy checks](../scripts/check_privacy_live.py)

Provider policies and deployment settings can change. The date at the top identifies the scope of this review.
