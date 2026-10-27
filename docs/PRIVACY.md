# Your privacy, in plain English

**Account/privacy release, 19 October 2026.** This document describes the code in this release. [Validation](VALIDATION.md) records what has actually been tested and deployed. The hosted architecture is React/FastAPI on Vercel and PostgreSQL on Neon.

## What we can honestly promise

VeritasAI gives you account access controls, encrypted content storage, external-AI blocking, a review before sharing, and deletion/export controls. These are implemented behaviours, not a “privacy score.”

**We cannot promise zero leaks. This is not end-to-end encryption.** The app server decrypts your documents to search and check evidence. Someone who compromises the running server or obtains both the database and its vault key could read content. An authorized database operator can still read unencrypted metadata and vectors. A compromised browser, extension or stolen session can also defeat account protections.

## What happens when you create an account?

1. Enter your email, a passphrase of 15–128 characters, and the same passphrase again.
2. The server stores an Argon2id password hash, not the password. Each account gets its own workspace.
3. Your email is encrypted. A separate keyed fingerprint finds your account when you sign in.
4. A random recovery code is shown once. Save it privately. Its hash is stored; the original code is not.
5. **External AI and answer history start off.** Uploads still persist until you delete them.

Email is a sign-in identifier; ownership is **not verified**. We do not send verification or reset emails. Recovery needs your email and recovery code. Losing both password and recovery code can mean losing account access. MFA, passkeys and organization sharing are not implemented.

If this browser has an older anonymous workspace, account creation offers to move it into your new account. The transaction encrypts its old document and answer records and invalidates its old access cookie. Unclaimed legacy records remain inaccessible through the new private API; they are not silently assigned to an email address.

## Where each kind of data goes

| Data | Processing and storage |
|---|---|
| Original PDF and filename | Browser → app server → encrypted fields in PostgreSQL. |
| Extracted pages and passages | Processed in server memory; text is encrypted before storage. |
| Search vectors | Stored as readable numerical vectors for database search. Treat them as sensitive derived data, not anonymous data. |
| Question and answer | Processed on the server. Written to encrypted answer history only when history is on and the question is not temporary. |
| Gemini request | Only after a one-use disclosure approval: reviewed question, selected passages, pseudonymous source labels and passage IDs → Google. |
| API key entered in settings | Tab memory → app server → Google, only during generation. Not put in a URL, prompt, database, localStorage or sessionStorage by the app. |
| Email | Encrypted email field plus a keyed lookup fingerprint. |
| Password and recovery code | Argon2id password hash and a SHA-256 hash of the random recovery code. |
| Session | Random token in an HttpOnly cookie; only its hash is stored in the database. |
| Privacy activity | Fixed action names and times. No questions, document text, emails, keys or IP addresses. |
| Operational metadata | IDs, relationships, content hashes, sizes, page numbers/labels, offsets, timings, model/verdict counts and request counters. Not all metadata is application-encrypted. |

“Local models” on the live website means **models on the hosted app server**, not models inside your laptop. The app has no advertising or third-party analytics scripts. Hosting providers can still produce operational logs; those provider-level settings have not been independently audited.

## What encrypted storage means

AES-256-GCM encrypts original PDFs, filenames, page/chunk text, saved questions, full saved answers/evidence, and email fields before database writes. Every write uses a fresh random nonce. The account/workspace, record and field identity are authenticated with the ciphertext, so copying encrypted data into a different record fails validation.

The vault key is a server secret stored separately from database records. Missing or malformed keys prevent encrypted writes; the app never falls back to plaintext for new content. The Privacy Center reports whether your current documents and saved answers have been encrypted.

This protects content against a database-only disclosure when the attacker does not also obtain the vault key. It does not hide search vectors or all metadata, and does not protect against a compromised running application. It is not zero-knowledge encryption. Key rotation, KMS-backed keys and independent security review remain future work.

**Owners:** keep a secure backup of `VERITAS_VAULT_KEY`. Do not replace it on redeployment. Losing the key makes encrypted records unreadable. Keep development, test and production secrets separate.

## How external-AI review works

**External AI blocked** is the default, enforced in Python. Supplying an API key or directly calling the API does not bypass it.

To use Gemini:

1. Enable **Allow reviewed Gemini requests** in Privacy Center.
2. Enter your key in AI settings and select Gemini.
3. Ask a question. The app first retrieves passages locally and opens a preview. It has not called Gemini yet.
4. Read the exact question and passages that will be shared. Source filenames are replaced with labels such as “Source 1.” Obvious email addresses, phone numbers and common secret patterns are masked.
5. Check the approval box and submit, or cancel.

