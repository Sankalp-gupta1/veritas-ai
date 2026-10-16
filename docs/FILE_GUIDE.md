# A simple guide to the files

You do not need to read the whole project at once. Start with the README, run the app, upload the fictional Cedar PDF, and check one claim. Then follow that request through the files below.

## The request in five stops

1. `frontend/src/App.tsx` collects the question and selected PDFs.
2. `frontend/src/api.ts` sends the request to Python.
3. `app/main.py` checks workspace access and validates input.
4. `app/pipeline.py` finds passages and coordinates the answer checks.
5. `frontend/src/ClaimCard.tsx` and `EvidencePanel.tsx` show the decision and source.

## Python application

| File | What it does | Read it when you want to… |
|---|---|---|
| `app/__init__.py` | Marks `app` as a Python package. | Understand Python imports. |
| `app/config.py` | Defines model names, paths, thresholds and limits. | Change upload limits or verification thresholds. |
| `app/db.py` | Opens and reuses PostgreSQL connections. | Understand where database queries run. |
| `app/documents.py` | Reads PDF pages, normalizes text, and creates passages with exact offsets. | Improve PDF extraction or chunking. |
| `app/ml.py` | Loads the local models and runs embedding, ranking and NLI inference. | Understand the actual machine-learning calls. |
| `app/generation.py` | Calls Gemini or a local Ollama server and validates the model's JSON. | Change the generator, prompt or retry behavior. |
| `app/verification.py` | Checks quote integrity, support and possible counterevidence. | Understand why a claim was kept or withheld. |
| `app/pipeline.py` | Connects retrieval, reranking, generation and verification. | Trace one complete answer or comparison. |
| `app/main.py` | Defines HTTP routes, ownership checks, uploads, saved answers and deletion. | Add an endpoint or debug an API error. |
| `migrations/001_initial.sql` | Creates the tables, vector extension and indexes. | Understand how information is stored. |

## React interface

| File | Plain-English purpose |
|---|---|
| `frontend/index.html` | The HTML page that loads React. |
| `frontend/src/main.tsx` | Starts React and imports the stylesheet. |
| `frontend/src/App.tsx` | Main workspace: library, uploads, selected files, questions, history and comparison. |
| `frontend/src/ClaimCard.tsx` | One claim, its status, citations and explanation. |
| `frontend/src/EvidencePanel.tsx` | Original PDF and extracted page text with the matching quote highlighted. |
| `frontend/src/SettingsDialog.tsx` | Model choice and private, tab-memory API-key input. |
| `frontend/src/Research.tsx` | Actual fixture graphs, saved-run count and recorded pipeline times. |
| `frontend/src/api.ts` | Shared HTTP helper and JSON download helper. |
| `frontend/src/types.ts` | Describes the data structures the interface expects. |
| `frontend/src/styles.css` | Base layouts, document viewer, charts and reduced-motion support. |
| `frontend/src/chat.css` | Chat appearance: charcoal colors, readable text, sidebar, composer, message bubbles and small-screen layout. |
| `frontend/src/vite-env.d.ts` | Makes Vite's environment types available to TypeScript. |
| `frontend/public/favicon.svg` | Small VeritasAI icon used by browser tabs. |
| `frontend/src/App.test.tsx` | Tests navigation, sending questions, saved history, keyboard input and retry drafts with controlled API responses. |
| `frontend/src/ClaimCard.test.tsx` | Tests citation clicks and safe rendering of model-provided text. |
| `frontend/vite.config.ts` | Development API proxy and frontend test/build settings. |
| `frontend/tsconfig.json` | TypeScript compiler rules. |
| `frontend/package.json` | Frontend commands and required packages. |
| `frontend/package-lock.json` | Exact resolved npm dependency tree; do not edit it by hand. |

TypeScript is JavaScript with descriptions of expected data types. It helps catch mistakes before the browser runs the code. The styles are ordinary CSS; no external design system is required.

## Scripts and tests

