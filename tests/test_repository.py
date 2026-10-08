from __future__ import annotations

import json

import pytest

from app import repository


# --- shape -------------------------------------------------------------

def test_load_profile_returns_live_source(db, tmp_path):
    data, source = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    assert source == "live"
    assert data["profile"]["full_name"] == "Test Person"
    assert data["profile"]["headline"] == "Test Headline"


def test_experience_ordered_and_draft_excluded(db, tmp_path):
    data, _ = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    companies = [r["company_name"] for r in data["experience"]]
    assert companies == ["Current Co", "Past Co"]      # draft row excluded


def test_highlights_grouped_under_their_role(db, tmp_path):
    data, _ = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    assert data["experience"][0]["highlights"] == ["First bullet", "Second bullet"]
    assert data["experience"][1]["highlights"] == ["Past bullet"]


def test_skills_grouped_by_category(db, tmp_path):
    data, _ = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    assert data["skills"]["Technical"] == ["Python", "SQL"]
    assert data["skills"]["Language"] == ["Hindi"]


# --- privacy -----------------------------------------------------------

def test_phone_never_reaches_the_profile_dict(db, tmp_path):
    data, _ = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    types = [c["type"] for c in data["contacts"]]
    assert "phone" not in types
    assert "email" in types and "linkedin" in types


def test_phone_never_reaches_the_snapshot_file(db, tmp_path):
    snap = tmp_path / "s.json"
    repository.load_profile(database_url=db, snapshot_path=snap)
    assert "555" not in snap.read_text()


# --- date formatting ---------------------------------------------------

@pytest.mark.parametrize("start,end,current,expected", [
    ("2026-06-01", None, 1, "Jun 2026 – Present"),
    ("2025-06-01", "2025-08-01", 0, "Jun 2025 – Aug 2025"),
    ("2024-06-01", "2024-06-01", 0, "Jun 2024"),
    (None, None, 0, ""),
])
def test_date_range_formatting(start, end, current, expected):
    assert repository.format_date_range(start, end, current) == expected


def test_education_expected_label(db, tmp_path):
    data, _ = repository.load_profile(database_url=db, snapshot_path=tmp_path / "s.json")
    assert data["education"][0]["date_label"] == "Expected May 2027"


# --- snapshot / fallback ----------------------------------------------

def test_successful_read_writes_a_snapshot(db, tmp_path):
    snap = tmp_path / "s.json"
    repository.load_profile(database_url=db, snapshot_path=snap)
    assert snap.exists()
    assert json.loads(snap.read_text())["profile"]["full_name"] == "Test Person"


UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:1/none"


def test_falls_back_to_snapshot_when_db_unreachable(db, tmp_path):
    snap = tmp_path / "s.json"
    repository.load_profile(database_url=db, snapshot_path=snap)       # populate snapshot
    data, source = repository.load_profile(database_url=UNREACHABLE, snapshot_path=snap)
    assert source == "snapshot"
    assert data["profile"]["full_name"] == "Test Person"


def test_falls_back_to_minimal_when_db_and_snapshot_both_missing(tmp_path):
    data, source = repository.load_profile(
        database_url=UNREACHABLE, snapshot_path=tmp_path / "gone.json"
    )
    assert source == "minimal"
    assert data["profile"]["full_name"]          # renders something, not a crash
    assert data["experience"] == []


def test_corrupt_snapshot_degrades_to_minimal(tmp_path):
    snap = tmp_path / "s.json"
    snap.write_text("{ this is not json")
    data, source = repository.load_profile(database_url=UNREACHABLE, snapshot_path=snap)
    assert source == "minimal"


def test_snapshot_write_failure_does_not_break_live_read(db, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a directory should be")
    data, source = repository.load_profile(database_url=db, snapshot_path=blocker / "s.json")
    assert source == "live"
    assert data["profile"]["full_name"] == "Test Person"


# --- Review Focus ------------------------------------------------------

def test_snapshot_parent_directory_is_created(db, tmp_path):
    # On Railway, data/ does not exist in the image (its contents are gitignored).
    snap = tmp_path / "data" / "s.json"
    repository.load_profile(database_url=db, snapshot_path=snap)
    assert snap.exists()


def test_snapshot_round_trips_dates_as_iso_strings(db, tmp_path):
    snap = tmp_path / "s.json"
    live, _ = repository.load_profile(database_url=db, snapshot_path=snap)
    saved = json.loads(snap.read_text())
    assert saved["experience"][0]["start_date"] == "2026-06-01"
    assert saved["experience"][0]["date_range"] == "Jun 2026 – Present"
    assert saved == live


@pytest.mark.parametrize("url", ["", "sqlite:///./data/resume.db", UNREACHABLE])
def test_bad_database_url_degrades_and_logs(url, tmp_path, caplog):
    data, source = repository.load_profile(database_url=url, snapshot_path=tmp_path / "none.json")
    assert source == "minimal"
    assert "live read failed" in caplog.text


def test_empty_database_degrades_instead_of_crashing(empty_db, tmp_path):
    data, source = repository.load_profile(database_url=empty_db, snapshot_path=tmp_path / "s.json")
    assert source == "minimal"


def test_date_objects_format_like_strings():
    from datetime import date
    assert repository.format_month(date(2027, 5, 1)) == "May 2027"
    assert repository.format_date_range(date(2025, 6, 1), date(2025, 8, 1), False) == "Jun 2025 – Aug 2025"
