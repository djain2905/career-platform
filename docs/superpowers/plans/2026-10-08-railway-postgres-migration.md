# Railway + PostgreSQL Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve `https://dhwanijain.me` from the existing Railway project, with the resume read from Railway's PostgreSQL instead of a SQLite file on the Azure VM, then retire the VM.

**Architecture:** The app keeps its one read path, `load_profile()`, and its snapshot → minimal fallback, but `_read_live` now runs against Postgres through `psycopg` 3. `app/schema.sql` becomes a Postgres schema that uses native types: `IDENTITY` ids, `BOOLEAN` flags, `DATE` dates and `TIMESTAMPTZ` stamps. The live rows are copied from the VM's SQLite file into Railway Postgres by a one-shot script that keeps every id. Railway builds the repo from `pyproject.toml` / `uv.lock`, applies the schema in a pre-deploy step and runs Uvicorn on `$PORT`. Railway then terminates TLS for the custom domain, which takes over the job Nginx and Certbot do on the VM. The VM keeps serving until Railway is verified over HTTPS. Only then does DNS move.

**Tech Stack:** Python 3.13, FastAPI 0.115.0, Uvicorn 0.30.6, Jinja2 3.1.4, psycopg 3 (binary), PostgreSQL (Railway managed; local Docker for tests), Railway CLI, Railpack builder, Cloudflare DNS

**Spec:** `docs/superpowers/specs/2026-09-15-career-platform-app-spec.md` (content model §7, degraded reads §9.4). Prior deployment state: `docs/superpowers/plans/2026-09-24-azure-vm-migration.md`, `docs/superpowers/plans/2026-10-01-operate-the-vm.md`.

## Starting State (inspected 2026-10-08)

| Fact | Value |
|---|---|
| Live commit on VM | `a987583`. Local `main` is 4 commits ahead with docs-only changes |
| Process on VM | `career-platform.service`, `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2`, behind Nginx + Let's Encrypt |
| Live data | `/home/azureuser/career-platform/data/resume.db` (SQLite, 139 KB) |
| Row counts on VM | person_profile 1, contact_method 4, role_experience 5, experience_highlight 16, project 3, project_highlight 8, skill 18, skill_proficiency 18, education_record 2, certification 1, achievement 5, content_section 0, tag 0, entity_tag 0 |
| DB code | `app/db.py` and `app/repository.py` call `sqlite3` directly. `app/repository.py` opens the file with `mode=ro` |
| SQLite-isms to port | `?` placeholders, `cur.lastrowid`, `executescript`, `PRAGMA`, `AUTOINCREMENT`, `datetime('now')`, 0/1 integer flags, `sqlite_master` |
| Laptop tooling | `uv` installed. Docker is installed but the daemon is **not running**. **No** `railway` CLI, **no** `psql` |
| Railway | Project exists with a Postgres service and a web service. Names, Postgres version and deploy source are unknown until Task 0 |

## Global Constraints

- **Existing dependency versions stay frozen:** `fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `jinja2==3.1.4`, `python-dotenv==1.0.1`. The only new runtime dependency is `psycopg[binary]`, pinned to an exact version in both `pyproject.toml` and `requirements.txt`.
- **Python 3.13**, from `.python-version`.
- **Connection strings never go into git, the plan, or the chat transcript.** They contain the database password. Read them into shell variables (`$(railway variables …)`) and never `echo` them. Scripts print host and database name only.
- **Tests only ever wipe a local database.** `tests/conftest.py` refuses any `TEST_DATABASE_URL` whose host is not `localhost`/`127.0.0.1`.
- **The phone number never renders and never reaches the snapshot.** `PRIVATE_CONTACT_TYPES` stays the single filter.
- **The VM stays running, with auto-shutdown off, until Task 8 passes.** After that the owner stops it from the portal and confirms "Stopped (deallocated)". The VM and its disk are kept, not deleted.
- **Railway changes need owner approval before each one.** That covers variables, deploys and domains. Cloudflare and Azure changes are made by the owner, since the agent has no credentials for them. Interactive logins are run by the owner as `! <command>`.
- **The Railway web service uses the private Postgres URL** (`${{<Postgres service>.DATABASE_URL}}`). The public URL (`DATABASE_PUBLIC_URL`) is used only from the laptop, for the data copy and verification.
- **Rollback is DNS only.** Until Task 9, pointing the Cloudflare `@`/`www` records back to A `4.155.216.147` restores the VM site exactly as it was.

## Review Focus

These are the failure modes most likely to hurt a real visitor that no main-path test exercises. Each one has its check folded into the task that owns it.

1. **Snapshot directory missing in the container.** `data/` holds only gitignored files, so it does not exist in the Railway image. Today `_write_snapshot` fails silently when the directory is missing, so the fallback would never be written and the first database hiccup would serve the minimal page. Task 2 makes the write create its parent directory and tests that it does.
2. **`DATE` values breaking the snapshot.** psycopg returns `datetime.date`, which `json.dump` rejects with `TypeError`. That isn't an `OSError`, so it would turn a working live read into a 500. Task 2 serializes dates as ISO strings and tests that the snapshot round-trips.
3. **A stale or wrong `DATABASE_URL`.** A leftover `sqlite:///` value, an empty variable, or an unreachable host must degrade to the snapshot and log the reason. It must never return a 500 or hang the request. Task 2 tests all three; `CONNECT_TIMEOUT` keeps the hang short.
4. **Running the data copy twice.** A second run would collide on primary keys halfway through. The copy refuses a non-empty target before writing anything, and it resets the identity sequences so later inserts don't collide with copied ids. Task 4 tests both.
5. **Railway reports the deploy healthy while the page serves fallback content.** `/health` doesn't touch the database. Task 7 verifies the rendered page has **no** "Showing saved content" banner and does contain a known role. A 200 status alone doesn't count.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `app/config.py` | Modify | `DATABASE_URL` default becomes `""` (no implicit SQLite) |
| `app/db.py` | Rewrite | `connect(url, read_only)` → psycopg connection with `dict_row`; `init_schema(conn)`; `DatabaseNotConfigured` |
| `app/schema.sql` | Rewrite | Postgres DDL, same tables/columns/constraints as the SQLite schema |
| `app/repository.py` | Modify | `_read_live` on Postgres; date handling; snapshot parent creation; fallback logging |
| `scripts/init_db.py` | Modify | Postgres table listing; no URL printed |
| `scripts/seed_resume.py` | Modify | `%s` params, `RETURNING id`, Python bools |
| `scripts/copy_sqlite_to_postgres.py` | Create | One-shot SQLite → Postgres copy, ids preserved, refuses non-empty target |
| `tests/fixtures/sqlite_schema.sql` | Create (moved) | The old SQLite schema, kept only so the copy script has a realistic source in tests |
| `tests/conftest.py` | Rewrite | Local-Postgres fixtures with a safety guard; SQLite source fixture |
| `tests/test_db.py` | Create | Schema creation, idempotence, URL validation |
| `tests/test_repository.py` | Modify | Same assertions on Postgres + Review Focus 1–3 |
| `tests/test_seed.py` | Create | Seed is re-runnable and stores what the page needs |
| `tests/test_copy.py` | Create | Review Focus 4 + fidelity of the copy |
| `railway.json` | Create | Build/deploy config: pre-deploy schema, start command, health check |
| `pyproject.toml`, `requirements.txt`, `uv.lock` | Modify | Add `psycopg[binary]` |
| `.env.example` | Modify | Postgres URL example |
| `README.md` | Modify | How to run locally against Docker Postgres, how to run tests |

