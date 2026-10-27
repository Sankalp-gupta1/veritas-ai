# Security design and honest limits

Read [Privacy](PRIVACY.md) first for a plain-English explanation. These controls reduce defined risks; they do not establish zero risk or independent certification.

## Threats addressed

| Threat | Implemented control | Remaining boundary |
|---|---|---|
| Another user guesses a record ID | Every private route derives workspace ownership from a server session; queries scope documents, pages, vectors, answers and deletion. | No database row-level security yet. |
| Password database disclosure | Argon2id: 64 MiB, three iterations, parallelism one; library-generated salts; 15–128 character passphrases. | MFA, password-breach checks and email ownership verification are not implemented. |
| Stolen database content | AES-256-GCM content fields; fresh 96-bit nonces; row/field-associated data; separate vault secret. | Runtime compromise or key + database compromise can reveal content; vectors and metadata remain readable. |
| Session theft or a shared device | 256-bit opaque session tokens, only hashes in DB, HttpOnly/Secure/SameSite=Strict production cookies, idle/absolute expiry, revocation and visible lock/logout. | A compromised browser or active stolen cookie can still act as the user until revocation/expiry. |
| Cross-site requests | Same-origin mutation checks, required custom header, strict cookies, no permissive CORS. | Same-origin script compromise remains serious. |
| Browser injection/tracking | Text rendering, restrictive CSP, no third-party analytics/fonts/scripts, no-store private responses, no-referrer, sandboxed private PDF responses. | Dependencies and browser extensions are outside that guarantee. |
| Silent external-AI disclosure | Server-side default block, redacted/pseudonymous preview, one-use hashed approval token tied to payload/preferences/workspace, ten-minute expiry. | Masking is heuristic; users must review; in-flight requests cannot be recalled. |
| Unwanted answer retention | History off by default; temporary-answer override; encrypted saved results; deletion/export UI. | Uploaded PDFs persist, backups/exports/provider logs are separate. |
| Sensitive diagnostics | Generic validation errors without echoed input; application logger stores request ID/path, not raw exceptions, prompts or keys. | Provider/platform crash dumps and log drains have not been audited. |
| Abuse | Database-backed per-identifier/account and global rate limits, file/page/storage limits. | Global limits can cause denial of service; no independent WAF/load review. |

## Authentication implementation

`app/auth.py` implements this small Python application's account flow using the maintained `argon2-cffi` library. It uses opaque database sessions rather than a custom JWT format. The Argon2 parameters exceed the minimum in the [OWASP password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Session decisions follow [OWASP's session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Email is encrypted and indexed by a keyed fingerprint. Password comparison, password changes and recovery are serialized against the account row. Password recovery uses a 256-bit random code shown once; only its hash persists. Changing/resetting a password invalidates sessions and rotates recovery. Generic login failures do not disclose whether an email exists. Registration errors are intentionally nonspecific, but the service is not claimed immune to account enumeration or timing attacks.

Sessions expire after seven days absolutely and after thirty minutes without an authenticated request. The UI also clears private state after inactivity. Production uses `__Host-veritas_session`; development uses `veritas_session` on localhost. Both are HttpOnly and SameSite=Strict; production requires HTTPS/Secure. Legacy anonymous cookies cannot authorize private API routes. They can only claim the same browser's unowned old workspace during explicit registration.

## Vault implementation

`app/vault.py` uses the [cryptography AESGCM implementation](https://cryptography.io/en/stable/hazmat/primitives/aead/). It creates a new random nonce for every encrypted field and binds the workspace, row and field through associated data. Modified ciphertext or a different identity fails authentication. Writes fail closed if `VERITAS_VAULT_KEY` is missing or invalid.

Never regenerate the production key during build, startup, migration or deployment. Keep it out of Git, frontend bundles, SQL records, screenshots and logs. Keep a secure backup. Automated key rotation is not implemented. The key also protects email lookup fingerprints, so key replacement requires a planned content and account-index migration.

The application decrypts records in memory. It is not E2EE, zero-knowledge or confidential computing. Printed page labels, vectors, hashes, structural metadata and aggregate result metadata are not encrypted by this layer.

## Disclosure implementation

`app/privacy.py` masks common email/phone/key/secret patterns and replaces source filenames with neutral labels. Preview tokens contain no text and are stored hashed with a digest of the approved payload, operation and privacy version. A changed question, document set, model or preferences invalidates approval. Tokens are consumed atomically; replay fails. No text or API key is persisted in the consent table. Recomputing a changed evidence payload requires new approval.

`app/pipeline.py` refuses Gemini generation without prepared disclosure data. Restored placeholders go through original exact-quote and semantic checks. Provider retry requests contain the same approved content. The generator has no browser, shell, arbitrary URL or database tools; uploaded instructions are treated as untrusted data.

## Data deletion and concurrency

Document deletion, workspace clearing and answer saving lock the workspace row. Saving checks source existence before writing encrypted history. History preferences are re-read at save time, so disabling history applies to unfinished answers too. Clearing history does not promise to cancel a different in-flight request. Deleting an account cascades through its workspace and private records. Retention limits and backup caveats are documented in [Privacy](PRIVACY.md).

## Tests and release requirements

Tests cover cipher tampering/row substitution, missing-key refusal, sensitive-input validation errors, masking/restoration, private defaults, registration/confirmation, recovery/revocation/expiry, original PDF recovery, encrypted DB records, cross-account access, history opt-out and disclosure bypass/replay. Frontend tests cover matching passwords, recovery-code acknowledgement, session clearing and approval before Gemini calls.

Use a disposable PostgreSQL/pgvector database for integration tests. Do not point the test suite at production. Production smoke tests use only newly created fictional accounts and remove them in `finally` blocks. See [Validation](VALIDATION.md) for actual outcomes, rather than treating this checklist as proof of passing.

## Next security work

Verified email plus MFA/passkeys; restricted runtime database role and RLS; KMS-backed key rotation; isolated PDF parsing and streamed-body ingress limits; scheduled retention and tested backup purge; dependency/cloud-permission review; independent penetration, load and accessibility tests. No certified compliance or “100% leak-proof” claim is made.
