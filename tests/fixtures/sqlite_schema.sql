-- Frozen copy of the SQLite schema the Azure VM ran (commit a987583). Used only
-- as the source side of tests/test_copy.py. The live schema is app/schema.sql.
-- Career Platform schema
-- Mirrors the content model in docs/specs/career-platform-app-spec.md section 7.

PRAGMA foreign_keys = ON;

-- 7.1 PersonProfile -----------------------------------------------------
CREATE TABLE IF NOT EXISTS person_profile (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name           TEXT NOT NULL,
    headline            TEXT,
    summary             TEXT,
    location            TEXT,
    pronouns            TEXT,
    preferred_role      TEXT,
    availability_status TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.2 ContactMethod -----------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_method (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    label       TEXT,
    value       TEXT NOT NULL,
    url         TEXT,
    is_primary  INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (profile_id, type, value)
);

-- 7.3 RoleExperience ----------------------------------------------------
CREATE TABLE IF NOT EXISTS role_experience (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    company_name    TEXT NOT NULL,
    role_title      TEXT NOT NULL,
    employment_type TEXT,
    location        TEXT,
    start_date      TEXT,
    end_date        TEXT,
    is_current      INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
    summary         TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'published', 'archived')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (profile_id, company_name, role_title, start_date),
    CHECK (is_current = 0 OR end_date IS NULL)
);

-- Resume bullets for a role. Split into rows so the admin UI can reorder
-- and edit them individually (spec 6.2) instead of editing one blob.
CREATE TABLE IF NOT EXISTS experience_highlight (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    experience_id INTEGER NOT NULL REFERENCES role_experience(id) ON DELETE CASCADE,
    body          TEXT NOT NULL,
    order_index   INTEGER NOT NULL DEFAULT 0
);

-- 7.4 Project -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS project (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id        INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    title             TEXT NOT NULL,
    slug              TEXT NOT NULL UNIQUE,
    short_description TEXT,
    long_description  TEXT,
    status            TEXT NOT NULL DEFAULT 'published'
                      CHECK (status IN ('draft', 'published', 'archived')),
    start_date        TEXT,
    end_date          TEXT,
    external_url      TEXT,
    repo_url          TEXT,
    featured          INTEGER NOT NULL DEFAULT 0 CHECK (featured IN (0, 1)),
    image_url         TEXT,
    order_index       INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS project_highlight (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    body        TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0
);

-- 7.5 Skill -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.6 SkillProficiency --------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_proficiency (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id        INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    skill_id          INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    proficiency_level TEXT,
    years_experience  REAL,
    notes             TEXT,
    UNIQUE (profile_id, skill_id)
);

-- 7.7 EducationRecord ---------------------------------------------------
CREATE TABLE IF NOT EXISTS education_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    institution     TEXT NOT NULL,
    degree          TEXT,
    field_of_study  TEXT,
    location        TEXT,
    start_date      TEXT,
    end_date        TEXT,
    is_expected     INTEGER NOT NULL DEFAULT 0 CHECK (is_expected IN (0, 1)),
    description     TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'published'
                    CHECK (status IN ('draft', 'published', 'archived')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.8 Certification -----------------------------------------------------
CREATE TABLE IF NOT EXISTS certification (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id     INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    issuer         TEXT,
    date_earned    TEXT,
    credential_url TEXT,
    status         TEXT NOT NULL DEFAULT 'published'
                   CHECK (status IN ('draft', 'published', 'archived')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.9 Achievement -------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievement (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    date_earned TEXT,
    source      TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'published'
                CHECK (status IN ('draft', 'published', 'archived')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.10 ContentSection ---------------------------------------------------
CREATE TABLE IF NOT EXISTS content_section (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id   INTEGER NOT NULL REFERENCES person_profile(id) ON DELETE CASCADE,
    section_type TEXT NOT NULL,
    title        TEXT,
    body         TEXT,
    order_index  INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0, 1)),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 7.11 Tag / EntityTag --------------------------------------------------
CREATE TABLE IF NOT EXISTS tag (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    slug       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS entity_tag (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
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
