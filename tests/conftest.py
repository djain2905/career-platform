from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA = BASE_DIR / "app" / "schema.sql"


@pytest.fixture
def db(tmp_path) -> Path:
    """A schema-complete database seeded with a small, known profile."""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA.read_text())

    conn.execute(
        "INSERT INTO person_profile (id, full_name, headline, summary, location) "
        "VALUES (1, 'Test Person', 'Test Headline', NULL, 'Los Angeles, CA')"
    )
    contacts = [
        ("email", "Email", "t@example.com", "mailto:t@example.com", 1, 0),
        ("phone", "Phone", "+1 (555) 555-5555", "tel:+15555555555", 0, 1),
        ("linkedin", "LinkedIn", "linkedin.com/in/test", "https://linkedin.com/in/test", 0, 2),
    ]
    conn.executemany(
        "INSERT INTO contact_method (profile_id, type, label, value, url, is_primary, order_index) "
        "VALUES (1, ?, ?, ?, ?, ?, ?)",
        contacts,
    )
    conn.execute(
        "INSERT INTO role_experience (id, profile_id, company_name, role_title, location, "
        "start_date, end_date, is_current, order_index, status) "
        "VALUES (1, 1, 'Current Co', 'Analyst', 'LA, CA', '2026-06-01', NULL, 1, 0, 'published')"
    )
    conn.execute(
        "INSERT INTO role_experience (id, profile_id, company_name, role_title, location, "
        "start_date, end_date, is_current, order_index, status) "
        "VALUES (2, 1, 'Past Co', 'Intern', 'SF, CA', '2025-06-01', '2025-08-01', 0, 1, 'published')"
    )
    conn.execute(
        "INSERT INTO role_experience (id, profile_id, company_name, role_title, "
        "start_date, order_index, status) "
        "VALUES (3, 1, 'Draft Co', 'Hidden', '2024-01-01', 2, 'draft')"
    )
    conn.executemany(
        "INSERT INTO experience_highlight (experience_id, body, order_index) VALUES (?, ?, ?)",
        [(1, "First bullet", 0), (1, "Second bullet", 1), (2, "Past bullet", 0)],
    )
    conn.execute(
        "INSERT INTO project (id, profile_id, title, slug, short_description, repo_url, "
        "featured, order_index, status) VALUES (1, 1, 'Test Project', 'test-project', "
        "'A description', 'https://github.com/x/y', 1, 0, 'published')"
    )
    conn.executemany(
        "INSERT INTO project_highlight (project_id, body, order_index) VALUES (?, ?, ?)",
        [(1, "Project bullet", 0)],
    )
    for i, (name, cat) in enumerate([("Python", "Technical"), ("SQL", "Technical"), ("Hindi", "Language")]):
        conn.execute("INSERT INTO skill (id, name, category, sort_order) VALUES (?, ?, ?, ?)",
                     (i + 1, name, cat, i))
        conn.execute("INSERT INTO skill_proficiency (profile_id, skill_id) VALUES (1, ?)", (i + 1,))
    conn.execute(
        "INSERT INTO education_record (profile_id, institution, degree, field_of_study, "
        "end_date, is_expected, description, order_index, status) "
        "VALUES (1, 'Test University', 'BS', 'Data', '2027-05-01', 1, 'Coursework: X', 0, 'published')"
    )
    conn.execute(
        "INSERT INTO achievement (profile_id, title, description, order_index, status) "
        "VALUES (1, 'First Place', 'Won a thing', 0, 'published')"
    )
    conn.commit()
    conn.close()
    return path
