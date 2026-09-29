# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Career Platform FastAPI app from the local laptop onto the existing Azure VM, running under systemd and serving the real resume data from SQLite.

**Architecture:** The VM pulls application code from GitHub and installs dependencies with `uv` from a committed lock file, so the VM's Python environment is reproducible rather than hand-assembled. Runtime configuration comes from a `.env` file derived from a committed `.env.example`. The resume database is *not* shipped through git — it is copied laptop-to-VM over `scp`, keeping personal data out of the public repository. Uvicorn runs as a systemd service so it survives logout and reboot.

**Tech Stack:** Ubuntu (Azure VM), git, sqlite3, uv, Python 3.13, FastAPI 0.115.0, Uvicorn 0.30.6, Jinja2 3.1.4, systemd

**Spec:** `docs/specs/career-platform-app-spec.md` (deployment direction: `docs/plans/implementation-plan.md` §1, "local Codespace first, then eventual Azure VM deployment")

## Global Constraints

- **SSH identity:** always `-i ~/.ssh/isba4775_azure`, user `azureuser`, host `4.155.216.147`. Never use a different key or user.
- **VM:** `vm-career-platform` in resource group `rg-career-platform`.
- **Repo:** `https://github.com/djain2905/career-platform.git`, branch `main`.
- **App root on VM:** `/home/azureuser/career-platform`.
- **Python version:** 3.13 on both laptop and VM (pinned via `.python-version`; `uv` provisions it).
- **Dependency versions are frozen** at the values already in `requirements.txt`: `fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `jinja2==3.1.4`, `python-dotenv==1.0.1`. Do not upgrade them during migration.
- **Personal data never goes to GitHub.** `data/*.db` must be untracked and gitignored before any push.
- **Azure resource changes require explicit owner approval.** Exactly one is needed (an inbound NSG rule, Task 7.3). Nothing else in this plan creates or modifies Azure resources.

## Preflight Findings

This plan was written against the live repository on 2026-09-24. Four steps in the original migration outline cannot run as written today. Section 0 fixes each on the laptop before the VM is touched.

| Outline step | Problem found | Fixed in |
|---|---|---|
| "uv sync from the lock file" | No `pyproject.toml` and no `uv.lock` exist in the repo. | Task 0.2 |
| "copy .env from .env.example" | No `.env.example` exists in the repo. | Task 0.3 |
| "git clone from GitHub" | `app/db.py`, `app/schema.sql` and `scripts/` are uncommitted. A clone today produces a VM that cannot build or seed the database. | Task 0.4 |
| "scp my SQLite .db file" | `data/resume.db` is *tracked in git*, so the clone delivers a stale copy that `scp` then overwrites — and the personal data in it is published to GitHub. | Task 0.1 |

A fifth issue affects the final section: **the app contains no database reads.** `app/main.py` exposes only `/health` and `/`, and `app/templates/index.html` renders `{{ app_name }}` against a static placeholder. "The site shows my data" therefore cannot pass in this migration. Task 8 verifies what is genuinely true after migration — the data is present and queryable on the VM, and the site answers over the public internet — and Task 8.4 records the remaining gap explicitly rather than papering over it.

---

## Section 0: Prerequisites (laptop)

*Added to the owner's outline. Every step here runs on the laptop and must be pushed before the VM clones anything.*

### Task 0.1: Remove the database from version control

**Files:**
- Modify: `.gitignore`
- Untrack: `data/resume.db`

- [x] **Step 1: Untrack the database and ignore it**

**Where:** laptop
**What to run:**
```bash
cd ~/isba-4775/career-platform
printf '\n# Local database — personal data, never committed\ndata/*.db\ndata/*.db-journal\ndata/*.db-wal\n' >> .gitignore
git rm --cached data/resume.db
```
**Why:** The database holds a phone number, an email address and a full work history. It is currently tracked, so every push publishes it to a GitHub repository. It also breaks the migration mechanically: the clone would place a stale `resume.db` on the VM that the `scp` in Task 6 then overwrites, leaving the VM's working tree permanently dirty.
**How we check it worked:**
```bash
git ls-files data/          # expect: no output
test -f data/resume.db && echo "local file still present (correct)"
git check-ignore -v data/resume.db   # expect: a .gitignore match
```
**How we undo it:** `git checkout .gitignore && git add -f data/resume.db`

- [x] **Step 2: Commit**

**Where:** laptop
**What to run:**
```bash
git add .gitignore
git commit -m "chore: untrack local sqlite database"
```
**Why:** Isolates the privacy fix in one reviewable commit.
**How we check it worked:** `git show --stat HEAD` lists `.gitignore` and the deletion of `data/resume.db`.
**How we undo it:** `git reset --hard HEAD~1` (the local `data/resume.db` file is untouched by this, since it is now untracked).

---

### Task 0.2: Create the uv project and lock file

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `uv.lock` (generated)

- [x] **Step 1: Confirm uv is installed on the laptop**

**Where:** laptop
**What to run:**
```bash
uv --version || curl -LsSf https://astral.sh/uv/install.sh | sh
```
**Why:** The whole Python section depends on `uv`. Establish it before writing files that assume it.
**How we check it worked:** `uv --version` prints a version.
**How we undo it:** `rm -rf ~/.local/bin/uv ~/.local/share/uv`

- [x] **Step 2: Write pyproject.toml**

**Where:** laptop
**What to run:**
```bash
cat > pyproject.toml <<'EOF'
[project]
name = "career-platform"
version = "0.1.0"
description = "Database-driven resume and portfolio site"
requires-python = ">=3.13"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "jinja2==3.1.4",
    "python-dotenv==1.0.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
EOF
echo "3.13" > .python-version
```
**Why:** `uv sync` needs a declared project. Dependency versions are copied verbatim from `requirements.txt` so the VM gets exactly what the laptop has been running. `.python-version` makes `uv` provision Python 3.13 on the VM even though Ubuntu ships 3.12, removing a whole class of version-drift bugs.
**How we check it worked:** `test -f pyproject.toml && test -f .python-version && cat .python-version`
**How we undo it:** `rm pyproject.toml .python-version`

- [x] **Step 3: Generate the lock file**

**Where:** laptop
**What to run:**
```bash
uv lock
```
**Why:** The lock file pins the full transitive dependency tree by hash. This is what makes `uv sync --frozen` on the VM reproducible instead of "whatever PyPI served that day."
**How we check it worked:**
```bash
test -f uv.lock && grep -c 'name = ' uv.lock   # expect a count well above 4 (transitive deps)
```
**How we undo it:** `rm uv.lock`

- [x] **Step 4: Verify the locked environment actually runs the app**

**Where:** laptop
**What to run:**
```bash
uv sync --frozen
uv run uvicorn app.main:app --port 8001 &
sleep 3
curl -s http://127.0.0.1:8001/health
kill %1
```
**Why:** Catch a broken lock file on the laptop, where it costs a minute, rather than on the VM where it costs a debugging session over SSH.
**How we check it worked:** the curl prints `{"status":"ok","app":"Career Platform"}`.
**How we undo it:** `rm -rf .venv`

- [x] **Step 5: Commit**

**Where:** laptop
**What to run:**
```bash
git add pyproject.toml uv.lock .python-version
git commit -m "build: add uv project definition and lock file"
```
**How we check it worked:** `git show --stat HEAD` lists all three files.
**How we undo it:** `git reset --hard HEAD~1`

---

### Task 0.3: Create .env.example

**Files:**
- Create: `.env.example`

- [x] **Step 1: Write the example config**

**Where:** laptop
**What to run:**
```bash
cat > .env.example <<'EOF'
# Copy to .env and adjust per environment.
APP_NAME=Career Platform
APP_ENV=development
DATABASE_URL=sqlite:///./data/resume.db
EOF
```
**Why:** `app/config.py` already reads `APP_NAME`, `APP_ENV` and `DATABASE_URL` via `load_dotenv`. Those three keys are the complete contract, but nothing in the repo documents them, so the VM operator would be guessing. `.gitignore` already excludes `.env`, so the example file is the only way the key names travel.
**How we check it worked:**
```bash
cat .env.example
grep -o 'os.getenv("[A-Z_]*"' app/config.py   # every key printed must appear in .env.example
```
**How we undo it:** `rm .env.example`

- [x] **Step 2: Commit**

**Where:** laptop
**What to run:**
```bash
git add .env.example
git commit -m "docs: add .env.example documenting runtime config keys"
```
**How we check it worked:** `git ls-files .env.example` prints the path.
**How we undo it:** `git reset --hard HEAD~1`

---

### Task 0.4: Commit the schema and seed code, then push

**Files:**
- Commit: `app/db.py`, `app/schema.sql`, `scripts/__init__.py`, `scripts/init_db.py`, `scripts/seed_resume.py`

- [x] **Step 1: Commit the untracked database code**

**Where:** laptop
**What to run:**
```bash
git add app/db.py app/schema.sql scripts/
git commit -m "feat: add sqlite schema, db helper, and resume seed script"
```
**Why:** These five files are untracked right now. Without them the VM can clone the repo and still have no way to create the schema — and no way to rebuild the database if the `scp` in Task 6 ever needs redoing.
**How we check it worked:**
```bash
git status --short    # expect: clean
git ls-files app/db.py app/schema.sql scripts/
```
**How we undo it:** `git reset --soft HEAD~1`

- [x] **Step 2: Push everything to GitHub**

**Where:** laptop
**What to run:**
```bash
git push origin main
```
**Why:** The VM clones from GitHub. Nothing committed locally reaches the VM until it is pushed.
**How we check it worked:**
```bash
git status -sb        # expect: "## main...origin/main" with no ahead/behind marker
```
**How we undo it:** `git push --force-with-lease origin HEAD~4:main` — destructive and rewrites shared history. Prefer `git revert <sha>` followed by a normal push.

- [x] **Step 3: Confirm the database is genuinely absent from the remote**

**Where:** laptop
**What to run:**
```bash
git ls-tree -r origin/main --name-only | grep -i '\.db$' && echo "FAIL: db still on remote" || echo "OK: no database on remote"
```
**Why:** This is the gate on the privacy fix. Verify it against the *remote* tree, not the local index.
**How we check it worked:** prints `OK: no database on remote`.
**How we undo it:** n/a — read-only check.

> **Note on history:** this removes the database from the current tree, not from past commits. The blob remains reachable in history on GitHub. The file was 0 bytes until the seed ran on 2026-09-22, so whether any real data was ever pushed depends on what was committed after that. Confirm with `git log --oneline --all -- data/resume.db` and, if a populated version was pushed, treat purging history (`git filter-repo`) as separate follow-up work outside this migration.

---

## Section 1: Server

### Task 1: Establish SSH access to the VM

**Files:**
- Create: `~/.ssh/config` entry (laptop)

- [ ] **Step 1: Confirm the key pair exists**

**Where:** laptop
**What to run:**
```bash
ls -l ~/.ssh/isba4775_azure ~/.ssh/isba4775_azure.pub
ssh-keygen -lf ~/.ssh/isba4775_azure.pub
```
**Why:** Every later step depends on this key. Confirm it before blaming the network.
**How we check it worked:** private key shows mode `-rw-------`; fingerprint prints `SHA256:Otu9QvItNrvgJe+c8gW9PmzwjepA5nerMr8lqMySg7U`.
**How we undo it:** n/a — read-only check.

- [ ] **Step 2: Open a first connection**

**Where:** laptop
**What to run:**
```bash
ssh -i ~/.ssh/isba4775_azure azureuser@4.155.216.147 'whoami && hostname && lsb_release -ds'
```
**Why:** Proves the key is installed on the VM, the NSG allows port 22 from this laptop, and confirms the OS release that the `apt-get` step assumes.
**How we check it worked:** prints `azureuser`, a hostname, and an Ubuntu version string.
**How we undo it:** n/a — read-only.

> If this hangs or times out, the likely cause is the NSG's port-22 source restriction versus this laptop's current public IP (`157.242.208.113` as of 2026-09-24, and dynamic — it changes). Check the inbound rule in the portal before debugging anything else.

- [ ] **Step 3: Add an SSH config alias**

**Where:** laptop
**What to run:**
```bash
cat >> ~/.ssh/config <<'EOF'

Host career-vm
    HostName 4.155.216.147
    User azureuser
    IdentityFile ~/.ssh/isba4775_azure
    IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```
**Why:** Removes the chance of a later step silently using the wrong key or user — the global constraint becomes mechanical instead of remembered.
**How we check it worked:** `ssh career-vm 'whoami'` prints `azureuser`.
**How we undo it:** delete the `Host career-vm` block from `~/.ssh/config`.

> Later sections use `ssh career-vm` for brevity. The explicit `-i ~/.ssh/isba4775_azure azureuser@4.155.216.147` form is always equivalent.

---

## Section 2: Packages

### Task 2: Install system packages

- [ ] **Step 1: Refresh the package index and install**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'sudo apt-get update && sudo apt-get install -y git sqlite3'
```
**Why:** `git` clones the code in Section 3. `sqlite3` is the CLI used to verify the database in Sections 6 and 8 — the Python `sqlite3` module is built in and does not provide a shell. `-y` avoids an interactive prompt that would hang a non-interactive SSH command.
**How we check it worked:**
```bash
ssh career-vm 'git --version && sqlite3 --version'
```
Expect a version line from each.
**How we undo it:** `ssh career-vm 'sudo apt-get remove -y sqlite3'` — do not remove `git`, other system tooling depends on it.

- [ ] **Step 2: Confirm curl is present for the uv installer**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'curl --version | head -1 || sudo apt-get install -y curl'
```
**Why:** Task 4 installs `uv` via a `curl` pipeline. Ubuntu server images usually include curl, but confirm rather than assume.
**How we check it worked:** a `curl 8.x` version line prints.
**How we undo it:** n/a — curl is a base system tool, leave it installed.

---

## Section 3: Code

### Task 3: Clone the repository onto the VM

- [ ] **Step 1: Clone**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'git clone https://github.com/djain2905/career-platform.git ~/career-platform'
```
**Why:** Public HTTPS clone needs no deploy key or credential on the VM. The path matches the `App root on VM` global constraint that every later step assumes.
**How we check it worked:**
```bash
ssh career-vm 'cd ~/career-platform && git log --oneline -1 && ls app/ scripts/'
```
The log line must match the laptop's `git rev-parse --short HEAD`, and `app/db.py`, `app/schema.sql` and `scripts/seed_resume.py` must all be listed.
**How we undo it:** `ssh career-vm 'rm -rf ~/career-platform'`

- [ ] **Step 2: Confirm the prerequisites actually arrived**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && ls -l pyproject.toml uv.lock .python-version .env.example && ls data/ 2>/dev/null'
```
**Why:** This is the gate on Section 0. If `uv.lock` or `.env.example` is missing, Sections 4 and 5 will fail — stop here and push from the laptop instead of improvising on the VM. `data/` should be absent or empty, confirming the database did not travel through git.
**How we check it worked:** all four files listed; no `resume.db` in `data/`.
**How we undo it:** n/a — read-only check.

---

## Section 4: Python

### Task 4: Install uv and sync the environment

- [ ] **Step 1: Install uv**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```
**Why:** Installs to `~/.local/bin` under `azureuser`, so no `sudo` and no interference with the system Python that Ubuntu's own tooling depends on.
**How we check it worked:**
```bash
ssh career-vm '~/.local/bin/uv --version'
```
**How we undo it:** `ssh career-vm 'rm -rf ~/.local/bin/uv ~/.local/bin/uvx ~/.local/share/uv'`

- [ ] **Step 2: Sync the locked environment**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && ~/.local/bin/uv sync --frozen'
```
**Why:** `--frozen` makes `uv` install exactly what `uv.lock` specifies and fail loudly if the lock file disagrees with `pyproject.toml`, rather than silently re-resolving and drifting from the laptop. `uv` also provisions Python 3.13 here, per `.python-version`.
**How we check it worked:**
```bash
ssh career-vm 'cd ~/career-platform && ~/.local/bin/uv run python -c "import fastapi, uvicorn, jinja2, dotenv; print(fastapi.__version__)"'
```
Expect `0.115.0`.
**How we undo it:** `ssh career-vm 'rm -rf ~/career-platform/.venv'`

- [ ] **Step 3: Confirm the app imports**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && ~/.local/bin/uv run python -c "from app.main import app; print(len(app.routes), \"routes\")"'
```
**Why:** Separates an import/dependency failure from a runtime serving failure. If this fails, Section 7 would fail for the same reason but with a far noisier error.
**How we check it worked:** prints a route count.
**How we undo it:** n/a — read-only check.

---

## Section 5: Config

### Task 5: Create the VM's .env

- [ ] **Step 1: Copy the example**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && cp .env.example .env'
```
**Why:** `app/config.py` calls `load_dotenv(BASE_DIR / ".env")`. Without this file the app still starts on defaults, but nothing is environment-specific and `APP_ENV` wrongly reports `development`.
**How we check it worked:** `ssh career-vm 'cat ~/career-platform/.env'`
**How we undo it:** `ssh career-vm 'rm ~/career-platform/.env'`

- [ ] **Step 2: Set the environment to production**

**Where:** VM
**What to run:**
```bash
ssh career-vm "cd ~/career-platform && sed -i 's/^APP_ENV=.*/APP_ENV=production/' .env && cat .env"
```
**Why:** The VM is not a development box. `DATABASE_URL` stays at the relative `sqlite:///./data/resume.db` because `app/db.py` resolves it against `BASE_DIR`, so it is already correct on the VM.
**How we check it worked:** the printed file shows `APP_ENV=production`.
**How we undo it:** `ssh career-vm "cd ~/career-platform && sed -i 's/^APP_ENV=.*/APP_ENV=development/' .env"`

