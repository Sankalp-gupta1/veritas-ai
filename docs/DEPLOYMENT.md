# Running and releasing VeritasAI

**Existing website:** https://veritas-ai-v8lw.vercel.app/

**Repository:** https://github.com/Sankalp-gupta1/veritas-ai

## Current release status

The existing website was checked on 15–16 October 2026. The account/privacy upgrade is on the `privacy-accounts` branch and has separate automated tests. **The new account release has not been verified on production.** Do not treat the earlier website checks as evidence for the new sign-in or encryption flow. See [validation](VALIDATION.md).

On 27 October, the connected Vercel account returned no accessible teams. The earlier project request returned `403 — not authorized` for the project's team. Reconnect Vercel to an account with access to `veritas-ai-v8lw` before releasing. The application does not need the owner's Vercel password in chat.

A disposable Neon branch named `veritas-privacy-test-20261019` was created for migration rehearsal. Its migration request was not executed because automatic approval review failed with a model-capacity error. Production schema and secrets were not changed. The branch remains available for the release rehearsal; it contains a database snapshot and should be removed through an authorized cleanup after use.

## How the pieces connect

- **Vercel:** serves React assets and the same-origin Python/FastAPI API.
- **Neon PostgreSQL with pgvector:** keeps accounts, sessions, encrypted content, vectors and saved answers. Application storage does not depend on a temporary server filesystem.
- **Server CPU models:** downloaded at build time; used for retrieval, reranking and evidence checking.
- **Gemini, optional:** receives only user-reviewed requests after external AI is enabled. A configured key alone does not enable it. Self-hosted development can also use Ollama.

## Required private settings

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | Private PostgreSQL connection, preferably pooled, with pgvector enabled. |
| `DATABASE_URL_UNPOOLED` | Direct migration connection. Keep outside the web runtime when practical. |
| `VERITAS_VAULT_KEY` | A private, randomly generated 32-byte key encoded as base64. Required for accounts and encrypted content. |
| `APP_ENV` | `production` behind HTTPS; enables Secure cookies. |
| `GEMINI_API_KEY` | Optional server-side provider key. Never use a `VITE_` variable for secrets. |
| `GEMINI_MODEL` | Optional supported model name. |

Generate the vault key once with `python scripts/create_vault_key.py` after installing dependencies. It writes the key to the ignored local `.env`, protects that file on supported systems, and never prints the key. Transfer it using your hosting provider's private environment-variable settings. Keep a private backup. **Do not regenerate it on every deployment.** Replacing it makes existing encrypted data and email lookups unusable. Automated rotation is not implemented.

Preview deployments must use a separate test database and its own key. Never attach unreviewed preview code to production documents or production secrets.

## Release an existing installation safely

1. Read the [privacy limits](PRIVACY.md) and review the branch's passing CI. Keep a recoverable database backup and the current deployment reference.
2. Use a disposable database branch to run `python scripts/migrate.py`. This applies migration `001` and the additive `002_accounts_privacy.sql` in order. Re-running should leave the schema intact. The app does not migrate during startup.
3. Add a vault key to a preview environment, using that test database. Deploy `privacy-accounts` to preview, with Python 3.12 and Node 24.
4. Check `/api/health`, then run the account live-check command below. Walk through registration, recovery-code acknowledgement, upload, evidence, privacy settings, logout and sign-in in a browser. Never use real private documents for this rehearsal.
5. After rehearsal succeeds, apply migration `002` to the dedicated production `veritas` database and privately configure its vault key. This migration adds tables/columns; it does not bulk-encrypt existing data or drop records.
6. Release the reviewed commit and verify the production alias with the same account checks. A browser that owns an old workspace may explicitly import it at registration. Import encrypts that workspace's old records in one transaction and invalidates the old access cookie.

Do not merge and automatically release before the database and vault settings are ready. Once accounts have written encrypted content, rolling back to the old anonymous application is unsafe: it cannot interpret those records or enforce the new account boundaries. Prefer a forward fix, or restore a coordinated pre-release database snapshot and application version with a clearly communicated data-loss plan.

## Vercel build details

Import the repository with the **FastAPI** framework. `scripts/build.py` builds React, downloads pinned models and copies assets into root `public/` for Vercel's CDN. Keep this step: an earlier deployment served HTML without usable JavaScript until static asset copying was corrected.

The `/` and `/index.html` routes send `Cache-Control: no-store, max-age=0`; hashed assets remain cacheable. Private API responses are not cacheable. Uploads are limited to 4 MB before multipart overhead. Raising the application limit alone does not change platform request limits; larger PDFs need a separate upload design.

## Check a configured deployment

With Python dependencies installed, use a new output filename:

```bash
python scripts/check_accounts_live.py \
  --base-url https://YOUR-CONFIGURED-DEPLOYMENT.example \
  --out tmp/accounts-check.json
```

This command creates two fictional accounts, exercises access separation, encrypted-content status, history choices, disclosure gates and sign-out, then deletes its own accounts. It does not access existing users or call Gemini with an approved payload. It records pass/fail results without passwords or recovery codes. It does not establish browser usability, backup erasure, provider privacy or resistance to every attack. `smoke_live.py` and `check_privacy_live.py` are historical scripts for the earlier anonymous release.

## Docker on a computer or server

```bash
python -m pip install python-dotenv
python scripts/create_vault_key.py
docker compose up --build
```

Open `http://localhost:8000`. Docker builds React, downloads models, starts PostgreSQL/pgvector, applies migrations and starts FastAPI. Data uses a named volume. `docker compose down` stops containers without removing that volume. The example database password is for this localhost-bound setup only.

For a cloud container host, supply private database and vault settings, apply migrations, set `APP_ENV=production` behind HTTPS and expose port 8000. The image runs Python as an unprivileged user. Measure memory and concurrency before selecting a hosting plan. **Docker execution has not been tested in this environment.**

## Render and remaining checks

`render.yaml` supplies a Docker blueprint, including the required vault secret. Render has not been deployed. Supply secrets privately and complete the same migration, preview and verification steps.

Outstanding checks include live Gemini generation with approved fictional data, browser/mobile/keyboard testing of the new account screens, restart/restore behavior and concurrent load. Verified email, MFA, scheduled retention cleanup, a restricted runtime database role and key rotation remain future work.

Official references: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [function limits](https://vercel.com/docs/functions/limitations), [Neon pooling](https://neon.com/docs/connect/connection-pooling).
