# Deployment and current status

## What is actually complete

- The source, model downloads, React production build and local API/model tests are implemented.
- A dedicated database named `veritas` and the schema were created in the connected Vercel-managed Neon project. Existing application tables were not changed.
- The cloud database is not yet connected to a verified live VeritasAI website.
- The connected Vercel account rejected project creation with **403 forbidden** for team `saritamit2004-2327s-projects` on 14 October 2026. There was no independently authenticated Vercel CLI session to use as a fallback.
- No VeritasAI GitHub repository was found. The connected GitHub tools can write an existing repository but do not provide repository creation in this session.
- Render was not connected in this session. A Render configuration file is supplied, but no Render deployment is claimed.

These are access/deployment blockers, not a completed public release. No placeholder URL should be presented as live.

## Docker on a server

The included `Dockerfile` builds the React frontend, installs Python packages, downloads pinned models, and runs FastAPI as an unprivileged user. Durable state lives in PostgreSQL, not the container filesystem.

For local use, `docker compose up --build` also starts PostgreSQL and runs migrations. The exposed database and app ports bind to localhost only.

For a cloud container host:

1. Supply a dedicated PostgreSQL database with pgvector.
2. Set `DATABASE_URL` as a secret. Use a pooled URL if your provider supports it.
3. Apply `python scripts/migrate.py` once using the direct migration URL.
4. Set `APP_ENV=production` behind HTTPS. This enables Secure cookies.
5. Optionally set `GEMINI_API_KEY` and `GEMINI_MODEL`. Otherwise users can supply a key in the UI.
6. Build and start the Docker image. The HTTP port is 8000.
7. Check `/api/health`, then test a real upload, retrieval, claim check, source download and deletion.

The CPU models require memory. Measure the container's actual footprint before selecting a small hosting plan. Do not assume a free instance can comfortably hold every model under concurrency.

## Vercel

The project contains the official FastAPI entrypoint configuration in `pyproject.toml`, a build hook that compiles React and downloads model files, and `vercel.json` with the function entrypoint and file inclusion rules.

After the team has project-creation and deployment access:

1. Create or connect the dedicated `veritas-ai` repository. Do not reuse an unrelated app repository.
2. Import it into the intended Vercel team with the **FastAPI** framework.
3. Add `DATABASE_URL` as a sensitive variable. Add `APP_ENV=production` and optional Gemini variables.
4. Apply migrations separately using a direct connection. The application does not mutate its schema on startup.
5. Deploy and inspect the real build logs. Model files plus Python dependencies must fit the selected plan's bundle/memory limits.
6. Test both the production alias and API routes. Review the team's deployment protection settings; a READY build does not by itself prove that everyone can open it.

The upload limit is intentionally below Vercel's documented 4.5 MB request-body limit. Larger uploads would require private object storage and direct uploads, not just a higher FastAPI setting.

Official references:

- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/limitations
- https://neon.com/docs/connect/connection-pooling

## Render

`render.yaml` describes a Docker web service and lists secret variables without including their values. Before using it, connect the intended Render account and confirm available plan capacity. The file's free-plan setting is a starting configuration, not a tested capacity guarantee. Run the database migration separately before starting the service.

## Publishing the repository

The source archive excludes credentials, local environments, model weights, temporary databases and private experiment runs. After creating an empty repository named `veritas-ai`, push the reviewed source:

```bash
git init -b main
git add .
git commit -m "Build VeritasAI evidence research workspace"
git remote add origin https://github.com/Sankalp-gupta1/veritas-ai.git
git push -u origin main
```

If you cloned an existing repository rather than opening the source ZIP, skip initialization and use its existing remote. Git may ask you to configure your author name and email before the first commit. Authenticate using GitHub's normal browser or credential-manager flow; never put a password or token in these commands.

That URL is the intended destination, not a claim that the repository already exists. The exact repository must exist and be authorized before pushing.

## Release checks

Verify a genuine PDF upload persists across a service restart, two independent workspaces cannot access each other's sources, original page downloads require the correct cookie, unsupported claims are withheld, and deletion removes source text from saved history. Also test real provider success, quota errors and frontend keyboard/mobile flows. Keep the private database migration credential out of the runtime where possible; use a restricted application role.