- [ ] **Step 3: Restrict permissions**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'chmod 600 ~/career-platform/.env && ls -l ~/career-platform/.env'
```
**Why:** `.env` is the file that will hold secrets as the app grows (admin credentials, per spec §9.2). Establish the permission habit now, while the file is still harmless.
**How we check it worked:** mode reads `-rw-------`.
**How we undo it:** `ssh career-vm 'chmod 644 ~/career-platform/.env'`

---

## Section 6: Data

### Task 6: Copy the SQLite database to the VM

- [ ] **Step 1: Verify the source database on the laptop**

**Where:** laptop
**What to run:**
```bash
cd ~/isba-4775/career-platform
sqlite3 data/resume.db "SELECT full_name FROM person_profile;"
sqlite3 data/resume.db "SELECT COUNT(*) FROM role_experience;"
shasum -a 256 data/resume.db
```
**Why:** Establish what "correct" looks like before the copy, so the post-copy check has something to compare against. Record the checksum.
**How we check it worked:** prints `Dhwani Jain`, then `5`, then a SHA-256 hash.
**How we undo it:** n/a — read-only.

- [ ] **Step 2: Create the destination directory**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'mkdir -p ~/career-platform/data'
```
**Why:** `data/` is no longer in git (Task 0.1), so the clone did not create it. `scp` will not create a missing parent directory.
**How we check it worked:** `ssh career-vm 'ls -ld ~/career-platform/data'`
**How we undo it:** `ssh career-vm 'rmdir ~/career-platform/data'`