| File | What it does |
|---|---|
| `scripts/download_models.py` | Downloads pinned model revisions and records file hashes. |
| `scripts/migrate.py` | Applies the SQL schema to the configured database. |
| `scripts/build.py` | Downloads models, builds React and copies static assets to the Vercel CDN directory. |
| `scripts/create_samples.py` | Creates the fictional Cedar and Willow PDFs with ReportLab. |
| `scripts/smoke_live.py` | Checks a deployed site using fresh test workspaces; records results and deletes its own data. |
| `scripts/evaluate.py` | Runs the actual 24-pair local NLI evaluation and creates figures. |
| `tests/test_evidence.py` | Tests parsing, offsets, exact quotes, unknown sources and real model decisions. |
| `tests/test_generation.py` | Tests provider formatting, malformed output, safe errors and bounded retries using controlled HTTP responses. |
| `tests/test_delivery.py` | Checks that refreshing the website loads the current frontend after a deployment. |
| `tests/test_api.py` | Tests actual uploads, retrieval, workspace separation, history, deletion and comparison wiring. Requires a disposable database. |
| `tests/test_research.py` | Tests metric arithmetic and refusal to score missing independent labels. Its labels are authored test inputs. |
| `.github/workflows/ci.yml` | Configures GitHub to test against native PostgreSQL/pgvector and build the frontend. |

## Research and examples

| File | What it contains |
|---|---|
| `research/PROTOCOL.md` | Comparison design, independent review instructions, metric definitions and roadmap. |
| `research/PAPER_DRAFT.md` | Preliminary manuscript with existing research, measured fixture results and pending experiments. |
| `research/fixtures.json` | The 24 authored evidence–claim pairs and their expected labels. |
| `research/questions.example.json` | Four development questions with predefined required facts. |
| `research/run_experiment.py` | Calls the real comparison API and exports raw outputs plus a blind review sheet. |
| `research/score_experiment.py` | Scores independently reviewed runs and produces comparison graphs. |
| `research/results/fixture_metrics.json` | Actual diagnostic predictions, scores and failures. |
| `research/results/fixture_comparison.png` | Raster figure for the README and report. |
| `research/results/fixture_comparison.svg` | Scalable version of the same measured figure. |
| `research/results/model_manifest.json` | Model repository revisions and downloaded-file hashes. |
| `samples/cedar-trial-report.pdf` | Fictional two-page study with explicit facts. |
| `samples/cedar-reanalysis.pdf` | Fictional follow-up with potentially conflicting information. |
| `samples/willow-observation.pdf` | Fictional observational report for scope comparison. |
| `samples/manifest.json` | Sample titles, content hashes and licensing information. |

No included sample is a real scientific paper or customer document. Private experiment outputs belong in the ignored `research/private-runs/` directory. Publish only data that you have permission to share.

## Setup and deployment

| File | Purpose |
|---|---|
| `README.md` | Start here: what the app does and how to run it. |
| `requirements.txt` | Pinned direct Python application dependencies. |
| `requirements.lock.txt` | Fully resolved Python dependencies used by Docker. |
| `requirements-dev.txt` | Adds testing, PDF fixture generation and graphing tools. |
| `pyproject.toml` | Python project, test, lint and Vercel entrypoint settings. |
| `.env.example` | Placeholder configuration only. Copy locally and enter your own secrets. |
| `.gitignore` | Keeps secrets, downloaded models and generated local data out of Git. |
| `.dockerignore` | Keeps private and unnecessary files out of the Docker build context. |
| `Dockerfile` | Builds the frontend and runs Python as an unprivileged user. |
| `compose.yaml` | Starts a local app, PostgreSQL/pgvector and schema migration. |
| `vercel.json` | Configures the intended Vercel function and bundled files. |
| `render.yaml` | Starting blueprint for a Docker web service on Render. |
| `LICENSE` | MIT license for the project code, with separate upstream model terms. |

## Documentation

| File | Answers this question |
|---|---|
| `docs/USER_GUIDE.md` | How do I use each button and interpret each label? |
| `docs/ARCHITECTURE.md` | How do the website, models and database work together? |
| `docs/DECISIONS.md` | Why were these technologies and boundaries chosen? |
| `docs/FILE_GUIDE.md` | What is each file for? |
| `docs/PROJECT_REPORT.md` | What was built, measured and left unfinished? |
| `docs/evidence/` | Raw live API check results, including the first reproduced conflict failure. |
| `docs/VALIDATION.md` | Which checks actually ran, and which still need to run? |
| `docs/DEPLOYMENT.md` | Where is the live site, and how can I host this code? |
| `docs/SECURITY.md` | What data protections exist and what are their limits? |
| `docs/THIRD_PARTY.md` | Which models, packages, services and licenses are used? |

## A useful first code change

Add one new authored evidence–claim pair to `research/fixtures.json`, explain its expected label, then run `python scripts/evaluate.py`. Inspect any failure instead of changing the expected label to match the model. This teaches the most important habit in the project: compare behavior with independent evidence.
