from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import BASE_DIR, DATABASE_URL

SCHEMA_PATH = BASE_DIR / "app" / "schema.sql"


def database_path() -> Path:
    """Resolve the sqlite file location from DATABASE_URL."""
    prefix = "sqlite:///"
    if not DATABASE_URL.startswith(prefix):
        raise ValueError(f"Unsupported DATABASE_URL: {DATABASE_URL!r}")
    raw = DATABASE_URL[len(prefix):]
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / raw.lstrip("./")
    return path


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
