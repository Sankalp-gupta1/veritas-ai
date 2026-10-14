"""Small, explicit configuration. No keys are sent to the frontend."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(ROOT / "models")))
MAX_FILE_BYTES = 4_000_000
MAX_PAGES = 80
MAX_PAGE_CHARS = 60_000
MAX_DOCUMENTS = 20
MAX_WORKSPACE_BYTES = 30_000_000
MAX_TOTAL_BYTES = 200_000_000
EMBEDDING_DIM = 256
EMBEDDING_MODEL = "minishlab/potion-base-8M"
NLI_MODEL = "Xenova/nli-deberta-v3-xsmall"
RERANK_MODEL = "Xenova/ms-marco-TinyBERT-L-2-v2"
SUPPORT_THRESHOLD = 0.80
CONTRADICTION_THRESHOLD = 0.85
PRODUCTION = os.getenv("APP_ENV") == "production"