- [ ] **Step 3: Copy the database**

**Where:** laptop
**What to run:**
```bash
cd ~/isba-4775/career-platform
scp -i ~/.ssh/isba4775_azure data/resume.db azureuser@4.155.216.147:~/career-platform/data/resume.db
```
**Why:** The database carries personal data and is deliberately excluded from git, so `scp` is the transport. Copying the file directly (rather than re-running the seed on the VM) guarantees the VM serves byte-identical content to what was reviewed on the laptop.
**How we check it worked:**
```bash
ssh career-vm 'sha256sum ~/career-platform/data/resume.db'
```
Must equal the laptop checksum from Step 1.
**How we undo it:** `ssh career-vm 'rm ~/career-platform/data/resume.db'`

> The app must not be running during this copy. On a first migration it is not running yet. When repeating this step later, stop the service first (`sudo systemctl stop career-platform`) so SQLite is not overwritten mid-write.

- [ ] **Step 4: Verify the data on the VM**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && sqlite3 data/resume.db "SELECT full_name, headline FROM person_profile;" && sqlite3 data/resume.db "SELECT company_name FROM role_experience ORDER BY order_index;" && sqlite3 data/resume.db "SELECT COUNT(*) FROM experience_highlight;"'
```
**Why:** Confirms the file is a readable SQLite database on the VM and not a truncated transfer — a checksum match proves the bytes arrived, this proves they are queryable.
**How we check it worked:** prints `Dhwani Jain` with the headline, five company names beginning with `HUM Nutrition`, then `16`.
**How we undo it:** n/a — read-only.

- [ ] **Step 5: Set file permissions**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'chmod 600 ~/career-platform/data/resume.db && ls -l ~/career-platform/data/resume.db'
```
**Why:** The database holds personal contact details. Only `azureuser`, which is also the service account in Section 7, needs to read it.
**How we check it worked:** mode reads `-rw-------`.
**How we undo it:** `ssh career-vm 'chmod 644 ~/career-platform/data/resume.db'`

