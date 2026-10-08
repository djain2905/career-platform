from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import psycopg
import pytest

from app.db import init_schema

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_SCHEMA = BASE_DIR / "tests" / "fixtures" / "sqlite_schema.sql"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:54329/career_test"
)


@pytest.fixture
def pg_url() -> str:
    """A local Postgres database with every table dropped."""
    if urlparse(TEST_DATABASE_URL).hostname not in {"localhost", "127.0.0.1"}:
        pytest.fail(f"Refusing to wipe a non-local database: {urlparse(TEST_DATABASE_URL).hostname}")
    try:
        conn = psycopg.connect(TEST_DATABASE_URL, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.fail(
            "Test Postgres is not reachable. Start it with:\n"
            "  docker start career-pg-test\n"
            f"({exc})"
        )
    with conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    return TEST_DATABASE_URL


@pytest.fixture
def empty_db(pg_url) -> str:
    with psycopg.connect(pg_url) as conn:
        init_schema(conn)
    return pg_url


@pytest.fixture
def db(empty_db) -> str:
    """A schema-complete database seeded with a small, known profile."""
    with psycopg.connect(empty_db) as conn:
        conn.execute(
            "INSERT INTO person_profile (id, full_name, headline, summary, location) "
            "VALUES (1, 'Test Person', 'Test Headline', NULL, 'Los Angeles, CA')"
        )
        conn.cursor().executemany(
            "INSERT INTO contact_method (profile_id, type, label, value, url, is_primary, order_index) "
            "VALUES (1, %s, %s, %s, %s, %s, %s)",
            [
                ("email", "Email", "t@example.com", "mailto:t@example.com", True, 0),
                ("phone", "Phone", "+1 (555) 555-5555", "tel:+15555555555", False, 1),
                ("linkedin", "LinkedIn", "linkedin.com/in/test", "https://linkedin.com/in/test", False, 2),
            ],
        )
        conn.execute(
            "INSERT INTO role_experience (id, profile_id, company_name, role_title, location, "
            "start_date, end_date, is_current, order_index, status) VALUES "
            "(1, 1, 'Current Co', 'Analyst', 'LA, CA', '2026-06-01', NULL, TRUE, 0, 'published'),"
            "(2, 1, 'Past Co', 'Intern', 'SF, CA', '2025-06-01', '2025-08-01', FALSE, 1, 'published'),"
            "(3, 1, 'Draft Co', 'Hidden', NULL, '2024-01-01', NULL, FALSE, 2, 'draft')"
        )
        conn.cursor().executemany(
            "INSERT INTO experience_highlight (experience_id, body, order_index) VALUES (%s, %s, %s)",
            [(1, "First bullet", 0), (1, "Second bullet", 1), (2, "Past bullet", 0)],
        )
        conn.execute(
            "INSERT INTO project (id, profile_id, title, slug, short_description, repo_url, "
            "featured, order_index, status) VALUES (1, 1, 'Test Project', 'test-project', "
            "'A description', 'https://github.com/x/y', TRUE, 0, 'published')"
        )
        conn.execute(
            "INSERT INTO project_highlight (project_id, body, order_index) VALUES (1, 'Project bullet', 0)"
        )
        for i, (name, cat) in enumerate([("Python", "Technical"), ("SQL", "Technical"), ("Hindi", "Language")]):
            conn.execute(
                "INSERT INTO skill (id, name, category, sort_order) VALUES (%s, %s, %s, %s)",
                (i + 1, name, cat, i),
            )
            conn.execute("INSERT INTO skill_proficiency (profile_id, skill_id) VALUES (1, %s)", (i + 1,))
        conn.execute(
            "INSERT INTO education_record (profile_id, institution, degree, field_of_study, "
            "end_date, is_expected, description, order_index, status) VALUES "
            "(1, 'Test University', 'BS', 'Data', '2027-05-01', TRUE, 'Coursework: X', 0, 'published')"
        )
        conn.execute(
            "INSERT INTO achievement (profile_id, title, description, order_index, status) "
            "VALUES (1, 'First Place', 'Won a thing', 0, 'published')"
        )
    return empty_db


@pytest.fixture
def sqlite_source(tmp_path) -> Path:
    """A SQLite file in the VM's old schema, holding a small known profile."""
    path = tmp_path / "source.db"
    conn = sqlite3.connect(path)
    conn.executescript(SQLITE_SCHEMA.read_text())
    conn.executescript("""
        INSERT INTO person_profile (id, full_name, headline, location, created_at, updated_at)
            VALUES (7, 'Source Person', 'Source Headline', 'Dubai', '2026-09-24 20:59:59', '2026-09-24 20:59:59');
        INSERT INTO contact_method (id, profile_id, type, label, value, url, is_primary, order_index)
            VALUES (3, 7, 'email', 'Email', 's@example.com', 'mailto:s@example.com', 1, 0),
                   (4, 7, 'phone', 'Phone', '+1 (555) 000-0000', 'tel:+15550000000', 0, 1);
        INSERT INTO role_experience (id, profile_id, company_name, role_title, start_date, end_date, is_current, order_index)
            VALUES (11, 7, 'Now Co', 'Analyst', '2026-06-01', NULL, 1, 0),
                   (12, 7, 'Then Co', 'Intern', '2025-06-01', '2025-08-01', 0, 1);
        INSERT INTO experience_highlight (id, experience_id, body, order_index)
            VALUES (21, 11, 'Now bullet', 0), (22, 12, 'Then bullet', 0);
        INSERT INTO skill (id, name, category, sort_order) VALUES (31, 'Python', 'Technical', 0);
        INSERT INTO skill_proficiency (id, profile_id, skill_id) VALUES (41, 7, 31);
    """)
    conn.commit()
    conn.close()
    return path
