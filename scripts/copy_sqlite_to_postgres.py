"""Copy every row from the VM's SQLite database into PostgreSQL, keeping ids.

Usage:  DATABASE_URL=postgresql://... python -m scripts.copy_sqlite_to_postgres path/to/resume.db

One-shot: refuses to run if the target already holds a profile, so a second
run cannot collide with or duplicate rows. Applies the schema first, so it
works against a brand-new database.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

from app.db import connect, init_schema

# Parents before children, so every foreign key already has its target.
TABLES = [
    "person_profile", "contact_method", "role_experience", "experience_highlight",
    "project", "project_highlight", "skill", "skill_proficiency",
    "education_record", "certification", "achievement", "content_section",
    "tag", "entity_tag",
]

BOOLEAN_COLUMNS = {"is_primary", "is_current", "featured", "is_expected", "is_published"}
DATE_COLUMNS = {"start_date", "end_date", "date_earned"}
TIMESTAMP_COLUMNS = {"created_at", "updated_at"}


class TargetNotEmpty(RuntimeError):
    """The target database already has a profile; copying would collide."""


def _convert(column: str, value):
    if value is None:
        return None
    if column in BOOLEAN_COLUMNS:
        return bool(value)
    if column in DATE_COLUMNS:
        return date.fromisoformat(value[:10])
    if column in TIMESTAMP_COLUMNS:
        # SQLite's datetime('now') is UTC with no offset marker.
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return value


def copy_database(sqlite_path: Path, conn: psycopg.Connection) -> dict[str, int]:
    init_schema(conn)
    if conn.execute("SELECT EXISTS (SELECT 1 FROM person_profile) AS e").fetchone()["e"]:
        raise TargetNotEmpty("target already has a person_profile row; refusing to copy")

    src = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    try:
        for table in TABLES:
            rows = src.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            if rows:
                columns = rows[0].keys()
                conn.cursor().executemany(
                    f"INSERT INTO {table} ({', '.join(columns)}) "
                    f"VALUES ({', '.join(['%s'] * len(columns))})",
                    [tuple(_convert(c, r[c]) for c in columns) for r in rows],
                )
                # Copied rows carry explicit ids, which do not advance the
                # identity sequence; move it past them so new inserts don't collide.
                conn.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"(SELECT MAX(id) FROM {table}))"
                )
            counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        src.close()
    return counts


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.copy_sqlite_to_postgres path/to/resume.db")
    with connect() as conn:
        counts = copy_database(Path(sys.argv[1]), conn)
        where = f"{conn.info.host}/{conn.info.dbname}"
    print(f"Copied into {where}")
    for table, n in counts.items():
        print(f"  {table:<22} {n}")


if __name__ == "__main__":
    main()