---

## Task 0: Preflight — tools, Railway link, test database

**Where this runs:** the laptop. Steps marked **Owner** need an interactive login or a click.

**Interfaces:**
- Produces: the recorded Railway names `<PG_SERVICE>` and `<WEB_SERVICE>`, the Postgres major version `<PG_MAJOR>`, the deploy source (GitHub or CLI), and a local test Postgres at `postgresql://postgres:test@localhost:54329/career_test`. Every later task uses these names.

- [ ] **Step 1: Install the Railway CLI**

```bash
brew install railway && railway --version
```

Expected: a version string.

- [ ] **Step 2: Owner — log in and link the project**

```
! railway login
! railway link
```

In `railway link`, pick the existing project, the `production` environment, and the **web** service.

- [ ] **Step 3: Record what the project contains**

```bash
railway status
railway list --json | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin), indent=1)[:4000])'
```

Write the exact service names into this plan, under **Task 0 findings** at the bottom, as `<PG_SERVICE>` (usually `Postgres`) and `<WEB_SERVICE>`. In the Railway dashboard, open the web service's **Settings → Source** and record whether a GitHub repo is connected and which branch it deploys from.

- [ ] **Step 4: Record the Postgres server version without exposing the URL**

```bash
PGURL=$(railway variables --service <PG_SERVICE> --kv | sed -n 's/^DATABASE_PUBLIC_URL=//p')
test -n "$PGURL" && echo "got public url" || echo "MISSING DATABASE_PUBLIC_URL"
U="$PGURL" uv run --with 'psycopg[binary]' python -c 'import os,psycopg; print(psycopg.connect(os.environ["U"]).execute("show server_version").fetchone()[0])'
```

Record the major version as `<PG_MAJOR>`. If `DATABASE_PUBLIC_URL` is missing, the Postgres service has no TCP proxy. **Owner:** enable it under Postgres → Settings → Networking → TCP Proxy.

- [ ] **Step 5: Start the local test database**

**Owner:** open Docker Desktop. Then:

```bash
docker run -d --name career-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=career_test -p 54329:5432 postgres:<PG_MAJOR>
docker exec career-pg-test pg_isready -U postgres
```

Expected: `accepting connections`. Port 54329 avoids clashing with any Postgres already on 5432.

- [ ] **Step 6: Commit the findings**

```bash
git add docs/superpowers/plans/2026-10-08-railway-postgres-migration.md
git commit -m "docs: record Railway preflight findings"
```

---

## Task 1: Postgres connection and schema

**Files:**
- Modify: `app/config.py`, `pyproject.toml`, `requirements.txt`, `uv.lock`, `.env.example`
- Rewrite: `app/db.py`, `app/schema.sql`, `tests/conftest.py`
- Create: `tests/fixtures/sqlite_schema.sql`, `tests/test_db.py`

**Interfaces:**
- Consumes: local test Postgres from Task 0.
- Produces:
  - `app.db.connect(url: str | None = None, *, read_only: bool = False) -> psycopg.Connection`. Rows come back as dicts. `url=None` means `app.config.DATABASE_URL`.
  - `app.db.init_schema(conn: psycopg.Connection) -> None`, idempotent.
  - `app.db.DatabaseNotConfigured(RuntimeError)`, raised for an empty or non-Postgres URL.
  - `app.db.CONNECT_TIMEOUT: int = 3`
  - Fixtures: `pg_url` (wiped local DB URL), `empty_db` (schema applied, returns URL), `db` (schema + known profile, returns URL), `sqlite_source` (path to a SQLite file in the old schema with known rows).

- [ ] **Step 1: Add the dependency**

```bash
uv add 'psycopg[binary]'
grep -A6 '^dependencies' pyproject.toml
```

`uv add` writes a `>=` range, so replace it with the exact version it resolved (from `uv.lock`). For example, if it resolved `3.2.10`:

