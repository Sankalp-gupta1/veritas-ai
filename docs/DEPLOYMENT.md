# Where VeritasAI runs

**Live website: https://veritas-ai-v8lw.vercel.app/**
**Source code: https://github.com/Sankalp-gupta1/veritas-ai**

The website was manually deployed by the owner. Public HTTP checks and browser testing were performed on 15 October 2026. The website, API, PostgreSQL connection and local models respond. See [the validation record](VALIDATION.md) for tested flows and remaining limits.

## How the live pieces connect

- **Vercel project:** `veritas-ai-v8lw` serves the React interface and Python/FastAPI API.
- **PostgreSQL on Neon:** stores the original PDF bytes, pages, vectors, workspace tokens and saved results. These records do not depend on a temporary Vercel filesystem.
- **Local CPU models:** downloaded when Vercel builds the app; used for search, reranking and claim checks.
- **Optional Gemini:** not configured on the live server during this review. A user can enter their own key in AI settings for that tab. A self-hosted installation can also use Ollama.

The Vercel admin connector returned 403 for this team, so it could not inspect private deployment settings. This does **not** mean that the public website is unavailable. The public site and GitHub deployment status were checked independently. No deployment protection was disabled.

## Deploy this repository on Vercel

1. Import `Sankalp-gupta1/veritas-ai` and choose the **FastAPI** framework.
2. Use Python 3.12 and Node 24, matching the repository's CI environment.
3. Add the private environment variables below in Vercel's settings.
4. Run `python scripts/migrate.py` once with a direct database connection. The application does not modify its schema during startup.
5. Deploy. `scripts/build.py` builds React, downloads pinned models and copies the generated assets into the root `public/` directory for Vercel's CDN.
6. Open the production URL and check `/api/health`. Then test a real upload, a claim, its citation, history and deletion.

| Variable | What to enter |
|---|---|
| `DATABASE_URL` | Your private, preferably pooled PostgreSQL URL with pgvector enabled. |
| `DATABASE_URL_UNPOOLED` | The direct URL for migrations; keep this outside the web runtime when practical. |
| `APP_ENV` | `production` when the site uses HTTPS. This enables Secure cookies. |
| `GEMINI_API_KEY` | Optional server-side Gemini key. Never use a `VITE_` variable for secrets. |
| `GEMINI_MODEL` | Optional model name available to that key. |

The model files and `frontend/dist` are also bundled with the FastAPI function. A past deployment served HTML without usable JavaScript; the root `public/assets` copy fixes static asset delivery. Keep this build step when changing deployment configuration. The `/` and `/index.html` routes also send `Cache-Control: no-store, max-age=0` and return the current HTML even when a browser sends conditional cache headers. Hashed assets can remain cacheable; the small HTML shell must not point at a previous deployment.

Uploads are limited to 4 MB before multipart overhead. Increasing this number alone will not solve a hosting platform's request-size limit. Larger files need a separate upload/storage design.

## Check a deployed installation yourself

From the repository, with Python dependencies installed:

```bash
python scripts/smoke_live.py \
  --base-url https://veritas-ai-v8lw.vercel.app \
  --out tmp/my-live-check.json
```

This command creates fresh test workspaces, uploads only the included fictional PDFs, exercises public API flows, and removes its workspaces in a `finally` block. It never uses an existing user's cookie. It stops at the first failure and records whether cleanup succeeded. Choose a new report filename for each run. It does not test browser rendering, a paid provider, or service-restart durability.

## Docker on your computer or a server

```bash
docker compose up --build
```

Open `http://localhost:8000`. Docker builds React, downloads models, starts PostgreSQL with pgvector, applies the schema and starts FastAPI. Database data uses a named volume. `docker compose down` stops the containers without removing that volume. The example password is only for this localhost-bound setup.

For a cloud container host, supply your own database secret, run the migration, set `APP_ENV=production` behind HTTPS, and expose port 8000. The image runs Python as an unprivileged user. Measure memory and concurrency before selecting a hosting plan.

**Docker execution was not tested in this environment.** The files are a deployment option, not a claim that a Docker instance is already running.

## Render

`render.yaml` is a starting Docker blueprint. Render was not connected or deployed during this review. Confirm plan capacity, supply secrets privately, and run the database migration separately before using it. The live link above is the Vercel installation.

## Remaining release work

Test a real generator, mobile and keyboard access, service restart, concurrent uploads and cold starts. Add account recovery, retention controls and a restricted database runtime role before expanding to a broad public service. A successful health check or build does not replace these checks.

Official setup references: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [function limits](https://vercel.com/docs/functions/limitations), [Neon pooling](https://neon.com/docs/connect/connection-pooling).