---

## Section 7: Processes

### Task 7: Run uvicorn under systemd

**Files:**
- Create: `/etc/systemd/system/career-platform.service` (VM)

- [ ] **Step 1: Smoke-test uvicorn in the foreground**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && (timeout 10 ~/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/uvicorn-smoke.log 2>&1 &) && sleep 5 && curl -s http://127.0.0.1:8000/health; echo'
```
**Why:** Confirms the app serves before adding systemd on top. Debugging a foreground process is far easier than debugging a unit file that fails at boot.
**How we check it worked:** prints `{"status":"ok","app":"Career Platform"}`.
**How we undo it:** the `timeout 10` ends the process on its own.

- [ ] **Step 2: Write the systemd unit**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'sudo tee /etc/systemd/system/career-platform.service > /dev/null <<EOF
[Unit]
Description=Career Platform FastAPI site
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/career-platform
ExecStart=/home/azureuser/.local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'
```
**Why:** A bare `uvicorn` in an SSH session dies on logout and does not survive reboot. `Restart=on-failure` covers crashes; `User=azureuser` keeps the service unprivileged and matches the file ownership set in Sections 5 and 6. `--host 0.0.0.0` is required for the VM to accept traffic from outside itself — `127.0.0.1` would answer only locally.
**How we check it worked:** `ssh career-vm 'sudo systemd-analyze verify /etc/systemd/system/career-platform.service && cat /etc/systemd/system/career-platform.service'` — verify prints no errors.
**How we undo it:** `ssh career-vm 'sudo rm /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload'`