```toml
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "jinja2==3.1.4",
    "python-dotenv==1.0.1",
    "psycopg[binary]==3.2.10",
]
```

Then add the identical line `psycopg[binary]==3.2.10` (same version) to `requirements.txt`, and run `uv lock`.

- [ ] **Step 2: Keep the old SQLite schema for the copy tests**

```bash
mkdir -p tests/fixtures
git mv app/schema.sql tests/fixtures/sqlite_schema.sql
```

Add one line to the top of `tests/fixtures/sqlite_schema.sql`:

```sql
-- Frozen copy of the SQLite schema the Azure VM ran (commit a987583). Used only
-- as the source side of tests/test_copy.py. The live schema is app/schema.sql.
```

- [ ] **Step 3: Write the failing tests**

`tests/conftest.py`:

```python
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
```

`tests/test_db.py`:

```python
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
```

- [ ] **Step 4: Run them to verify they fail**

Run: `uv run pytest tests/test_db.py -v`
Expected: collection error, `ImportError: cannot import name 'DatabaseNotConfigured' from 'app.db'`.

- [ ] **Step 5: Write the Postgres schema**

`app/schema.sql`:

```sql
-- Career Platform schema (PostgreSQL)
-- Mirrors the content model in docs/superpowers/specs/2026-09-15-career-platform-app-spec.md section 7.
-- Idempotent: every statement is IF NOT EXISTS, so it runs on every deploy.

-- 7.1 PersonProfile -----------------------------------------------------
CREATE TABLE IF NOT EXISTS person_profile (
    id                  INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    full_name           TEXT NOT NULL,
    headline            TEXT,
    summary             TEXT,
    location            TEXT,
    pronouns            TEXT,
    preferred_role      TEXT,
    availability_status TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.2 ContactMethod -----------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_method (
    id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    label       TEXT,
    value       TEXT NOT NULL,
    url         TEXT,
    is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, type, value)
);

-- 7.3 RoleExperience ----------------------------------------------------
CREATE TABLE IF NOT EXISTS role_experience (
    id              INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id      INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    company_name    TEXT NOT NULL,
    role_title      TEXT NOT NULL,
    employment_type TEXT,
    location        TEXT,
    start_date      DATE,
    end_date        DATE,
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    summary         TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'published', 'archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, company_name, role_title, start_date),
    CHECK (NOT is_current OR end_date IS NULL)
);

-- Resume bullets for a role. Split into rows so the admin UI can reorder
-- and edit them individually (spec 6.2) instead of editing one blob.
CREATE TABLE IF NOT EXISTS experience_highlight (
    id            INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    experience_id INTEGER NOT NULL REFERENCES role_experience(id) ON DELETE CASCADE,
    body          TEXT NOT NULL,
    order_index   INTEGER NOT NULL DEFAULT 0
);

-- 7.4 Project -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS project (
    id                INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id        INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    title             TEXT NOT NULL,
    slug              TEXT NOT NULL UNIQUE,
    short_description TEXT,
    long_description  TEXT,
    status            TEXT NOT NULL DEFAULT 'published'
                      CHECK (status IN ('draft', 'published', 'archived')),
    start_date        DATE,
    end_date          DATE,
    external_url      TEXT,
    repo_url          TEXT,
    featured          BOOLEAN NOT NULL DEFAULT FALSE,
    image_url         TEXT,
    order_index       INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_highlight (
    id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0
);

-- 7.5 Skill -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill (
    id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.6 SkillProficiency --------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_proficiency (
    id                INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id        INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    skill_id          INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    proficiency_level TEXT,
    years_experience  REAL,
    notes             TEXT,
    UNIQUE (profile_id, skill_id)
);

-- 7.7 EducationRecord ---------------------------------------------------
CREATE TABLE IF NOT EXISTS education_record (
    id              INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id      INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    institution     TEXT NOT NULL,
    degree          TEXT,
    field_of_study  TEXT,
    location        TEXT,
    start_date      DATE,
    end_date        DATE,
    is_expected     BOOLEAN NOT NULL DEFAULT FALSE,
    description     TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'published', 'archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.8 Certification -----------------------------------------------------
CREATE TABLE IF NOT EXISTS certification (
    id             INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id     INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    issuer         TEXT,
    date_earned    DATE,
    credential_url TEXT,
    status         TEXT NOT NULL DEFAULT 'published'
                   CHECK (status IN ('draft', 'published', 'archived')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.9 Achievement -------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievement (
    id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    date_earned DATE,
    source      TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'published'
                CHECK (status IN ('draft', 'published', 'archived')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.10 ContentSection ---------------------------------------------------
CREATE TABLE IF NOT EXISTS content_section (
    id           INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    profile_id   INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL,
    title        TEXT,
    body         TEXT,
    order_index  INTEGER NOT NULL DEFAULT 0,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7.11 Tag / EntityTag --------------------------------------------------
CREATE TABLE IF NOT EXISTS tag (
    id         INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    slug       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entity_tag (
    id          INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tag_id      INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    UNIQUE (tag_id, entity_type, entity_id)
);

-- Indexes for the common public-page reads ------------------------------
CREATE INDEX IF NOT EXISTS idx_experience_profile  ON role_experience (profile_id, status, order_index);
CREATE INDEX IF NOT EXISTS idx_project_profile     ON project (profile_id, status, order_index);
CREATE INDEX IF NOT EXISTS idx_education_profile   ON education_record (profile_id, status, order_index);
CREATE INDEX IF NOT EXISTS idx_contact_profile     ON contact_method (profile_id, order_index);
CREATE INDEX IF NOT EXISTS idx_exp_highlight       ON experience_highlight (experience_id, order_index);
CREATE INDEX IF NOT EXISTS idx_proj_highlight      ON project_highlight (project_id, order_index);
CREATE INDEX IF NOT EXISTS idx_entity_tag_lookup   ON entity_tag (entity_type, entity_id);
```

