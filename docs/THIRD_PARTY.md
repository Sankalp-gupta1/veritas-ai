# Models, libraries and attribution

## Downloaded models

Model weights are not included in the source archive. `scripts/download_models.py` retrieves immutable revisions and records a SHA-256 hash for every downloaded file. The observed manifest is included in `research/results/model_manifest.json`.

| Purpose | Download source | Revision |
|---|---|---|
| Embeddings | `minishlab/potion-base-8M` | `bf8b056651a2c21b8d2565580b8569da283cab23` |
| Reranking | `Xenova/ms-marco-TinyBERT-L-2-v2` | `b76bb5e1fefd66aa36cd108622d768e86c015ff1` |
| NLI verifier | `Xenova/nli-deberta-v3-xsmall` | `2a4f614a701367a02d51389039afc998faeda637` |

POTION's model card identifies the model as MIT-licensed. Its vectors are static, distilled embeddings; they are not a newly trained VeritasAI model.

The two Xenova repositories provide ONNX conversions of Sentence Transformers cross-encoders. Their upstream model cards identify Apache-2.0 licenses. The conversion cards do not independently declare a license in their metadata; preserve upstream attribution and review conversion/model terms before redistributing weights. The setup script downloads them from their public source rather than relicensing or bundling them as original project code.

Primary model sources:

- https://huggingface.co/minishlab/potion-base-8M
- https://github.com/MinishLab/model2vec
- https://huggingface.co/Xenova/ms-marco-TinyBERT-L-2-v2
- https://huggingface.co/cross-encoder/ms-marco-TinyBERT-L2-v2
- https://huggingface.co/Xenova/nli-deberta-v3-xsmall
- https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall

## Frameworks and services

Python/FastAPI, pypdf, NumPy, Model2Vec, ONNX Runtime, tokenizers, psycopg and pgvector power the backend. React, Vite, TypeScript, Lucide and Recharts power the UI. Matplotlib generates research figures and ReportLab creates the authored PDFs. Each dependency retains its own license.

Account and content protection use maintained libraries, not a new cryptographic algorithm. The installed package metadata identifies these licenses:

| Library | Role | Version | License |
|---|---|---|---|
| `argon2-cffi` | Argon2id password hashing | 25.1.0 | MIT |
| `cryptography` | AES-GCM authenticated encryption | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| `email-validator` | Email syntax and normalization | 2.3.0 | Unlicense |

`requirements.lock.txt` records the resolved production dependencies used by the tested Python 3.12 environment. Dependency versions and licenses do not establish that the complete application has passed a security audit.

Google Gemini is an optional external API. It is not an open-source model. `gemini-3.5-flash-lite` is the configured default; model availability and pricing can change. Official references checked on 14 October 2026:

- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing

Ollama is an optional self-hosted provider. The example `qwen3:4b` model must be installed separately, and its model terms remain applicable. It was not downloaded or benchmarked in this implementation session.

The local integration run used Electric's PGlite PostgreSQL-WASM engine with pgvector and its socket adapter because a native PostgreSQL service and Docker were unavailable. This was a real SQL/vector execution test. Subsequent GitHub CI used native PostgreSQL 17/pgvector, and the public Vercel application was exercised against its hosted database on 15 October 2026. Concurrency under load remains untested. See `VALIDATION.md`.

## Data

The Cedar and Willow PDFs and `research/fixtures.json` were authored for this project and are dedicated under CC0-1.0. Their contents are fictional. User-uploaded PDFs retain their owners' rights and are not redistributed by default.

SciFact is discussed as a future verifier benchmark; its data is not included. Its official repository distinguishes CC BY 4.0 claims/annotations, ODC-By 1.0 abstracts and Apache-2.0 code. Do not treat every dataset used by a code repository as sharing the code's license.

## AI assistance

This project was built with ChatGPT/Codex assistance for architecture, coding, tests, documentation and source research. The source, decisions and known failures are supplied so the owner can understand, explain, debug and extend the implementation. No claim is made that the models, frameworks or prior research were created by this project.
