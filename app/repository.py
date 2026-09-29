"""Read the public profile out of SQLite, with a snapshot fallback.

`load_profile()` returns one nested dict describing everything the public page
renders. That same dict is what gets written to the snapshot file, so the
degraded-read path (spec 9.4) returns an identical structure and the template
never has to know which source it got.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.db import database_path

SNAPSHOT_PATH = BASE_DIR / "data" / "snapshot.json"

# Contact types that must never be rendered publicly or written to the
# snapshot. Filtered at this chokepoint so no caller can leak them by accident.
PRIVATE_CONTACT_TYPES = {"phone"}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Served when the database is unavailable and no snapshot exists yet, so a
# first-boot failure still renders a page instead of a 500.
MINIMAL: dict[str, Any] = {
    "profile": {
        "full_name": "Dhwani Jain",
        "headline": "Information Systems & Business Analytics student at Loyola Marymount University",
        "summary": None,
        "location": "Los Angeles, CA",
    },
    "contacts": [
        {"type": "email", "label": "Email", "value": "dhwanijain2905@gmail.com",
         "url": "mailto:dhwanijain2905@gmail.com"},
        {"type": "linkedin", "label": "LinkedIn", "value": "linkedin.com/in/dhwani-jain2",
         "url": "https://www.linkedin.com/in/dhwani-jain2"},
        {"type": "github", "label": "GitHub", "value": "github.com/djain2905",
         "url": "https://github.com/djain2905"},
    ],
    "experience": [],
    "projects": [],
    "skills": {},
    "education": [],
    "achievements": [],
    "generated_at": None,
}


def format_month(value: str | None) -> str:
    """'2026-06-01' -> 'Jun 2026'. Dates are month-precision from the resume."""
    if not value:
        return ""
    try:
        dt = datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return ""
    return f"{MONTHS[dt.month - 1]} {dt.year}"


def format_date_range(start: str | None, end: str | None, is_current: int) -> str:
    left = format_month(start)
    if is_current:
        return f"{left} – Present" if left else "Present"
    right = format_month(end)
    if left and right:
        return left if left == right else f"{left} – {right}"
    return left or right


def _group_highlights(conn: sqlite3.Connection, table: str, fk: str) -> dict[int, list[str]]:
    """One query for all bullets, grouped in Python — avoids N+1 per row."""
    grouped: dict[int, list[str]] = {}
    for row in conn.execute(f"SELECT {fk}, body FROM {table} ORDER BY {fk}, order_index"):
        grouped.setdefault(row[fk], []).append(row["body"])
    return grouped


def _read_live(db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        profile_row = conn.execute(
            "SELECT id, full_name, headline, summary, location FROM person_profile "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if profile_row is None:
            raise sqlite3.DatabaseError("no person_profile row")
        pid = profile_row["id"]

        contacts = [
            {"type": r["type"], "label": r["label"], "value": r["value"], "url": r["url"]}
            for r in conn.execute(
                "SELECT type, label, value, url FROM contact_method "
                "WHERE profile_id = ? ORDER BY order_index", (pid,))
            if r["type"] not in PRIVATE_CONTACT_TYPES
        ]

        exp_bullets = _group_highlights(conn, "experience_highlight", "experience_id")
        experience = []
        for r in conn.execute(
            "SELECT id, company_name, role_title, employment_type, location, start_date, "
            "end_date, is_current FROM role_experience "
            "WHERE profile_id = ? AND status = 'published' ORDER BY order_index", (pid,)
        ):
            experience.append({
                "company_name": r["company_name"],
                "role_title": r["role_title"],
                "employment_type": r["employment_type"],
                "location": r["location"],
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "is_current": bool(r["is_current"]),
                "date_range": format_date_range(r["start_date"], r["end_date"], r["is_current"]),
                "highlights": exp_bullets.get(r["id"], []),
            })

        proj_bullets = _group_highlights(conn, "project_highlight", "project_id")
        projects = []
        for r in conn.execute(
            "SELECT id, title, slug, short_description, repo_url, external_url, featured "
            "FROM project WHERE profile_id = ? AND status = 'published' ORDER BY order_index", (pid,)
        ):
            projects.append({
                "title": r["title"],
                "slug": r["slug"],
                "short_description": r["short_description"],
                "repo_url": r["repo_url"],
                "external_url": r["external_url"],
                "featured": bool(r["featured"]),
                "highlights": proj_bullets.get(r["id"], []),
            })

        skills: dict[str, list[str]] = {}
        for r in conn.execute(
            "SELECT s.name, s.category FROM skill s "
            "JOIN skill_proficiency sp ON sp.skill_id = s.id "
            "WHERE sp.profile_id = ? ORDER BY s.sort_order", (pid,)
        ):
            skills.setdefault(r["category"] or "Other", []).append(r["name"])

        education = []
        for r in conn.execute(
            "SELECT institution, degree, field_of_study, location, end_date, is_expected, "
            "description FROM education_record "
            "WHERE profile_id = ? AND status = 'published' ORDER BY order_index", (pid,)
        ):
            label = format_month(r["end_date"])
            education.append({
                "institution": r["institution"],
                "degree": r["degree"],
                "field_of_study": r["field_of_study"],
                "location": r["location"],
                "date_label": f"Expected {label}" if r["is_expected"] and label else label,
                "description": r["description"],
            })

        achievements = [
            {"title": r["title"], "description": r["description"], "source": r["source"]}
            for r in conn.execute(
                "SELECT title, description, source FROM achievement "
                "WHERE profile_id = ? AND status = 'published' ORDER BY order_index", (pid,))
        ]

        return {
            "profile": {
                "full_name": profile_row["full_name"],
                "headline": profile_row["headline"],
                "summary": profile_row["summary"],
                "location": profile_row["location"],
            },
            "contacts": contacts,
            "experience": experience,
            "projects": projects,
            "skills": skills,
            "education": education,
            "achievements": achievements,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    finally:
        conn.close()


def _write_snapshot(data: dict[str, Any], path: Path) -> None:
    """Atomic write — a crash mid-write must not leave truncated JSON behind."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_profile(
    db_path: Path | None = None,
    snapshot_path: Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Return (profile_dict, source) where source is 'live', 'snapshot' or 'minimal'."""
    db_path = db_path or database_path()
    snapshot_path = snapshot_path or SNAPSHOT_PATH

    try:
        data = _read_live(db_path)
    except (sqlite3.Error, OSError):
        try:
            return json.loads(snapshot_path.read_text()), "snapshot"
        except (OSError, ValueError):
            return MINIMAL, "minimal"

    try:
        _write_snapshot(data, snapshot_path)
    except OSError:
        pass          # a failed snapshot must never break a working live read
    return data, "live"