- [ ] **Step 6: Write `app/db.py` and the config default**

`app/config.py`: change the last line to

```python
DATABASE_URL = os.getenv("DATABASE_URL", "")
```

`app/db.py`:

```python
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from app.config import BASE_DIR, DATABASE_URL

SCHEMA_PATH = BASE_DIR / "app" / "schema.sql"

# Seconds to wait for Postgres before a page read gives up and falls back to
# the snapshot. libpq's minimum is 2.
CONNECT_TIMEOUT = 3


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL is empty or is not a PostgreSQL URL."""


def connect(url: str | None = None, *, read_only: bool = False) -> psycopg.Connection:
    url = DATABASE_URL if url is None else url
    if not url.startswith(("postgresql://", "postgres://")):
        raise DatabaseNotConfigured("DATABASE_URL must be a postgresql:// URL")
    conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=CONNECT_TIMEOUT)
    conn.read_only = read_only
    return conn


def init_schema(conn: psycopg.Connection) -> None:
    # No parameters, so psycopg sends the whole file as one multi-statement query.
    conn.execute(SCHEMA_PATH.read_text())
    conn.commit()
```

The exception message deliberately leaves out the URL, because a URL can carry a password.

`.env.example`:

```
# Copy to .env and adjust per environment.
APP_NAME=Career Platform
APP_ENV=development
# Local Docker Postgres (see README). On Railway this is set to the
# Postgres service's private DATABASE_URL by reference, never by value.
DATABASE_URL=postgresql://postgres:test@localhost:54329/career_dev
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_db.py -v`
Expected: 7 passed. (`tests/test_repository.py` still fails at this point. Task 2 fixes it.)

- [ ] **Step 8: Commit**

```bash
git add app/config.py app/db.py app/schema.sql tests/conftest.py tests/test_db.py tests/fixtures/sqlite_schema.sql pyproject.toml requirements.txt uv.lock .env.example
git commit -m "feat: move the schema and connection layer to PostgreSQL"
```

---

## Task 2: Read the profile from Postgres

**Files:**
- Modify: `app/repository.py`, `tests/test_repository.py`

**Interfaces:**
- Consumes: `connect`, `DatabaseNotConfigured` and the `db` fixture from Task 1.
- Produces: `load_profile(database_url: str | None = None, snapshot_path: Path | None = None) -> tuple[dict, str]`. The first parameter **replaces** `db_path`, and `app/main.py` calls it with no arguments, so `main.py` is unchanged. `format_month` and `format_date_range` accept `date | str | None`.

- [ ] **Step 1: Port the existing tests and add the Review Focus tests**

