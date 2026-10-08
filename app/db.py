from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.config import BASE_DIR, DATABASE_URL

SCHEMA_PATH = BASE_DIR / "app" / "schema.sql"

# Seconds to wait for Postgres before a page read gives up and falls back to
# the snapshot. libpq's minimum is 2.
CONNECT_TIMEOUT = 3


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL is empty or is not a PostgreSQL URL."""


def connect(url: str | None = None, *, read_only: bool = False) -> psycopg.Connection:
    url = DATABASE_URL if url is None else url
    if not url.startswith(("postgresql://", "postgres://")):
        raise DatabaseNotConfigured("DATABASE_URL must be a postgresql:// URL")
    conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=CONNECT_TIMEOUT)
    conn.read_only = read_only
    return conn


def init_schema(conn: psycopg.Connection) -> None:
    # No parameters, so psycopg sends the whole file as one multi-statement query.
    conn.execute(SCHEMA_PATH.read_text())
    conn.commit()
