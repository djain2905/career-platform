from __future__ import annotations

from app import repository
from app.db import connect
from scripts.seed_resume import seed

EXPECTED = {
    "person_profile": 1, "contact_method": 4, "education_record": 2,
    "role_experience": 5, "experience_highlight": 16, "project": 3,
    "project_highlight": 8, "skill": 18, "skill_proficiency": 18,
    "certification": 1, "achievement": 5,
}


def test_seed_matches_the_vm_row_counts(empty_db):
    with connect(empty_db) as conn:
        assert seed(conn) == EXPECTED


def test_seed_is_rerunnable(empty_db):
    with connect(empty_db) as conn:
        seed(conn)
        assert seed(conn) == EXPECTED


def test_seeded_page_renders_and_hides_the_phone(empty_db, tmp_path):
    with connect(empty_db) as conn:
        seed(conn)
    data, source = repository.load_profile(database_url=empty_db, snapshot_path=tmp_path / "s.json")
    assert source == "live"
    assert data["experience"][0]["date_range"] == "Jun 2026 – Present"
    assert "phone" not in [c["type"] for c in data["contacts"]]
