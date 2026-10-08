from __future__ import annotations

import sqlite3

import pytest

from app import repository
from app.db import connect
from scripts.copy_sqlite_to_postgres import TABLES, TargetNotEmpty, copy_database


def _source_counts(path):
    conn = sqlite3.connect(path)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    finally:
        conn.close()


def test_every_table_copies_with_matching_counts(sqlite_source, empty_db):
    with connect(empty_db) as conn:
        assert copy_database(sqlite_source, conn) == _source_counts(sqlite_source)


def test_ids_and_links_survive(sqlite_source, empty_db, tmp_path):
    with connect(empty_db) as conn:
        copy_database(sqlite_source, conn)
        assert conn.execute("SELECT id FROM person_profile").fetchone()["id"] == 7
    data, source = repository.load_profile(database_url=empty_db, snapshot_path=tmp_path / "s.json")
    assert source == "live"
    assert [r["highlights"] for r in data["experience"]] == [["Now bullet"], ["Then bullet"]]
    assert data["experience"][0]["is_current"] is True
    assert data["experience"][0]["date_range"] == "Jun 2026 – Present"


def test_inserts_after_copy_do_not_collide(sqlite_source, empty_db):
    with connect(empty_db) as conn:
        copy_database(sqlite_source, conn)
        new_id = conn.execute(
            "INSERT INTO experience_highlight (experience_id, body) VALUES (11, 'new') RETURNING id"
        ).fetchone()["id"]
    assert new_id > 22


def test_refuses_a_target_that_already_has_a_profile(sqlite_source, empty_db):
    with connect(empty_db) as conn:
        copy_database(sqlite_source, conn)
    with connect(empty_db) as conn:
        with pytest.raises(TargetNotEmpty):
            copy_database(sqlite_source, conn)
        assert conn.execute("SELECT count(*) AS n FROM person_profile").fetchone()["n"] == 1


def test_timestamps_are_read_as_utc(sqlite_source, empty_db):
    with connect(empty_db) as conn:
        copy_database(sqlite_source, conn)
        ts = conn.execute("SELECT created_at FROM person_profile").fetchone()["created_at"]
    assert ts.isoformat().startswith("2026-09-24T20:59:59")
    assert ts.utcoffset().total_seconds() == 0
