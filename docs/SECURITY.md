# Security controls and remaining work

For the plain-English data flow, provider policies and deletion limits, read [Where your data goes](PRIVACY.md). This is a bounded research prototype, not an independently certified confidential-document service.

## Implemented controls

- Random 256-bit workspace tokens, stored as hashes, with HttpOnly and SameSite=Strict cookies. Production adds Secure.
- Workspace ownership checks on document lists, downloads, pages, retrieval, saved answers and deletion.
- Parameterized SQL, including selected document IDs. Model text never becomes a SQL command.
- Same-origin mutation checks plus a custom request header. These supplement workspace authentication; they do not replace it. No permissive cross-origin API policy.
- Private/no-store caching for API responses. Original PDFs are served through the authenticated API with a sandbox content-security policy, not public static paths.
- React renders document and model text as text, without `dangerouslySetInnerHTML`.
- Uploaded document instructions are untrusted. The generator has no execution tools.
- Browser-entered API keys are held in tab memory. The interface sends them only for Gemini generation, using headers. The reviewed code does not write them to browser storage or database records.
- The application error logger records request IDs and paths, not document bodies, credentials or raw provider error payloads. Hosting log drains and crash-dump settings were not audited.
- Database-backed request counters and storage limits bound the installation's intended use.
- Document deletion removes the active database's raw file, pages and vectors and clears all saved answers in that workspace. This is not a promise of immediate backup or provider erasure.
- Exact page/quote checks reject invented citations and references outside the selected workspace. This concerns evidence integrity, not confidentiality.

## Trust boundaries

The backend reads document text and holds database access. There is no end-to-end or application-level document encryption. Authorized infrastructure or database operators can technically read application content. PostgreSQL tables are separated by application query checks, not row-level security policies.

The workspace cookie grants access to that workspace. Someone who controls the browser or steals its cookie could access it. There is no account recovery, token-rotation UI, device management, organization sharing or automated retention cleanup. A 90-day cookie lifetime does not delete corresponding records.

Provider requests send questions, selected text, passage IDs and file names to the configured AI service. The Gemini key is visible to the app backend in memory before being relayed to Google. Local claim checks and source excerpts do not call Gemini. See the [privacy guide](PRIVACY.md#googles-data-use-rules) for provider-policy distinctions.

Files persist until explicitly deleted. Clearing browser data alone does not remove server content. The API supports `DELETE /api/workspace`; rate-limit metadata remains outside that deletion cascade. Provider logs, exports and backups have separate lifetimes.

## Upload processing

PDF reading occurs in the API process. Input and extraction limits reduce ordinary resource abuse but are not a complete defense against malicious parser inputs. Before broader deployment, move parsing into resource-limited worker processes, add malware scanning where appropriate, and enforce ingress limits for streamed/chunked requests.

The included sample data is fictional. Model weights are fetched from pinned public revisions during setup; search and verification inference run on the app server. No personal documents were used for validation.

## Verification and limits

The [16 October live privacy check](evidence/privacy-live-2026-10-16.json) passed 30 assertions against two new workspaces. It covered cookie flags, no-store responses, unauthorized and cross-workspace access, original-file integrity, deletion and cleanup. Provider-payload and browser-key regression tests use fictional keys and controlled responses.

This is not a full penetration test or a complete dependency, secret-history, cloud-permission or backup-retention audit. No real Gemini key was used. Passing these tests cannot prove that a leak is impossible or that no incident has occurred.

## Work before handling sensitive documents

1. Add accounts, recovery and credential rotation with an explicit access model.
2. Audit cloud permissions, introduce a restricted runtime database role and database row-level security.
3. Isolate PDF parsing and enforce streaming upload limits.
4. Set deletion/retention rules covering active records, rate-limit metadata, logs and backups; test restoration and purge behavior.
5. Add content-minimizing monitoring, abuse detection and incident procedures.
6. Complete independent security, accessibility and load reviews for the deployed configuration.

These are proposed improvements, not features that have already been delivered.
