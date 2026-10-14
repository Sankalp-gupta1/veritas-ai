# Deployment and current status

## What is actually complete

- The source, model downloads, React production build and local API/model tests are implemented.
- A dedicated database named `veritas` and the schema were created in the connected Vercel-managed Neon project. Existing application tables were not changed.
- The cloud database is not yet connected to a verified live VeritasAI website.
- The connected Vercel account rejected project creation with **403 forbidden** for team `saritamit2004-2327s-projects` on 14 October 2026. There was no independently authenticated Vercel CLI session to use as a fallback.
- The source is now public at https://github.com/Sankalp-gupta1/veritas-ai. The repository was created and uploaded manually on 14 October; setup files omitted by that upload are restored in the following source update.
- On 15 October, the Vercel connection still returned 403 when listing this team's projects. The GitHub commit had no deployment status. The import screen's “Production and Preview” setting selects environments; it does not confirm a successful deployment.
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

After the connected account has access to the intended team:

1. Use the existing dedicated `Sankalp-gupta1/veritas-ai` repository.
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

The repository is published. To work on it, clone it rather than making another repository:

```bash
git clone https://github.com/Sankalp-gupta1/veritas-ai.git
cd veritas-ai
```

Follow the README to install dependencies and configure your private environment. The repository excludes credentials, local environments, model weights, temporary databases and private experiment runs. Authenticate future pushes using GitHub's normal browser or credential-manager flow; never put a password or token in shell commands.

The repository URL is confirmed. No public application URL is claimed until the deployed upload, retrieval and deletion flow has been checked.

## Release checks

Verify a genuine PDF upload persists across a service restart, two independent workspaces cannot access each other's sources, original page downloads require the correct cookie, unsupported claims are withheld, and deletion removes source text from saved history. Also test real provider success, quota errors and frontend keyboard/mobile flows. Keep the private database migration credential out of the runtime where possible; use a restricted application role.
