"""Apply the checked-in additive migration to the explicitly configured database."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
url = os.getenv("DATABASE_URL_UNPOOLED") or os.environ["DATABASE_URL"]
with psycopg.connect(url) as connection:
    with connection.cursor() as cursor:
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            cursor.execute(path.read_text(), prepare=False)
            print("Applied", path.name)
