from __future__ import annotations

import psycopg
import pytest

from app.db import DatabaseNotConfigured, connect, init_schema

EXPECTED_TABLES = {
    "achievement", "certification", "contact_method", "content_section",
    "education_record", "entity_tag", "experience_highlight", "person_profile",
    "project", "project_highlight", "role_experience", "skill",
    "skill_proficiency", "tag",
}


def _tables(url: str) -> set[str]:
    with connect(url) as conn:
        return {r["table_name"] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )}


def test_init_schema_creates_every_table(empty_db):
    assert _tables(empty_db) == EXPECTED_TABLES


def test_init_schema_is_idempotent(db):
    with connect(db) as conn:
        init_schema(conn)
        assert conn.execute("SELECT count(*) AS n FROM person_profile").fetchone()["n"] == 1


def test_rows_come_back_as_dicts(db):
    with connect(db) as conn:
        assert conn.execute("SELECT full_name FROM person_profile").fetchone() == {"full_name": "Test Person"}


def test_read_only_connection_rejects_writes(db):
    with connect(db, read_only=True) as conn:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("DELETE FROM achievement")


@pytest.mark.parametrize("url", ["", "sqlite:///./data/resume.db"])
def test_non_postgres_url_is_rejected_clearly(url):
    with pytest.raises(DatabaseNotConfigured):
        connect(url)


def test_current_role_cannot_have_an_end_date(db):
    with connect(db) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO role_experience (profile_id, company_name, role_title, end_date, is_current) "
            "VALUES (1, 'X', 'Y', '2026-01-01', TRUE)"
        )
