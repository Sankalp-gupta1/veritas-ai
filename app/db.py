"""Short pooled transactions. Every user record is scoped to its workspace."""

import os
from contextlib import contextmanager
from functools import lru_cache

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config  # noqa: F401 -- loads .env before creating the pool


def configure(connection):
    register_vector(connection)
    connection.commit()


@lru_cache(maxsize=1)
def pool():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return ConnectionPool(
        url,
        min_size=0,
        max_size=4,
        timeout=15,
        open=True,
        kwargs={
            "row_factory": dict_row,
            "prepare_threshold": None,
            "connect_timeout": 10,
        },
        configure=configure,
        check=ConnectionPool.check_connection,
    )


@contextmanager
def connection():
    with pool().connection() as conn:
        with conn.transaction():
            conn.execute("SET LOCAL statement_timeout = '15000ms'")
            yield conn
