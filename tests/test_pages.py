"""Status codes and project messages for the home page (Project 1, requirement 1).

Healthy read: 200 with projects. Empty project table: 200 with a message.
Database down: profile still visible, "Projects temporarily unavailable",
503, and no saved project content. Database back: 200 again on the next
request, with no restart.
"""
from __future__ import annotations

import psycopg
import pytest
from starlette.requests import Request

from app import db as app_db
from app import main, repository

UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:1/none"
UNAVAILABLE = "Projects temporarily unavailable"
EMPTY = "No projects published yet"


def get_home():
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    response = main.home(Request(scope))
    return response.status_code, response.body.decode()


@pytest.fixture
def use_db(monkeypatch, tmp_path):
    """Point the app at a given DATABASE_URL, with a private snapshot file."""
    monkeypatch.setattr(repository, "SNAPSHOT_PATH", tmp_path / "snapshot.json")

    def _use(url: str) -> None:
        monkeypatch.setattr(app_db, "DATABASE_URL", url)

    return _use


def test_healthy_read_returns_200_with_projects(db, use_db):
    use_db(db)
    status, html = get_home()
    assert status == 200
    assert "Test Project" in html
    assert UNAVAILABLE not in html


def test_empty_project_table_returns_200_with_a_message(db, use_db):
    with psycopg.connect(db) as conn:
        conn.execute("DELETE FROM project")
    use_db(db)
    status, html = get_home()
    assert status == 200
    assert EMPTY in html
    assert UNAVAILABLE not in html


def test_database_down_returns_503_keeps_profile_and_hides_projects(db, use_db):
    use_db(db)
    get_home()                      # a healthy read saves the snapshot
    use_db(UNREACHABLE)
    status, html = get_home()
    assert status == 503
    assert UNAVAILABLE in html
    assert "Test Person" in html    # profile stays visible
    assert "Test Project" not in html  # no saved project content


def test_database_down_with_no_snapshot_still_shows_a_profile(use_db):
    use_db(UNREACHABLE)
    status, html = get_home()
    assert status == 503
    assert UNAVAILABLE in html
    assert repository.MINIMAL["profile"]["full_name"] in html


def test_recovery_needs_no_restart(db, use_db):
    use_db(UNREACHABLE)
    assert get_home()[0] == 503
    use_db(db)                      # same app object, database is back
    status, html = get_home()
    assert status == 200
    assert "Test Project" in html