The server binds approval to the account workspace, question, selected documents, model, method, current privacy preferences and outgoing payload. Approval expires after ten minutes and can be used once. Editing the question, changing privacy settings or reusing the token requires a new preview.

The provider also receives the app's fixed research instructions and response schema. Comparisons show both generation payloads; the verified method reuses the reranked draft. Bounded provider retries may send the same approved payload again. The app does not upload the raw PDF to Gemini or send previous answers as chat memory.

Masking is a **best-effort reduction**, not anonymization. It can miss names, addresses, document titles inside text, uncommon secrets or identifying combinations. It can also mask an innocent number. Read the preview. Restored placeholders are checked against original local evidence so that citation offsets still refer to your original page.

Turning external AI off blocks new requests and invalidates pending previews. It cannot recall a request already in flight or erase content already received by Google.

### Google's separate terms

The [Gemini API terms](https://ai.google.dev/gemini-api/terms), checked on 19 October 2026, distinguish unpaid and paid use. Unpaid content can be used for product improvement and human review; the terms say not to send sensitive, confidential or personal information. Paid-service prompts/responses are not used to improve Google's products. Gemini API paid status requires a project with active billing; possessing a key alone is not enough. Regional provisions also apply in the EEA, Switzerland and UK.

Google's [abuse-monitoring documentation](https://ai.google.dev/gemini-api/docs/usage-policies) describes retention of prompts, context and outputs for 55 days and review of flagged content. No-training terms do not mean zero retention. Check your project's current terms, region, billing and optional data-sharing settings yourself.

The app cannot inspect or control Google's internal processing. No live Gemini key was used in the automated privacy tests.

## Sessions, locking and shared computers

Production sessions use Secure, HttpOnly, SameSite=Strict host-only cookies. Only hashed random tokens are stored. The server rejects sessions after 30 minutes without an authenticated request or seven days from creation. The interface also locks after 30 minutes without user activity and clears its private React state. Active tabs can refresh a session while you work.

**Sign out** removes the current server session. **Sign out everywhere**, password change and account recovery revoke old sessions. A password change also replaces the recovery code. Browser tabs receive a sign-out notification; an expired/revoked token cannot open private API routes.

Network failures can prevent immediate server-side logout. An offline screen lock is not remote revocation. On a shared computer, confirm logout succeeded and close the browser. Downloads remain on that computer unless you remove them.

## History and deletion

| Action | Effect on the active database |
|---|---|
| History off | New questions/results are not added to answer history. Existing saved answers remain. Uploads remain. |
| Temporary answer | Does not save that answer even if history is enabled. |
| Clear history | Deletes saved questions, answers and evidence. PDFs remain. |
| Delete one PDF | Deletes its PDF, pages and vectors, and all saved workspace answers that may contain source text. |
| Delete workspace data | Deletes all PDFs, pages, vectors and saved answers; your account remains. |
| Delete account | Requires the current password and explicit UI confirmation; removes the workspace, account, sessions, content, answer history, consents and privacy activity. |
| Clear cookies | Signs you out locally. It does not delete stored documents. |
| Export data | Downloads private text and answers. Original PDFs remain available through signed-in download routes. Exports are outside the app's deletion controls. |

Documents have no automatic expiry schedule. Privacy activity is displayed for 30 days; old entries are cleaned on later activity for that workspace. Expired sessions/consents and old rate counters are cleaned opportunistically, not by a guaranteed wall-clock purge job. Expiry checks block access before cleanup. Rate-counter metadata can outlive account deletion until cleanup.

Deletion affects the **active database**. Provider backups, operational logs, local exports and content already sent to Google have separate lifetimes. An application deletion cannot guarantee immediate removal from those systems. Older database snapshots may contain plaintext records from before this encryption release.

## What still needs work

The implementation has focused automated tests, not an independent penetration test or compliance certification. Database row-level security and a restricted runtime role, isolated PDF workers, verified email, MFA/passkeys, key rotation, scheduled retention and backup-erasure validation remain future work. Infrastructure permissions, log drains, incident history and every dependency have not been exhaustively audited.

An accurate description is:

> VeritasAI is an evidence-focused research assistant with account isolation, encrypted content storage and server-enforced review before external AI disclosure. Users control history, exports and active-data deletion. The server processes documents, so it is not end-to-end encrypted or guaranteed leak-proof.

See [security implementation](SECURITY.md), [file guide](FILE_GUIDE.md), and [dated validation](VALIDATION.md).