- [ ] **Step 3: Open port 8000 in the network security group**

**Where:** Azure portal — **requires owner approval before running (this is the plan's only Azure resource change)**
**What to click:** Portal → Resource groups → `rg-career-platform` → the NSG attached to `vm-career-platform` → Settings → Inbound security rules → **+ Add**. Set Source `IP Addresses`, Source IP `157.242.208.113/32`, Destination `Any`, Service `Custom`, Destination port ranges `8000`, Protocol `TCP`, Action `Allow`, Priority `1010`, Name `allow-http-8000`.
**Why:** Azure NSGs deny inbound traffic by default, so the site is unreachable from the laptop until a rule exists. Scoping the source to this laptop's IP keeps an unauthenticated, plain-HTTP app off the open internet during testing.
**How we check it worked:** Task 8 Step 2's `curl` from the laptop succeeds.
**How we undo it:** delete the `allow-http-8000` inbound rule in the same blade.

> The laptop IP `157.242.208.113` is dynamic and will change. When the site stops answering from the laptop but answers on the VM's own loopback, this rule is the first thing to re-check. Widening the source to `0.0.0.0/0` would expose an unauthenticated admin-less app over plain HTTP — do not do it as a debugging shortcut.

- [ ] **Step 4: Enable and start the service**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'sudo systemctl daemon-reload && sudo systemctl enable --now career-platform'
```
**Why:** `daemon-reload` makes systemd read the new unit; `enable --now` starts it immediately and registers it to start on boot.
**How we check it worked:**
```bash
ssh career-vm 'systemctl is-active career-platform && systemctl is-enabled career-platform'
```
Expect `active` and `enabled`.
**How we undo it:** `ssh career-vm 'sudo systemctl disable --now career-platform'`

- [ ] **Step 5: Check the service logs**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'sudo journalctl -u career-platform -n 30 --no-pager'
```
**Why:** A unit can report `active` while the app logs startup errors on every restart attempt. Read the logs before declaring success.
**How we check it worked:** logs show `Uvicorn running on http://0.0.0.0:8000` and no tracebacks.
**How we undo it:** n/a — read-only.

---

## Section 8: Verify

### Task 8: Confirm the site answers and the data is live

- [ ] **Step 1: Verify from the VM itself**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'curl -s http://127.0.0.1:8000/health; echo; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/'
```
**Why:** Isolates "the app works" from "the network allows reaching it." If this passes and Step 2 fails, the fault is the NSG rule, not the app.
**How we check it worked:** `{"status":"ok","app":"Career Platform"}` then `200`.
**How we undo it:** n/a — read-only.

- [ ] **Step 2: Verify from the laptop over the public IP**

**Where:** laptop
**What to run:**
```bash
curl -s --max-time 10 http://4.155.216.147:8000/health; echo
curl -s --max-time 10 http://4.155.216.147:8000/ | head -20
```
**Why:** This is the real acceptance test — the site answering over the public internet, which is what the migration set out to achieve.
**How we check it worked:** the health JSON prints, and the HTML includes `<title>Career Platform</title>`.
**How we undo it:** n/a — read-only.

- [ ] **Step 3: Verify the migrated data is live on the VM**

**Where:** VM
**What to run:**
```bash
ssh career-vm 'cd ~/career-platform && sqlite3 data/resume.db "SELECT (SELECT COUNT(*) FROM role_experience) || \" roles, \" || (SELECT COUNT(*) FROM project) || \" projects, \" || (SELECT COUNT(*) FROM skill) || \" skills, \" || (SELECT COUNT(*) FROM achievement) || \" achievements\";"'
```
**Why:** Confirms the full record set survived the transfer, matching the counts verified on the laptop when the resume was seeded.
**How we check it worked:** prints `5 roles, 3 projects, 18 skills, 5 achievements`.
**How we undo it:** n/a — read-only.

- [ ] **Step 4: Record the known gap**

**Where:** laptop
**What to run:**
```bash
cd ~/isba-4775/career-platform
cat >> docs/plans/implementation-plan.md <<'EOF'

## Post-migration status (2026-09-24)

The app is deployed on the Azure VM and serving. The database is present on the
VM with the full resume loaded. The public site does not yet render that data:
`app/main.py` exposes only `/health` and `/`, and `app/templates/index.html`
renders a static placeholder. Wiring public pages to the database (spec §6.1)
is the next task and is deliberately out of scope for the migration.
EOF
git add docs/plans/implementation-plan.md
git commit -m "docs: record post-migration status and remaining gap"
git push origin main
```
**Why:** The outline's goal was "the site answers on the VM and shows my data." After this migration the first half is true and the second is not, because no route reads the database. Recording that in the plan document keeps the gap visible instead of leaving a half-true success claim.
**How we check it worked:** `git log --oneline -1` shows the docs commit; `tail -12 docs/plans/implementation-plan.md` shows the new section.
**How we undo it:** `git reset --hard HEAD~1` then `git push --force-with-lease origin main`.

---

## Rollback: full teardown

To return the VM to its pre-migration state, in reverse order:

```bash
ssh career-vm 'sudo systemctl disable --now career-platform'
ssh career-vm 'sudo rm -f /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload'
ssh career-vm 'rm -rf ~/career-platform'
ssh career-vm 'rm -rf ~/.local/bin/uv ~/.local/bin/uvx ~/.local/share/uv'
ssh career-vm 'sudo apt-get remove -y sqlite3'
```
Then delete the `allow-http-8000` inbound NSG rule in the portal. The VM itself, its public IP, and the SSH key are left intact.