In `tests/test_repository.py`, replace every `db_path=db` with `database_url=db`. Then replace the three fallback tests that use `tmp_path / "gone.db"` and the final unwritable-snapshot test with the versions below, and append the new tests:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_repository.py -v`
Expected: FAIL. Calls error with `TypeError: load_profile() got an unexpected keyword argument 'database_url'`.

- [ ] **Step 3: Port `app/repository.py`**

Change the module docstring's first line to `"""Read the public profile out of PostgreSQL, with a snapshot fallback.`. Replace the imports through `SNAPSHOT_PATH` with:

```python
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from app.config import BASE_DIR
from app.db import DatabaseNotConfigured, connect

log = logging.getLogger(__name__)

SNAPSHOT_PATH = BASE_DIR / "data" / "snapshot.json"


class NoProfile(LookupError):
    """The database is reachable but holds no person_profile row."""
```

Keep `PRIVATE_CONTACT_TYPES`, `MONTHS` and `MINIMAL` unchanged. Replace the functions from `format_month` through the end of `_read_live`:

```python
def format_month(value: date | str | None) -> str:
    """date(2026, 6, 1) or '2026-06-01' -> 'Jun 2026'. Dates are month-precision."""
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return ""
    return f"{MONTHS[value.month - 1]} {value.year}"


def format_date_range(start: date | str | None, end: date | str | None, is_current: bool) -> str:
    left = format_month(start)
    if is_current:
        return f"{left} – Present" if left else "Present"
    right = format_month(end)
    if left and right:
        return left if left == right else f"{left} – {right}"
    return left or right


def _iso(value: date | None) -> str | None:
    """Dates leave this module as strings so the dict stays JSON-serializable."""
    return value.isoformat() if value else None


def _group_highlights(conn: psycopg.Connection, table: str, fk: str) -> dict[int, list[str]]:
    """One query for all bullets, grouped in Python — avoids N+1 per row."""
    grouped: dict[int, list[str]] = {}
    for row in conn.execute(f"SELECT {fk}, body FROM {table} ORDER BY {fk}, order_index"):
        grouped.setdefault(row[fk], []).append(row["body"])
    return grouped


def _read_live(database_url: str | None) -> dict[str, Any]:
    with connect(database_url, read_only=True) as conn:
        profile_row = conn.execute(
            "SELECT id, full_name, headline, summary, location FROM person_profile "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if profile_row is None:
            raise NoProfile("no person_profile row")
        pid = profile_row["id"]

        contacts = [
            {"type": r["type"], "label": r["label"], "value": r["value"], "url": r["url"]}
            for r in conn.execute(
                "SELECT type, label, value, url FROM contact_method "
                "WHERE profile_id = %s ORDER BY order_index", (pid,))
            if r["type"] not in PRIVATE_CONTACT_TYPES
        ]

        exp_bullets = _group_highlights(conn, "experience_highlight", "experience_id")
        experience = []
        for r in conn.execute(
            "SELECT id, company_name, role_title, employment_type, location, start_date, "
            "end_date, is_current FROM role_experience "
            "WHERE profile_id = %s AND status = 'published' ORDER BY order_index", (pid,)
        ):
            experience.append({
                "company_name": r["company_name"],
                "role_title": r["role_title"],
                "employment_type": r["employment_type"],
                "location": r["location"],
                "start_date": _iso(r["start_date"]),
                "end_date": _iso(r["end_date"]),
                "is_current": r["is_current"],
                "date_range": format_date_range(r["start_date"], r["end_date"], r["is_current"]),
                "highlights": exp_bullets.get(r["id"], []),
            })

        proj_bullets = _group_highlights(conn, "project_highlight", "project_id")
        projects = []
        for r in conn.execute(
            "SELECT id, title, slug, short_description, repo_url, external_url, featured "
            "FROM project WHERE profile_id = %s AND status = 'published' ORDER BY order_index", (pid,)
        ):
            projects.append({
                "title": r["title"],
                "slug": r["slug"],
                "short_description": r["short_description"],
                "repo_url": r["repo_url"],
                "external_url": r["external_url"],
                "featured": r["featured"],
                "highlights": proj_bullets.get(r["id"], []),
            })

        skills: dict[str, list[str]] = {}
        for r in conn.execute(
            "SELECT s.name, s.category FROM skill s "
            "JOIN skill_proficiency sp ON sp.skill_id = s.id "
            "WHERE sp.profile_id = %s ORDER BY s.sort_order", (pid,)
        ):
            skills.setdefault(r["category"] or "Other", []).append(r["name"])

        education = []
        for r in conn.execute(
            "SELECT institution, degree, field_of_study, location, end_date, is_expected, "
            "description FROM education_record "
            "WHERE profile_id = %s AND status = 'published' ORDER BY order_index", (pid,)
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
                "WHERE profile_id = %s AND status = 'published' ORDER BY order_index", (pid,))
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
```

In `_write_snapshot`, add this as the first line of the function body (after the docstring):

```python
    path.parent.mkdir(parents=True, exist_ok=True)
```

Replace `load_profile`:

```python
def load_profile(
    database_url: str | None = None,
    snapshot_path: Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Return (profile_dict, source) where source is 'live', 'snapshot' or 'minimal'."""
    snapshot_path = snapshot_path or SNAPSHOT_PATH

    try:
        data = _read_live(database_url)
    except (psycopg.Error, DatabaseNotConfigured, NoProfile, OSError) as exc:
        log.warning("live read failed, serving fallback: %s", exc)
        try:
            return json.loads(snapshot_path.read_text()), "snapshot"
        except (OSError, ValueError):
            return MINIMAL, "minimal"

    try:
        _write_snapshot(data, snapshot_path)
    except OSError:
        pass          # a failed snapshot must never break a working live read
    return data, "live"
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest -v`
Expected: everything in `tests/test_db.py` and `tests/test_repository.py` passes.

- [ ] **Step 5: Commit**

```bash
git add app/repository.py tests/test_repository.py
git commit -m "feat: read the public profile from PostgreSQL"
```

---

## Task 3: Port the schema and seed scripts

**Files:**
- Modify: `scripts/init_db.py`, `scripts/seed_resume.py`
- Create: `tests/test_seed.py`

**Interfaces:**
- Consumes: `connect`, `init_schema`, the `empty_db` fixture, and `load_profile(database_url=…)`.
- Produces: `scripts.seed_resume.seed(conn: psycopg.Connection) -> dict[str, int]`, unchanged in shape.

- [ ] **Step 1: Write the failing test**

`tests/test_seed.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_seed.py -v`
Expected: FAIL with `psycopg.errors.SyntaxError` at or near `?`.

- [ ] **Step 3: Port `scripts/seed_resume.py`**

Leave the data constants unchanged. Replace `seed()` and `main()`, and change the import line to `from app.db import connect, init_schema`:

```python
def seed(conn) -> dict[str, int]:
    cur = conn.cursor()

    # Idempotent reload: drop this person and let cascades clear dependents.
    cur.execute("DELETE FROM person_profile WHERE full_name = %s", (PROFILE["full_name"],))
    cur.execute("DELETE FROM skill")

    pid = cur.execute(
        """INSERT INTO person_profile
           (full_name, headline, summary, location, pronouns,
            preferred_role, availability_status)
           VALUES (%(full_name)s, %(headline)s, %(summary)s, %(location)s, %(pronouns)s,
                   %(preferred_role)s, %(availability_status)s)
           RETURNING id""",
        PROFILE,
    ).fetchone()["id"]

    for i, (ctype, label, value, url, primary) in enumerate(CONTACTS):
        cur.execute(
            """INSERT INTO contact_method
               (profile_id, type, label, value, url, is_primary, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (pid, ctype, label, value, url, bool(primary), i),
        )

    for i, ed in enumerate(EDUCATION):
        cur.execute(
            """INSERT INTO education_record
               (profile_id, institution, degree, field_of_study, location,
                start_date, end_date, is_expected, description, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (pid, ed["institution"], ed["degree"], ed["field_of_study"],
             ed["location"], ed["start_date"], ed["end_date"],
             bool(ed["is_expected"]), ed["description"], i),
        )

    for i, job in enumerate(EXPERIENCE):
        eid = cur.execute(
            """INSERT INTO role_experience
               (profile_id, company_name, role_title, employment_type, location,
                start_date, end_date, is_current, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (pid, job["company_name"], job["role_title"], job["employment_type"],
             job["location"], job["start_date"], job["end_date"],
             bool(job["is_current"]), i),
        ).fetchone()["id"]
        for j, body in enumerate(job["highlights"]):
            cur.execute(
                "INSERT INTO experience_highlight (experience_id, body, order_index) VALUES (%s, %s, %s)",
                (eid, body, j),
            )

    for i, proj in enumerate(PROJECTS):
        prid = cur.execute(
            """INSERT INTO project
               (profile_id, title, slug, short_description, start_date, end_date,
                external_url, repo_url, featured, order_index)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (pid, proj["title"], proj["slug"], proj["short_description"],
             proj["start_date"], proj["end_date"], proj["external_url"],
             proj["repo_url"], bool(proj["featured"]), i),
        ).fetchone()["id"]
        for j, body in enumerate(proj["highlights"]):
            cur.execute(
                "INSERT INTO project_highlight (project_id, body, order_index) VALUES (%s, %s, %s)",
                (prid, body, j),
            )

    for i, (name, category, level) in enumerate(SKILLS):
        sid = cur.execute(
            "INSERT INTO skill (name, category, sort_order) VALUES (%s, %s, %s) RETURNING id",
            (name, category, i),
        ).fetchone()["id"]
        cur.execute(
            """INSERT INTO skill_proficiency (profile_id, skill_id, proficiency_level)
               VALUES (%s, %s, %s)""",
            (pid, sid, level),
        )

    for cert in CERTIFICATIONS:
        cur.execute(
            """INSERT INTO certification (profile_id, name, issuer, date_earned, credential_url)
               VALUES (%s, %s, %s, %s, %s)""",
            (pid, cert["name"], cert["issuer"], cert["date_earned"], cert["credential_url"]),
        )

    for i, ach in enumerate(ACHIEVEMENTS):
        cur.execute(
            """INSERT INTO achievement
               (profile_id, title, description, date_earned, source, order_index)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (pid, ach["title"], ach["description"], ach["date_earned"], ach["source"], i),
        )

    conn.commit()

    counts = {}
    for table in ("person_profile", "contact_method", "education_record",
                  "role_experience", "experience_highlight", "project",
                  "project_highlight", "skill", "skill_proficiency",
                  "certification", "achievement"):
        counts[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    return counts


def main() -> None:
    with connect() as conn:
        init_schema(conn)
        counts = seed(conn)
        where = f"{conn.info.host}/{conn.info.dbname}"
    print(f"Seeded {where}")
    for table, n in counts.items():
        print(f"  {table:<22} {n}")
```

- [ ] **Step 4: Port `scripts/init_db.py`**

```python
"""Create (or re-apply) the Career Platform schema. Runs before every Railway deploy.

Usage:  python -m scripts.init_db
"""
from __future__ import annotations

from app.db import connect, init_schema


def main() -> None:
    with connect() as conn:
        init_schema(conn)
        tables = [
            r["table_name"]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
        ]
        where = f"{conn.info.host}/{conn.info.dbname}"
    print(f"Schema applied to {where}")
    print(f"{len(tables)} tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run all tests, then smoke-test the page locally**

Run: `uv run pytest -v` → all pass.

```bash
docker exec career-pg-test createdb -U postgres career_dev
cp .env.example .env                      # replaces the old sqlite:/// URL
uv run python -m scripts.init_db          # expect "14 tables: ..."
uv run python -m scripts.seed_resume
uv run uvicorn app.main:app --port 8000 &
sleep 2; curl -s localhost:8000/ | grep -c "HUM Nutrition"; curl -s localhost:8000/ | grep -c "Showing saved content"; kill %1
```

Expected: `1` or greater for HUM Nutrition, `0` for the banner. The `.env` is gitignored, so check it isn't staged.

- [ ] **Step 6: Commit**

```bash
git add scripts/init_db.py scripts/seed_resume.py tests/test_seed.py
git commit -m "feat: port schema and seed scripts to PostgreSQL"
```

---

## Task 4: Copy the VM's SQLite data into Postgres

**Files:**
- Create: `scripts/copy_sqlite_to_postgres.py`, `tests/test_copy.py`

**Interfaces:**
- Consumes: the `sqlite_source` and `empty_db` fixtures, plus `connect` and `init_schema`.
- Produces: `copy_database(sqlite_path: Path, conn: psycopg.Connection) -> dict[str, int]` and `TargetNotEmpty(RuntimeError)`. The CLI is `python -m scripts.copy_sqlite_to_postgres <sqlite_path>`, with the target taken from `DATABASE_URL`.

- [ ] **Step 1: Write the failing tests**

`tests/test_copy.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_copy.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.copy_sqlite_to_postgres'`.

- [ ] **Step 3: Write the copy script**

`scripts/copy_sqlite_to_postgres.py`:

```python
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Dry run against the real VM data, locally**

```bash
SCRATCH=$(mktemp -d)
scp career-vm:career-platform/data/resume.db "$SCRATCH/vm-resume.db"
docker exec career-pg-test dropdb -U postgres --if-exists career_dryrun
docker exec career-pg-test createdb -U postgres career_dryrun
DATABASE_URL=postgresql://postgres:test@localhost:54329/career_dryrun \
  uv run python -m scripts.copy_sqlite_to_postgres "$SCRATCH/vm-resume.db"
```

Expected counts match the **Starting State** table exactly: 1, 4, 5, 16, 3, 8, 18, 18, 2, 1, 5, 0, 0, 0. Keep `$SCRATCH/vm-resume.db` for Task 6, and **never** copy it into the repo.

- [ ] **Step 6: Commit**

```bash
git add scripts/copy_sqlite_to_postgres.py tests/test_copy.py
git commit -m "feat: add one-shot SQLite-to-Postgres copy"
```

---

## Task 5: Railway build and deploy configuration

**Files:**
- Create: `railway.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: `scripts.init_db` from Task 3.
- Produces: a deploy that runs `python -m scripts.init_db` before each release and serves on `$PORT`, with `/health` as the readiness check.

- [ ] **Step 1: Write `railway.json`**

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "preDeployCommand": ["python -m scripts.init_db"],
    "startCommand": "sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2'",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

`sh -c` makes `$PORT` expand whether or not Railway wraps the command in a shell. `--workers 2` matches the VM. No `--proxy-headers` is needed, because the template links assets by absolute path (`/static/...`) and never builds URLs from the request scheme.

- [ ] **Step 2: Document local development in `README.md`**

```markdown
# career-platform

Database-driven resume site: FastAPI + PostgreSQL, deployed on Railway.

## Run locally

    docker run -d --name career-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=career_test -p 54329:5432 postgres:<PG_MAJOR>
    docker exec career-pg-test createdb -U postgres career_dev
    cp .env.example .env
    uv run python -m scripts.init_db
    uv run python -m scripts.seed_resume
    uv run uvicorn app.main:app --reload

## Test

    docker start career-pg-test
    uv run pytest

Tests wipe the database at `TEST_DATABASE_URL` (default: the local container
above) and refuse to run against any non-local host.
```

Replace `<PG_MAJOR>` with the version recorded in Task 0.

- [ ] **Step 3: Validate the JSON and run the full suite**

```bash
python3 -m json.tool railway.json > /dev/null && echo valid
uv run pytest -q
```

Expected: `valid`, then all tests pass.

- [ ] **Step 4: Commit**

```bash
git add railway.json README.md
git commit -m "build: add Railway deploy configuration"
```

---

## Task 6: Load the live data into Railway Postgres

**Where this runs:** the laptop, against Railway's public Postgres URL. **Ask the owner before Step 2**, because it writes to the production database.

**Interfaces:**
- Consumes: `$SCRATCH/vm-resume.db` from Task 4 Step 5 and `<PG_SERVICE>` from Task 0.
- Produces: Railway Postgres holding the same rows as the VM.

- [ ] **Step 1: Re-fetch the VM database so it's current**

```bash
scp career-vm:career-platform/data/resume.db "$SCRATCH/vm-resume.db"
```

- [ ] **Step 2: Copy into Railway Postgres (owner approval required)**

```bash
PGURL=$(railway variables --service <PG_SERVICE> --kv | sed -n 's/^DATABASE_PUBLIC_URL=//p')
DATABASE_URL="$PGURL" uv run python -m scripts.copy_sqlite_to_postgres "$SCRATCH/vm-resume.db"
```

Expected: `Copied into <proxy host>/railway`, followed by the same counts as the Starting State table. If it raises `TargetNotEmpty`, the database was already loaded. Stop and ask the owner rather than wiping it.

- [ ] **Step 3: Verify the page renders from Railway's database, before deploying anything**

```bash
DATABASE_URL="$PGURL" uv run python -c '
from app.repository import load_profile
from pathlib import Path
d, s = load_profile(snapshot_path=Path("/dev/null/x"))
print(s, d["profile"]["full_name"], len(d["experience"]), [c["type"] for c in d["contacts"]])'
```

Expected: `live Dhwani Jain 5 ['email', 'linkedin', 'github']`. That means live data with no phone. The `/dev/null/x` path makes the snapshot write fail on purpose, so no file gets created in the repo.

- [ ] **Step 4: Record the outcome in the Execution Log and commit the plan**

---

## Task 7: Deploy the web service and verify on the Railway domain

**Where this runs:** the laptop with the Railway CLI. **Ask the owner before Steps 1 and 2.**

**Interfaces:**
- Consumes: `<WEB_SERVICE>`, `<PG_SERVICE>` and the deploy source from Task 0; commits from Tasks 1–5.
- Produces: the site live at `https://<something>.up.railway.app`, which is `<RAILWAY_HOST>` for Task 8.

- [ ] **Step 1: Set the web service's variables (owner approval required)**

```bash
railway variables --service <WEB_SERVICE> \
  --set 'DATABASE_URL=${{<PG_SERVICE>.DATABASE_URL}}' \
  --set 'APP_ENV=production' \
  --set 'APP_NAME=Career Platform'
railway variables --service <WEB_SERVICE> --kv | sed 's/=.*/=<set>/'
```

The single quotes keep `${{…}}` literal, so Railway resolves the reference to the **private** URL. The second command prints the variable names only. Expected: `DATABASE_URL`, `APP_ENV` and `APP_NAME` are present.

- [ ] **Step 2: Deploy (owner approval required)**

If Task 0 found GitHub connected to `main`: `git push origin main`. Otherwise: `railway up --service <WEB_SERVICE> --detach`.

Then:

```bash
railway logs --service <WEB_SERVICE> --deployment | tail -40
```

Expected in the build log: Python 3.13 and `psycopg` installed. In the pre-deploy output: `14 tables: ...`. In the runtime log: `Uvicorn running on http://0.0.0.0:<port>`. If the build installed from `requirements.txt` rather than `uv.lock`, that's fine because both pin the same versions, but note which one it used in the Execution Log.

- [ ] **Step 3: Generate the Railway domain and verify real content (Review Focus 5)**

```bash
railway domain --service <WEB_SERVICE>
H=<RAILWAY_HOST>
curl -sS "https://$H/health"
curl -sS "https://$H/" | grep -c "HUM Nutrition"
curl -sS "https://$H/" | grep -c "Showing saved content"
curl -sS "https://$H/" | grep -c "323"
curl -sS -o /dev/null -w '%{http_code}\n' "https://$H/static/css/styles.css"
```

Expected, in order: `{"status":"ok","app":"Career Platform"}`, then `≥1`, `0` (the page is live, not the fallback), `0` (the phone number is hidden), and `200`.

- [ ] **Step 4: Prove a redeploy keeps working**

```bash
railway redeploy --service <WEB_SERVICE> --yes
```

After it finishes, repeat Step 3. Expected: identical results. This shows the pre-deploy schema step is safe to re-run and the data persists across releases.

- [ ] **Step 5: Record the Railway host in Task 0 findings and log the outcome; commit the plan.**

---

## Task 8: Move `dhwanijain.me` to Railway (owner-executed, then verified)

**For a beginner:** Today Cloudflare's `A` records send visitors to the VM's IP address. Railway doesn't give you a fixed IP. Instead it gives you a **hostname** to point at, using a `CNAME` record. Cloudflare allows a CNAME on the bare domain (`@`) by "flattening" it. Railway also asks for a `TXT` record that proves you own the domain. After that it issues its own Let's Encrypt certificate, and from then on Nginx and Certbot on the VM aren't involved.

**Interfaces:**
- Consumes: `<RAILWAY_HOST>` from Task 7.
- Produces: `https://dhwanijain.me` and `https://www.dhwanijain.me` served by Railway with a valid certificate.

- [ ] **Step 1: Add both custom domains in Railway (owner approval required)**

```bash
railway domain dhwanijain.me --service <WEB_SERVICE>
railway domain www.dhwanijain.me --service <WEB_SERVICE>
```

Each command prints the DNS records Railway wants: a `CNAME` target and a `_railway-verify` `TXT` value. Copy them into the Execution Log. These are not secrets.

- [ ] **Step 2: Owner — update Cloudflare DNS**

In Cloudflare → `dhwanijain.me` → **DNS → Records**:

1. Delete the `A` record for `@` that points at `4.155.216.147`, and add a `CNAME` for `@` → the target Railway gave for `dhwanijain.me`.
2. Delete the `A` record for `www` and add a `CNAME` for `www` → the target Railway gave for `www.dhwanijain.me`.
3. Add each `TXT` verification record exactly as Railway printed it.
4. Leave every record on **DNS only** (gray cloud), as the VM setup did. With the proxy on, Railway can't complete its certificate check.

- [ ] **Step 3: Verify DNS from public resolvers**

```bash
dig +short @8.8.8.8 dhwanijain.me
dig +short @1.1.1.1 www.dhwanijain.me
```

Expected: Railway addresses, **not** `4.155.216.147`. If an address starts with `104.` or `172.67.`, the Cloudflare proxy is on.

- [ ] **Step 4: Verify Railway issued the certificate and serves the real page**

Wait until the Railway dashboard shows both domains with a green check (usually minutes). Then run this from the VM, which is outside LMU's network:

```bash
ssh career-vm 'for h in dhwanijain.me www.dhwanijain.me; do
  curl -sS -o /dev/null -w "$h %{http_code} " "https://$h/"
  curl -sS "https://$h/" | grep -c "HUM Nutrition"
  echo | openssl s_client -connect $h:443 -servername $h 2>/dev/null | openssl x509 -noout -issuer -subject -enddate
done
curl -sS -o /dev/null -w "http->%{http_code} %{redirect_url}\n" http://dhwanijain.me/'
```

Expected: `200` and `≥1` for both names, a Let's Encrypt issuer, a subject that matches each name, and plain HTTP redirecting (`301`/`308`) to `https://`.

**Rollback for Task 8:** restore the two `A` records to `4.155.216.147` and delete the CNAMEs. The VM still has Nginx, its certificate and its data, so it resumes serving within the DNS TTL.

- [ ] **Step 5: Log the outcome with the cert issuer and expiry; commit the plan.**

---

## Task 9: Retire the VM and update the records

**Do not start until Task 8 has passed, and the site has served from Railway for at least 24 hours with no fallback banner.**

- [ ] **Step 1: Final data check — has anything changed on the VM since the copy?**

```bash
ssh career-vm 'stat -c %y ~/career-platform/data/resume.db'
```

Expected: a timestamp older than Task 6 Step 1. If it's newer, someone edited the VM's data after the copy. Stop and reconcile before going further.

- [ ] **Step 2: Owner — stop the VM in the Azure portal**

Azure portal → `vm-career-platform` → **Stop**. Wait for **Status: Stopped (deallocated)**. Don't delete the VM or its disk. The static public IP stays allocated, and Azure keeps billing for it, so note that cost in the log.

- [ ] **Step 3: Verify the site is unaffected**

```bash
curl -sS "https://dhwanijain.me/" | grep -c "HUM Nutrition"
curl -sS "https://dhwanijain.me/" | grep -c "Showing saved content"
```

Expected: `≥1`, then `0`.

- [ ] **Step 4: Update `docs/how-this-site-is-secured.md`**

Add a dated section at the top saying that, as of the Task 8 date, the site runs on Railway. TLS is now terminated by Railway, which renews the certificate automatically. The database is Railway Postgres, reached over Railway's private network. The Azure VM, Nginx and Certbot sections describe the retired setup and stay as history.

- [ ] **Step 5: Commit**

```bash
git add docs/how-this-site-is-secured.md docs/superpowers/plans/2026-10-08-railway-postgres-migration.md
git commit -m "docs: record the move to Railway and retire the VM"
```

---

## Task 0 findings

_Filled in during Task 0._

| Item | Value |
|---|---|
| `<PG_SERVICE>` | |
| `<WEB_SERVICE>` | |
| `<PG_MAJOR>` | |
| Deploy source | |
| `<RAILWAY_HOST>` | |

## Execution Log

_Append a dated entry as each task completes: what was verified, what deviated from the plan, and any blockers._
