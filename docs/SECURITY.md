# Privacy, boundaries and remaining work

This is a bounded research prototype. Do not treat its controls as an enterprise security certification.

## Implemented

- Random 256-bit workspace tokens, stored as hashes, with HttpOnly and SameSite=Strict cookies. Production adds Secure.
- Workspace ownership checks on document lists, downloads, pages, retrieval, saved answers and deletion.
- Parameterized SQL, including selected document IDs. Model text never becomes a SQL command.
- Same-origin mutation checks plus a custom request header. No permissive cross-origin API policy.
- Private no-store caching for API responses. Original PDFs are served through the authenticated API, not public static paths.
- React renders document and model text as text, without `dangerouslySetInnerHTML`.
- Uploaded document instructions are untrusted. The generator has no execution tools.
- API keys are held in browser memory, passed in headers, and excluded from database records and application logs.
- Server logs record request IDs and paths, not document content, provider error payloads or credentials.
- Database-backed request counters and storage limits bound the installation's intended use.
- Deletion removes raw files, text and vectors and clears saved answers containing source text.
- Exact page/quote checks reject invented citations and references outside the selected workspace.

## Important limits

The workspace token grants access to that workspace. Someone who controls your browser or steals its cookie could access it. There is no account recovery, token rotation UI, device management, organization sharing or automated retention cleanup.

Files persist until deleted; clearing a browser cookie alone does not delete the corresponding server data. Export what you need and remove documents before abandoning the workspace. The API also supports `DELETE /api/workspace`.

PDF reading occurs in the API process. Input and extraction limits reduce ordinary resource abuse but are not a complete defense against malicious parser inputs. Before broad public release, move parsing into resource-limited worker processes, add malware scanning where appropriate, and enforce ingress limits for streamed/chunked requests.

There is no database row-level security or formally verified tenant model. Query-scoping tests cover the exposed API, but a restricted database role and RLS are still desirable defense in depth.

Provider calls send relevant document excerpts and the user's question to that provider. Free Gemini-tier data-use terms may differ from paid tiers. The app warns before using Gemini; consult the provider terms for your documents.

The included sample data is entirely fictional. No company data, real customer records or credentials are part of the source package. Model weights are fetched from pinned public revisions at setup time.

## Before a broad public release

Add user accounts and recovery, strict ingress/body streaming limits, a restricted database role, RLS, isolated PDF workers, operational monitoring, backup/restore drills and a documented retention policy. Run browser security and accessibility checks on the deployed origin. Verify that upload, delete and model-provider behaviour match the intended deployment settings.
