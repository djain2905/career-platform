# AWS EC2 + RDS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `dhwanijain.me` from Railway to AWS. The FastAPI app runs on one EC2 instance behind Nginx and Let's Encrypt, and reads from a Single-AZ RDS PostgreSQL 18 database that only the instance can reach.

**Architecture:** One Ubuntu 24.04 `t3.micro` instance in the default VPC has an Elastic IP. Nginx on ports 80 and 443 proxies to Uvicorn on `127.0.0.1:8000`, run by systemd, the same layout as the Azure VM. RDS `db.t4g.micro` sits in the same Availability Zone, is not publicly accessible, and has a security group that only admits the web server's security group. The app connects as a non-master role over TLS with `sslmode=verify-full`. Deploy configuration (the systemd unit, the Nginx site and the deploy script) is committed under `deploy/aws/` and tested, which replaces what `railway.json` did. Data moves with `pg_dump`/`pg_restore`: a rehearsal from the 2026-10-29 backup, then a fresh dump at cutover.

**Tech Stack:** AWS CLI v2 (profile `isba-4775`), EC2, RDS PostgreSQL 18.6, Ubuntu 24.04 LTS (amd64), Nginx, Certbot, systemd, uv, Python 3.13, FastAPI 0.115.0, Uvicorn 0.30.6, psycopg 3.3.6, PGDG `postgresql-client-18`, Cloudflare DNS

**Spec:** `docs/superpowers/specs/2026-09-15-career-platform-app-spec.md` (app behavior, unchanged by this move). The deployment decisions below were made with the owner on 2026-11-03.

## Decisions (owner, 2026-11-03)

| Decision | Choice |
|---|---|
| Target | EC2 for the app, Single-AZ RDS PostgreSQL. Not Lambda, not Postgres on the instance |
| Build method | AWS CLI commands, run one at a time, each recorded with its output in the Execution Log. Not the console, not CloudFormation |
| Cutover | Short downtime. Freeze edits, take a fresh dump, restore, switch the apex DNS. Railway stays up about a day as the rollback, then is deleted |
| Branch | All work on `aws-ec2-rds-migration`. **Not merged to `main` until Railway is retired** (Task 9), because Railway redeploys on every push to `main` |
| Account plan | Stay on the AWS **Free plan** with 1-day RDS backups (owner, 2026-11-03). 7 days was refused with `FreeTierRestrictionError`. There are no charges, but the account closes 6 months after signup or when credits run out, whichever comes first. At $26.50/month, $100 of credit lasts about 3.8 months. (2026-11-08: the account actually has $140 in credits, about 5.3 months.) Upgrade to Paid before then to keep the site |
| Revision (2026-11-08) | Railway's trial ended, and the site has returned 404 since then. Restore from the Oct 29 dump, with no fresh dump. Test on `aws.dhwanijain.me` first (guide §10), then cut over. Keep the running Ubuntu **24.04** / 16 GB instance instead of the guide's 26.04 / 20 GB (owner: "move forward"). PGDG supplies `pg_restore` 18 |
| RDS access | The owner attached an RDS policy to `isba-student` from the root account. The owner pays for this account |

**Deadline:** Railway's trial ends around **2026-11-07**. Finish Task 8 by **2026-11-05** so the one-day rollback window in Task 9 fits before it ends. Once the trial lapses the Railway rollback is gone, and the backups in `~/backups/` are the only fallback.

## Starting State (inspected 2026-11-03)

| Fact | Value |
|---|---|
| Live site | `https://dhwanijain.me` on Railway project `desirable-achievement`, web service deploys from GitHub `main` |
| Live database | Railway Postgres **18.6**, database `railway`, user `postgres`, private only (no TCP proxy). Reached from the laptop with `railway connect Postgres --tunnel-only` |
| Latest backup | `~/backups/career-railway-20261029T2203Z.dump` (custom format, 40757 bytes, sha256 `7440740f…d7d6d7b`, mode 600). Restore test passed on 2026-10-29 |
| DNS (Cloudflare) | `dhwanijain.me` CNAME → Railway (DNS only, flattened to `69.46.46.53`). `www` proxied with a redirect rule to the root. MX → Zoho. **Only the apex record changes in this plan** |
| Repo | `main` clean at `89b52d3`. 48 tests pass. `app/schema.sql` uses `IF NOT EXISTS` throughout, so `scripts.init_db` is re-runnable |
| AWS account | `<AWS_ACCOUNT_ID>`, IAM user `isba-student`, CLI profile `isba-4775`, region `us-east-1`. Nothing created yet |
| Laptop tools | AWS CLI 2.39.3, Railway CLI, Docker (for `postgres:18` client tools), `uv`. No local `psql`/`pg_dump` |

### What `isba-student` can do (probed 2026-11-03 with `--dry-run`)

| Action | Result | Consequence for this plan |
|---|---|---|
| `ec2:RunInstances` | Only `t3.micro`/`t3.small`. `t2`, `t3a`, `t4g` denied | x86 (amd64) Ubuntu AMI |
| `ec2:CreateKeyPair` / `ImportKeyPair` | Denied / allowed | Generate the key on the laptop, import the public half |
| `ec2:CreateSubnet` | Denied | Default VPC `vpc-0c9f2991783380d88`. All its subnets are public, so the database stays private through `--no-publicly-accessible` and its security group |
| `ec2:CreateSecurityGroup`, `AllocateAddress` | Allowed | — |
| RDS | Granted by the owner on 2026-11-03. `DescribeDBInstances` works. `CreateDBInstance` is untested: Task 3 finds out | — |
| IAM, SSM, Secrets Manager, CloudWatch Logs, Budgets, Cost Explorer | Denied | No instance role, so SSH only. No RDS-managed password, since that lives in Secrets Manager. Logs come from `journalctl`. Billing is visible only from root |

## Global Constraints

- **AWS CLI:** every command uses `AWS_PROFILE=isba-4775 AWS_REGION=us-east-1`. Run multi-line blocks with `bash`, not zsh: zsh does not word-split variables. If a command fails with `ExpiredToken`, the owner re-runs `! aws login --profile isba-4775`. The owner chose CLI commands so each one can be recorded as evidence, so this plan doesn't use the AWS MCP tools to make changes.
- **No AWS resource is created, changed or deleted without the owner's go-ahead in that session.** Each task that does this starts with an **Approval gate**. Where AWS supports `--dry-run`, run it first.
- **Placement:** EC2 and RDS both in `us-east-1a` (subnet `subnet-03ebff170ff661abb`). This avoids cross-AZ latency and data charges. The RDS subnet group also needs `us-east-1b` (`subnet-0b1336c1e80fb0e89`), because RDS requires two AZs even for Single-AZ.
- **Names and tags:** `career-web` (instance), `career-web-sg`, `career-db-sg`, `career-db` (RDS), `career-db-subnets`, `career-aws` (key pair, SSH alias). Every resource is tagged `Project=career-platform`, so teardown can find them all.
- **Secrets never go into git, this plan, or chat output.** That covers the RDS master password, the app role's password, and any `DATABASE_URL`.
  - Passwords are generated with `openssl rand -hex 24` (hex, so URL-safe).
  - They're stored on the laptop under `~/.config/career-platform/aws/` (dir 700, files 600). The app's URL lives only in `/home/ubuntu/career-platform/.env` (mode 600) on the instance.
  - Passwords travel to the server over SSH **stdin**, never as command-line arguments.
  - `tests/test_deploy_files.py` fails if a credentialed URL or an RDS hostname appears in `deploy/aws/`.
- **Non-secret IDs** (security group IDs, instance ID, allocation ID, Elastic IP, RDS endpoint) go in `~/.config/career-platform/aws/ids.env` on the laptop, so later blocks can `source` it. They're redacted as `<PLACEHOLDERS>` in this public repo, following the Azure plan's convention.
- **Database roles:**
  - The master user `postgres` is for administration only, and its password never leaves the laptop except over SSH stdin.
  - The app connects as `career_app`, which owns database `career` and nothing else. `scripts.init_db` runs as `career_app`, so it can apply the schema.
- **TLS to RDS:** `sslmode=verify-full` with `sslrootcert=/etc/ssl/rds/global-bundle.pem`. RDS for PostgreSQL 15+ already rejects unencrypted connections (`rds.force_ssl=1`). `verify-full` also proves the server is really RDS.
- **Dependency versions are frozen** at the values in `requirements.txt`. Python 3.13 comes from `.python-version`, provisioned by `uv` (Ubuntu 24.04 ships 3.12).
- **Railway is gone** (the trial ended around 2026-11-07). There's no rollback target, so the site comes back only when AWS is live. The Oct 29 dump is the data of record (the owner confirmed no edits since).
- **Deviation log:** the guide asks for `migration-notes.md` at the repo root, which records every deviation from this plan. This plan's Execution Log keeps the step-by-step record.
- **Cloudflare changes are made by the owner** in the dashboard. The agent verifies them with `dig` and `curl`.
- **Backups:** RDS keeps 1 day of automated backups (the Free plan refused 7). Keep the `pg_dump` files in `~/backups/` as the longer history.
- **Keep this plan current:** tick checkboxes, fix stale facts, and append an Execution Log entry when each task completes.

## Review Focus

These are the failure modes most likely to hurt a real visitor that no main-path step exercises. Each has its check folded into the owning task.

1. **The page returns 200 but the database is unreachable.** For example, the security group is wrong, the `.env` is wrong, or TLS fails. `/health` never touches the database. `deploy/aws/deploy.sh` therefore also requires `/` to return 200, since it returns 503 when the DB is down. Task 7 checks for a known role and that the "Showing saved content" banner is absent.
2. **A database outage must degrade, not crash, and recover without a restart.** Task 7 revokes the `5432` rule to simulate an outage: the expected result is 503 with the profile visible. Restoring the rule must bring back a 200 with projects on the next request.
3. **`pg_restore` older than the dump.** Ubuntu 24.04's client is 16, and it can't read a dump made by `pg_dump` 18. Task 5 installs `postgresql-client-18` from PGDG and checks `pg_restore --version` before any restore.
4. **An unencrypted or unverified connection to RDS.** Task 5 proves `sslmode=disable` is rejected and `verify-full` succeeds. The app's `DATABASE_URL` uses `verify-full`.
5. **Stopping the instance changes its address or loses the service.** Task 7 runs a full **stop/start**, not just a reboot. It checks that the Elastic IP is unchanged and the site comes back with no manual step. Task 8 confirms `certbot renew --dry-run` works.

---

## File Structure

| File | Responsibility |
|---|---|
| `deploy/aws/career-platform.service` (create) | systemd unit: run Uvicorn as `ubuntu` on `127.0.0.1:8000`, 2 workers, restart on failure, start at boot |
| `deploy/aws/nginx-career-platform.conf` (create) | Nginx site, before Certbot: port 80 for `dhwanijain.me`, proxy to `127.0.0.1:8000`, forward `Host` and `X-Forwarded-*` |
| `deploy/aws/deploy.sh` (create) | Run on the server: pull a ref, `uv sync --frozen --no-dev`, `scripts.init_db`, restart, then require `/health` **and** `/` to return 200. Replaces Railway's build, `preDeployCommand` and health check |
| `tests/test_deploy_files.py` (create) | Pins the properties above and the no-secrets rule |
| `scripts/init_db.py` (modify docstring) | Say it runs on every deploy, not only on Railway |
| `.env.example` (modify comment) | Document the EC2/RDS `DATABASE_URL` shape, with placeholders |
| `railway.json` | Unchanged until Task 9, then deleted |

---

## Task 0: Preflight (no changes)

**Files:** none

- [ ] **Step 1: Confirm branch and tests**

Run: `git branch --show-current && git status --short && uv run pytest -q 2>&1 | tail -1`
Expected: `aws-ec2-rds-migration`, clean tree, `48 passed`. The test Postgres must be running: `docker start career-pg-test`.

- [ ] **Step 2: Confirm AWS identity and region**

Run: `aws sts get-caller-identity --profile isba-4775 --query Arn --output text && aws configure get region --profile isba-4775`
Expected: `arn:aws:iam::<AWS_ACCOUNT_ID>:user/isba-student`, `us-east-1`

- [ ] **Step 3: Confirm Railway only deploys from `main`**

Run: `railway status` and, in the Railway dashboard, web service → Settings → Source: check that the branch is `main` and "PR environments" is off.
Expected: branch `main`. If PR or branch deploys are on, stop and tell the owner before pushing this branch.

- [ ] **Step 4 (owner, root login): Set a cost alert**

`isba-student` can't see billing. The owner signs in as root, opens Billing → Budgets → Create budget → "Monthly cost budget", sets **$30** (just above the expected total below, so it only fires on a surprise), and enters their email. Record "budget set" in the Execution Log.

Expected monthly cost if nothing is free tier (on-demand, us-east-1, from AWS's public price list files on 2026-11-03, 730 hours a month):

| Item | ≈ / month |
|---|---|
| EC2 `t3.micro` | $7.59 |
| EBS gp3 16 GB | $1.28 |
| Elastic IP (public IPv4, billed even when unattached) | $3.65 |
| RDS `db.t4g.micro` Single-AZ | $11.68 |
| RDS gp3 20 GB | $2.30 |
| RDS backups ≤ 20 GB | $0 |
| Data transfer (under the free 100 GB out; EC2 to RDS in the same AZ is free) | $0 |
| **Total** | **$26.50** |

---

## Task 1: Deploy files, tested (repo only, no AWS)

**Files:**
- Create: `deploy/aws/career-platform.service`, `deploy/aws/nginx-career-platform.conf`, `deploy/aws/deploy.sh`, `tests/test_deploy_files.py`
- Modify: `scripts/init_db.py:1` (docstring), `.env.example:4-6` (comment)

**Interfaces:**
- Produces: a unit named `career-platform` (used in `deploy.sh`, Tasks 7–9), app root `/home/ubuntu/career-platform`, Uvicorn on `127.0.0.1:8000`, Nginx site file `nginx-career-platform.conf` (installed as `/etc/nginx/sites-available/career-platform` in Task 7), and `deploy/aws/deploy.sh [git-ref]`, which exits 0 only when `/health` and `/` both return 200.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_deploy_files.py`:

```python
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy" / "aws"
UNIT = DEPLOY / "career-platform.service"
NGINX = DEPLOY / "nginx-career-platform.conf"
DEPLOY_SH = DEPLOY / "deploy.sh"


def _exec_start() -> str:
    return next(l for l in UNIT.read_text().splitlines() if l.startswith("ExecStart="))


def test_service_binds_loopback_only():
    # Nginx is the only thing that should reach Uvicorn. Uvicorn's
    # X-Forwarded-Proto trust (FORWARDED_ALLOW_IPS) defaults to 127.0.0.1.
    assert "--host 127.0.0.1" in _exec_start()
    assert "0.0.0.0" not in _exec_start()


def test_service_runs_unprivileged_from_the_app_root():
    unit = UNIT.read_text()
    assert "User=ubuntu" in unit
    # app/main.py mounts "app/static" and "app/templates" by relative path.
    assert "WorkingDirectory=/home/ubuntu/career-platform" in unit
    assert "ExecStart=/home/ubuntu/career-platform/.venv/bin/uvicorn app.main:app" in unit


def test_service_restarts_and_starts_at_boot():
    unit = UNIT.read_text()
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_nginx_proxies_to_the_port_the_service_listens_on():
    port = re.search(r"--port (\d+)", _exec_start()).group(1)
    assert f"proxy_pass http://127.0.0.1:{port};" in NGINX.read_text()


def test_nginx_forwards_host_and_scheme():
    conf = NGINX.read_text()
    assert "server_name dhwanijain.me;" in conf
    assert "proxy_set_header Host $host;" in conf
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in conf
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in conf


def test_deploy_script_applies_schema_before_restart():
    s = DEPLOY_SH.read_text()
    assert s.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in s
    assert s.index("uv sync --frozen --no-dev") < s.index("-m scripts.init_db") < s.index(
        "systemctl restart career-platform"
    )


def test_deploy_script_requires_the_database_backed_page():
    # /health never touches the database; / returns 503 when it is down.
    s = DEPLOY_SH.read_text()
    assert "http://127.0.0.1:8000/health" in s
    assert "http://127.0.0.1:8000/" in s.replace("http://127.0.0.1:8000/health", "")


def test_deploy_script_is_executable():
    assert os.access(DEPLOY_SH, os.X_OK)


@pytest.mark.parametrize("path", [UNIT, NGINX, DEPLOY_SH], ids=lambda p: p.name)
def test_no_secrets_in_deploy_files(path):
    text = path.read_text()
    assert not re.search(r"postgres(?:ql)?://[^\s/:@]+:[^\s/@]+@", text), "credentialed URL"
    assert "rds.amazonaws.com" not in text, "RDS endpoint belongs in .env, not git"
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/test_deploy_files.py -q`
Expected: every test fails or errors with `FileNotFoundError` (no `deploy/aws/` yet).

- [ ] **Step 3: Write the systemd unit**

Create `deploy/aws/career-platform.service`:

```ini
[Unit]
Description=Career Platform (FastAPI behind Nginx)
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/career-platform
ExecStart=/home/ubuntu/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

No `Environment=` lines: `app/config.py` loads `/home/ubuntu/career-platform/.env` itself.

- [ ] **Step 4: Write the Nginx site**

Create `deploy/aws/nginx-career-platform.conf`:

```nginx
# Before Certbot. `certbot --nginx -d dhwanijain.me` (Task 8) edits the installed
# copy to add the 443 server and the http -> https redirect.
server {
    listen 80;
    server_name dhwanijain.me;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`www` is left out on purpose: Cloudflare answers it and redirects to the root, so it never reaches this server.

- [ ] **Step 5: Write the deploy script**

Create `deploy/aws/deploy.sh`:

```bash
#!/usr/bin/env bash
# Deploy on the EC2 instance. Replaces Railway's build, preDeployCommand and
# health check. Usage, on the server:  ~/career-platform/deploy/aws/deploy.sh [git-ref]
set -euo pipefail
cd "$(dirname "$0")/../.."

ref="${1:-$(git rev-parse --abbrev-ref HEAD)}"
git fetch --prune origin
git checkout "$ref"
git pull --ff-only origin "$ref"

~/.local/bin/uv sync --frozen --no-dev
.venv/bin/python -m scripts.init_db
sudo systemctl restart career-platform

# /health proves the process is up; / proves it can read the database (503 if not).
for _ in $(seq 1 20); do
  health=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health || true)
  home=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ || true)
  if [ "$health" = 200 ] && [ "$home" = 200 ]; then
    echo "Deployed $(git rev-parse --short HEAD): /health 200, / 200"
    exit 0
  fi
  sleep 1
done
echo "Deploy check failed: /health $health, / $home. Recent logs:" >&2
sudo journalctl -u career-platform -n 30 --no-pager >&2
exit 1
```

Run: `chmod +x deploy/aws/deploy.sh`

- [ ] **Step 6: Run the tests and watch them pass**

Run: `uv run pytest tests/test_deploy_files.py -q`
Expected: `13 passed` (as built on 2026-11-08: the Nginx site also names `aws.dhwanijain.me` for the guide's test subdomain, and a test pins that `deploy.sh` never seeds)

- [ ] **Step 7: Update the two comments**

`scripts/init_db.py` line 1, replace the docstring's first line with:

```python
"""Create (or re-apply) the Career Platform schema. Runs on every deploy: Railway's
preDeployCommand, and deploy/aws/deploy.sh on EC2.
```

`.env.example`, replace the comment above `DATABASE_URL` with:

```
# Local Docker Postgres (see README). On Railway this is set to the
# Postgres service's private DATABASE_URL by reference, never by value.
# On EC2 it is the career_app role on RDS, verified TLS, in a mode-600 .env:
#   postgresql://career_app:<PASSWORD>@<RDS_ENDPOINT>:5432/career?sslmode=verify-full&sslrootcert=/etc/ssl/rds/global-bundle.pem
```

- [ ] **Step 8: Full suite, commit, push the branch**

Run: `uv run pytest -q 2>&1 | tail -1`, expected `61 passed`.

```bash
git add deploy/aws tests/test_deploy_files.py scripts/init_db.py .env.example docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md
git commit -m "feat: add tested EC2 deploy files and the AWS migration plan"
git push -u origin aws-ec2-rds-migration
```

Expected: the push creates the branch on GitHub, and **no** new Railway deployment appears (check `railway status` or the dashboard's Deployments tab).

---

## Task 2: SSH key and security groups (AWS create)

**Approval gate:** ask the owner before Step 2. This creates a key pair and two security groups. All of them are free.

**Files:** none in the repo. On the laptop: `~/.ssh/isba4775_aws{,.pub}`, `~/.config/career-platform/aws/ids.env`

**Interfaces:**
- Produces: `WEB_SG`, `DB_SG` in `ids.env`, and key pair `career-aws`.

- [ ] **Step 1: Make the key and the state directory (laptop only)**

```bash
bash <<'EOF'
set -euo pipefail
install -d -m 700 ~/.config/career-platform/aws
touch ~/.config/career-platform/aws/ids.env && chmod 600 ~/.config/career-platform/aws/ids.env
[ -f ~/.ssh/isba4775_aws ] || ssh-keygen -t ed25519 -f ~/.ssh/isba4775_aws -N '' -C career-aws
ssh-keygen -lf ~/.ssh/isba4775_aws.pub
EOF
```

Expected: an `ED25519` fingerprint. The private key is mode 600.

- [ ] **Step 2: Import the public key, create both groups**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
IDS=~/.config/career-platform/aws/ids.env
VPC=vpc-0c9f2991783380d88
MYIP=$(curl -4 -s https://checkip.amazonaws.com)
TAG='Tags=[{Key=Project,Value=career-platform}]'

aws ec2 import-key-pair --key-name career-aws --public-key-material fileb://$HOME/.ssh/isba4775_aws.pub \
  --tag-specifications "ResourceType=key-pair,$TAG" --query KeyFingerprint --output text

WEB_SG=$(aws ec2 create-security-group --vpc-id $VPC --group-name career-web-sg \
  --description "career-platform web: SSH from laptop, HTTP/HTTPS from anyone" \
  --tag-specifications "ResourceType=security-group,$TAG" --query GroupId --output text)
echo "WEB_SG=$WEB_SG" >> "$IDS"
aws ec2 authorize-security-group-ingress --group-id $WEB_SG --ip-permissions \
  "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=$MYIP/32,Description=laptop}]" \
  "IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges=[{CidrIp=0.0.0.0/0}]" \
  "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0}]" >/dev/null

DB_SG=$(aws ec2 create-security-group --vpc-id $VPC --group-name career-db-sg \
  --description "career-platform RDS: Postgres from career-web-sg only" \
  --tag-specifications "ResourceType=security-group,$TAG" --query GroupId --output text)
echo "DB_SG=$DB_SG" >> "$IDS"
aws ec2 authorize-security-group-ingress --group-id $DB_SG --ip-permissions \
  "IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$WEB_SG,Description=career-web}]" >/dev/null
EOF
```

If a create fails only because tagging is denied (`ec2:CreateTags`), remove its `--tag-specifications`, log the deviation, and tag from the root login later. Task 10's leftovers check depends on the tags.

- [ ] **Step 3: Verify the rules**

```bash
AWS_PROFILE=isba-4775 aws ec2 describe-security-groups --filters Name=tag:Project,Values=career-platform \
  --query 'SecurityGroups[].{name:GroupName,in:IpPermissions[].{port:FromPort,cidr:IpRanges[].CidrIp,sg:UserIdGroupPairs[].GroupId}}' --output json
```

Expected:
- `career-web-sg` allows 22 from exactly one `/32`, and 80 and 443 from `0.0.0.0/0`.
- `career-db-sg` allows 5432 from `career-web-sg`'s ID only, with **no** CIDR.

**Note for later sessions:** the laptop's IP changes between home and campus. If SSH times out, re-point the rule:

```bash
bash <<'EOF'
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1; source ~/.config/career-platform/aws/ids.env
OLD=$(aws ec2 describe-security-groups --group-ids $WEB_SG --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`].IpRanges[0].CidrIp' --output text)
aws ec2 revoke-security-group-ingress --group-id $WEB_SG --protocol tcp --port 22 --cidr "$OLD"
aws ec2 authorize-security-group-ingress --group-id $WEB_SG --protocol tcp --port 22 --cidr "$(curl -4 -s https://checkip.amazonaws.com)/32"
EOF
```

---

## Task 3: RDS PostgreSQL, Single-AZ (AWS create, billed)

**Approval gate:** ask the owner before Step 2. RDS bills from creation (≈ $14/month with storage).

**Files:** on the laptop, `~/.config/career-platform/aws/rds-master.pw`

**Interfaces:**
- Consumes: `DB_SG`
- Produces: `RDS_ENDPOINT` in `ids.env`, and master user `postgres` whose password is in `rds-master.pw`.

- [ ] **Step 1: Generate the master password (laptop only)**

```bash
bash -c 'umask 077; f=~/.config/career-platform/aws/rds-master.pw; [ -f $f ] || openssl rand -hex 24 > $f; ls -l $f'
```

Expected: `-rw-------`, 49 bytes. Never `cat` it in chat.

- [ ] **Step 2: Subnet group and instance**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
source ~/.config/career-platform/aws/ids.env
aws rds create-db-subnet-group --db-subnet-group-name career-db-subnets \
  --db-subnet-group-description "career-platform: default VPC, us-east-1a + 1b" \
  --subnet-ids subnet-03ebff170ff661abb subnet-0b1336c1e80fb0e89 \
  --tags Key=Project,Value=career-platform --query 'DBSubnetGroup.SubnetGroupStatus' --output text

aws rds create-db-instance \
  --db-instance-identifier career-db \
  --engine postgres --engine-version 18.6 \
  --db-instance-class db.t4g.micro \
  --allocated-storage 20 --storage-type gp3 --storage-encrypted \
  --no-multi-az --availability-zone us-east-1a \
  --db-subnet-group-name career-db-subnets --vpc-security-group-ids "$DB_SG" \
  --no-publicly-accessible \
  --master-username postgres --master-user-password "$(cat ~/.config/career-platform/aws/rds-master.pw)" \
  --backup-retention-period 1 --deletion-protection --copy-tags-to-snapshot \
  --auto-minor-version-upgrade \
  --tags Key=Project,Value=career-platform \
  --query 'DBInstance.DBInstanceStatus' --output text
EOF
```

Expected: `Complete`, then `creating`.
- If `db.t4g.micro` is denied, re-run with `--db-instance-class db.t3.micro`.
- If `CreateDBInstance` itself is denied, stop and show the owner the exact error, since the RDS policy needs widening.
- Log any deviation.

- [ ] **Step 3: Wait (≈ 10–15 min), then verify the settings**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
aws rds wait db-instance-available --db-instance-identifier career-db
aws rds describe-db-instances --db-instance-identifier career-db --query 'DBInstances[0].{v:EngineVersion,cls:DBInstanceClass,az:AvailabilityZone,multiAZ:MultiAZ,public:PubliclyAccessible,enc:StorageEncrypted,backups:BackupRetentionPeriod,delProt:DeletionProtection,sg:VpcSecurityGroups[].VpcSecurityGroupId}' --output json
EP=$(aws rds describe-db-instances --db-instance-identifier career-db --query 'DBInstances[0].Endpoint.Address' --output text)
printf 'RDS_ENDPOINT=%s\n' "$EP" >> ~/.config/career-platform/aws/ids.env
EOF
```

Expected: `v 18.6`, `az us-east-1a`, `multiAZ false`, `public false`, `enc true`, `backups 1`, `delProt true`, `sg` = `DB_SG` only.

---

## Task 4: EC2 instance and Elastic IP (AWS create, billed)

**Approval gate:** ask the owner before Step 2 (≈ $12.50/month including the IP).

**Files:** `~/.ssh/config` (append `career-aws`)

**Interfaces:**
- Consumes: `WEB_SG`, key pair `career-aws`
- Produces: `INSTANCE_ID`, `EIP_ALLOC`, `EIP` in `ids.env`, and SSH alias `career-aws` (user `ubuntu`).

- [ ] **Step 1: Find the AMI and dry-run**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
source ~/.config/career-platform/aws/ids.env
AMI=$(aws ec2 describe-images --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*' Name=state,Values=available \
  --query 'sort_by(Images,&CreationDate)[-1].[ImageId,Name]' --output text)
echo "$AMI"
aws ec2 run-instances --dry-run --image-id ${AMI%%[[:space:]]*} --instance-type t3.micro --key-name career-aws \
  --security-group-ids $WEB_SG --subnet-id subnet-03ebff170ff661abb \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=16,VolumeType=gp3,Encrypted=true}' 2>&1 | grep -o 'DryRunOperation\|UnauthorizedOperation.*' | head -1
EOF
```

Expected: an `ami-…` from Canonical (owner `099720109477`) named `…noble-24.04-amd64…`, then `DryRunOperation`. If `Encrypted=true` causes `UnauthorizedOperation`, the policy is missing KMS rights for EBS: drop `Encrypted=true` and log the deviation.

- [ ] **Step 2: Launch, attach an Elastic IP**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
IDS=~/.config/career-platform/aws/ids.env; source "$IDS"
AMI=$(aws ec2 describe-images --owners 099720109477 \
  --filters 'Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*' Name=state,Values=available \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
INSTANCE_ID=$(aws ec2 run-instances --image-id $AMI --instance-type t3.micro --key-name career-aws \
  --security-group-ids $WEB_SG --subnet-id subnet-03ebff170ff661abb \
  --credit-specification CpuCredits=standard \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=16,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=career-web},{Key=Project,Value=career-platform}]' \
                       'ResourceType=volume,Tags=[{Key=Project,Value=career-platform}]' \
  --query 'Instances[0].InstanceId' --output text)
echo "INSTANCE_ID=$INSTANCE_ID" >> "$IDS"
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

EIP_ALLOC=$(aws ec2 allocate-address --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=career-web},{Key=Project,Value=career-platform}]' \
  --query AllocationId --output text)
echo "EIP_ALLOC=$EIP_ALLOC" >> "$IDS"
aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $EIP_ALLOC >/dev/null
EIP=$(aws ec2 describe-addresses --allocation-ids $EIP_ALLOC --query 'Addresses[0].PublicIp' --output text)
echo "EIP=$EIP" >> "$IDS"
aws ec2 wait instance-status-ok --instance-ids $INSTANCE_ID
aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].{state:State.Name,type:InstanceType,az:Placement.AvailabilityZone,ip:PublicIpAddress,imds:MetadataOptions.HttpTokens}' --output json
aws ec2 describe-instance-credit-specifications --instance-ids $INSTANCE_ID --query 'InstanceCreditSpecifications[0].CpuCredits' --output text
EOF
```

Expected:
- `running`, `t3.micro`, `us-east-1a`.
- `ip` equals `EIP`.
- `imds` is `required`.
- The last line prints `standard`.

Why each setting:
- `CpuCredits=standard` stops `t3` from billing for sustained CPU above its baseline. The default is `unlimited`.
- `HttpTokens=required` turns on IMDSv2, which blocks a class of SSRF credential theft.

- [ ] **Step 3: Verify the host key, then add the SSH alias**

Get the instance's own host-key fingerprints from its boot log:

```bash
bash -c 'source ~/.config/career-platform/aws/ids.env; AWS_PROFILE=isba-4775 AWS_REGION=us-east-1 aws ec2 get-console-output --instance-id $INSTANCE_ID --latest --output text | sed -n "/BEGIN SSH HOST KEY FINGERPRINTS/,/END SSH HOST KEY FINGERPRINTS/p"'
```

**Trust decision: show the ED25519 fingerprint to the owner and ask before connecting.** If the console output is empty or denied, say so and let the owner decide whether to accept on first use.

Append to `~/.ssh/config` with the real IP from `ids.env`:

```
Host career-aws
  HostName <EIP>
  User ubuntu
  IdentityFile ~/.ssh/isba4775_aws
  IdentitiesOnly yes
```

Run: `ssh career-aws 'lsb_release -ds; uname -m; nproc; free -m | awk "/Mem/{print \$2\" MB\"}"'`, and compare the fingerprint ssh prints with the console output.
Expected: `Ubuntu 24.04.x LTS`, `x86_64`, `2`, about `900 MB`.

---

## Task 5: Server software, code, and a verified TLS path to RDS

**Files:** on the server only

**Interfaces:**
- Consumes: SSH alias `career-aws`, `RDS_ENDPOINT`, `rds-master.pw`
- Produces: `/home/ubuntu/career-platform` on branch `aws-ec2-rds-migration` with `.venv` (Python 3.13), `/etc/ssl/rds/global-bundle.pem`, and `psql`/`pg_restore` 18.

- [ ] **Step 1: Packages**

```bash
ssh career-aws 'set -e
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get -yq upgrade
sudo DEBIAN_FRONTEND=noninteractive apt-get -yq install git nginx certbot python3-certbot-nginx postgresql-common curl
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo DEBIAN_FRONTEND=noninteractive apt-get -yq install postgresql-client-18
pg_restore --version; psql --version; nginx -v 2>&1; certbot --version
systemctl is-enabled unattended-upgrades'
```

Expected: `pg_restore (PostgreSQL) 18.x` (Review Focus 3), `psql 18.x`, an nginx version, a certbot version, and `enabled`.
Nginx starts serving its default page on port 80 now. That's harmless, and Task 7 replaces it.

- [ ] **Step 2: uv, code, Python environment**

```bash
ssh career-aws 'set -e
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone --branch aws-ec2-rds-migration https://github.com/djain2905/career-platform.git ~/career-platform
cd ~/career-platform && ~/.local/bin/uv sync --frozen --no-dev
.venv/bin/python --version; git log -1 --oneline'
```

Expected: `Python 3.13.x`, and the same commit as `git log -1 --oneline` on the laptop.

- [ ] **Step 3: RDS CA bundle**

```bash
ssh career-aws 'sudo install -d -m 755 /etc/ssl/rds && sudo curl -fsSo /etc/ssl/rds/global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem && grep -c "BEGIN CERTIFICATE" /etc/ssl/rds/global-bundle.pem'
```

Expected: a count above 100.

- [ ] **Step 4: Prove TLS is enforced and verified (Review Focus 4)**

```bash
bash <<'EOF'
source ~/.config/career-platform/aws/ids.env
cat ~/.config/career-platform/aws/rds-master.pw | ssh career-aws "read -r PGPASSWORD; export PGPASSWORD
echo '-- sslmode=disable (must be rejected):'
psql 'host=$RDS_ENDPOINT user=postgres dbname=postgres sslmode=disable connect_timeout=5' -Atc 'select 1' 2>&1 | tail -1
echo '-- sslmode=verify-full:'
psql 'host=$RDS_ENDPOINT user=postgres dbname=postgres sslmode=verify-full sslrootcert=/etc/ssl/rds/global-bundle.pem' -Atc 'select version(); select ssl, version from pg_stat_ssl where pid = pg_backend_pid()'"
EOF
```

Expected:
- The first command fails with `no pg_hba.conf entry … no encryption`.
- The second prints `PostgreSQL 18.6 …` and `t|TLSv1.3` (or `TLSv1.2`).

---

## Task 6: App role, database, rehearsal restore

**Files:** on the laptop, `~/.config/career-platform/aws/career-app.pw`. On the server, `~/career-platform/.env` (mode 600) and `~/backups/` (mode 700).

**Interfaces:**
- Consumes: Task 5's TLS path, `~/backups/career-railway-20261029T2203Z.dump`
- Produces: role `career_app` owning database `career`, restored from the Oct 29 dump, and a `.env` whose `DATABASE_URL` is used by the app and `scripts.init_db`.

- [ ] **Step 1: Create the role and database**

```bash
bash <<'EOF'
set -euo pipefail
umask 077
D=~/.config/career-platform/aws; source $D/ids.env
[ -f $D/career-app.pw ] || openssl rand -hex 24 > $D/career-app.pw
# Line 1 is the master password (consumed by `read`). The rest is SQL that psql reads from stdin.
{ cat $D/rds-master.pw
  printf "CREATE ROLE career_app LOGIN PASSWORD '%s';\n" "$(cat $D/career-app.pw)"
  echo "GRANT career_app TO postgres;"   # PG16+: needed for CREATE DATABASE ... OWNER
  echo "CREATE DATABASE career OWNER career_app;"
  echo "REVOKE ALL ON DATABASE career FROM PUBLIC;"
} | ssh career-aws "read -r PGPASSWORD; export PGPASSWORD
psql 'host=$RDS_ENDPOINT user=postgres dbname=postgres sslmode=verify-full sslrootcert=/etc/ssl/rds/global-bundle.pem' -v ON_ERROR_STOP=1 -q"
echo created
EOF
```

Expected: `created`, with no errors.

- [ ] **Step 2: Write the server's `.env`**

```bash
bash <<'EOF'
set -euo pipefail
D=~/.config/career-platform/aws; source $D/ids.env
# Quoted: later steps source this file, and a bare space or & would break that.
{ echo 'APP_NAME="Career Platform"'
  echo 'APP_ENV="production"'
  echo "DATABASE_URL=\"postgresql://career_app:$(cat $D/career-app.pw)@$RDS_ENDPOINT:5432/career?sslmode=verify-full&sslrootcert=/etc/ssl/rds/global-bundle.pem\""
} | ssh career-aws 'umask 077; cat > ~/career-platform/.env; ls -l ~/career-platform/.env | cut -c1-10'
EOF
```

Expected: `-rw-------`.

- [ ] **Step 3: Copy the Oct 29 dump and restore it**

```bash
bash <<'EOF'
set -euo pipefail
F=career-railway-20261029T2203Z.dump
ssh career-aws 'install -d -m 700 ~/backups'
scp -q ~/backups/$F career-aws:backups/$F
ssh career-aws "set -e; chmod 600 ~/backups/$F; sha256sum ~/backups/$F | cut -c1-16
cd ~/career-platform; set -a; . ./.env; set +a
pg_restore --no-owner --no-acl --exit-on-error --single-transaction -d \"\$DATABASE_URL\" ~/backups/$F
.venv/bin/python -m scripts.init_db"
EOF
```

Expected:
- The hash starts `7440740f34d2892f`.
- `pg_restore` prints nothing.
- `init_db` prints `Schema applied to <host>/career` and `14 tables: …`. This proves `career_app` can run the schema on every deploy.

- [ ] **Step 4: Check the rows match the backup**

```bash
ssh career-aws 'cd ~/career-platform; set -a; . ./.env; set +a
psql "$DATABASE_URL" -At -F" " -c "select t, n from (values
 (1,'"'"'person_profile'"'"',(select count(*) from person_profile)),(2,'"'"'contact_method'"'"',(select count(*) from contact_method)),
 (3,'"'"'role_experience'"'"',(select count(*) from role_experience)),(4,'"'"'experience_highlight'"'"',(select count(*) from experience_highlight)),
 (5,'"'"'project'"'"',(select count(*) from project)),(6,'"'"'project_highlight'"'"',(select count(*) from project_highlight)),
 (7,'"'"'skill'"'"',(select count(*) from skill)),(8,'"'"'skill_proficiency'"'"',(select count(*) from skill_proficiency)),
 (9,'"'"'education_record'"'"',(select count(*) from education_record)),(10,'"'"'certification'"'"',(select count(*) from certification)),
 (11,'"'"'achievement'"'"',(select count(*) from achievement)),(12,'"'"'content_section'"'"',(select count(*) from content_section)),
 (13,'"'"'tag'"'"',(select count(*) from tag)),(14,'"'"'entity_tag'"'"',(select count(*) from entity_tag))) v(i,t,n) order by i"'
```

Expected, the counts verified for this dump on 2026-10-29: `person_profile 1, contact_method 4, role_experience 5, experience_highlight 16, project 3, project_highlight 8, skill 18, skill_proficiency 18, education_record 2, certification 1, achievement 5, content_section 0, tag 0, entity_tag 0`. If any count differs, stop.

---

## Task 7: Run the app, prove it on the IP, prove it survives

**Files:** installs `deploy/aws/career-platform.service` and `deploy/aws/nginx-career-platform.conf` on the server

**Interfaces:**
- Consumes: Task 1's files, Task 6's `.env`
- Produces: a public HTTP site at `http://<EIP>/` (Host `dhwanijain.me`), which Task 8's Certbot run upgrades.

- [ ] **Step 1: Install the unit and the site, then deploy**

```bash
ssh career-aws 'set -e; cd ~/career-platform
sudo cp deploy/aws/career-platform.service /etc/systemd/system/career-platform.service
sudo cp deploy/aws/nginx-career-platform.conf /etc/nginx/sites-available/career-platform
sudo ln -sf /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl daemon-reload && sudo systemctl enable career-platform
deploy/aws/deploy.sh aws-ec2-rds-migration
sudo ss -ltnp | grep -E ":80 |:8000 "'
```

Expected:
- `Deployed <sha>: /health 200, / 200`.
- `ss` shows Nginx on `0.0.0.0:80` and Uvicorn on **`127.0.0.1:8000`** only.

- [ ] **Step 2: Verify real content from the laptop (Review Focus 1)**

```bash
bash -c 'source ~/.config/career-platform/aws/ids.env
P=$(curl -s -H "Host: dhwanijain.me" -w "\n%{http_code}" http://$EIP/)
echo "status: $(echo "$P" | tail -1)"
echo "banner: $(echo "$P" | grep -c "Showing saved content")"
echo "projects-unavailable: $(echo "$P" | grep -c "Projects temporarily unavailable")"
echo "known role: $(echo "$P" | grep -c "HUM Nutrition")"
curl -s -o /dev/null -w "port 8000 from outside: %{http_code}\n" --max-time 5 http://$EIP:8000/ || true'
```

Expected:
- `status: 200`, `banner: 0`, `projects-unavailable: 0`, `known role: 1` or more.
- Port 8000 fails with `000` (timeout): only 22, 80 and 443 are open.

- [ ] **Step 3: Database outage degrades and recovers without a restart (Review Focus 2)**

**Approval gate:** this briefly removes and re-adds the `5432` rule. The site isn't live on AWS yet, so no visitors are affected.

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1; source ~/.config/career-platform/aws/ids.env
RULE="IpProtocol=tcp,FromPort=5432,ToPort=5432,UserIdGroupPairs=[{GroupId=$WEB_SG,Description=career-web}]"
check() { P=$(curl -s -H "Host: dhwanijain.me" -w "\n%{http_code}" http://$EIP/); echo "$1: $(echo "$P"|tail -1), profile=$(echo "$P"|grep -c "Dhwani Jain"), projects-unavailable=$(echo "$P"|grep -c "Projects temporarily unavailable")"; }
aws ec2 revoke-security-group-ingress --group-id $DB_SG --ip-permissions "$RULE" >/dev/null
check "rule removed"
aws ec2 authorize-security-group-ingress --group-id $DB_SG --ip-permissions "$RULE" >/dev/null
sleep 2; check "rule restored"
EOF
```

Expected:
- `rule removed: 503, profile≥1, projects-unavailable=1`. That's within about 3 s, because of `CONNECT_TIMEOUT`.
- `rule restored: 200, profile≥1, projects-unavailable=0`, with no service restart.

This also closes the open `TASKS.md` item "Check live: DB down gives 503…".

- [ ] **Step 4: Stop/start keeps the address and the site (Review Focus 5)**

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1; source ~/.config/career-platform/aws/ids.env
aws ec2 stop-instances --instance-ids $INSTANCE_ID >/dev/null; aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID
aws ec2 start-instances --instance-ids $INSTANCE_ID >/dev/null; aws ec2 wait instance-status-ok --instance-ids $INSTANCE_ID
NOW=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "ip before $EIP after $NOW"
curl -s -o /dev/null -w "home after start: %{http_code}\n" -H "Host: dhwanijain.me" http://$EIP/
EOF
```

Expected: both IPs are equal, and `home after start: 200`, with no SSH or manual step.

---

## Task 8: Test on `aws.dhwanijain.me` (guide §10)

**Approval gate:** the owner approves the DNS change. It adds one record and changes nothing else.

**Files:** `docs/evidence/aws-ec2-rds.md` (create)

- [ ] **Step 1: Add the test record with the Cloudflare CLI**

Find the command with `cf cli search "create a DNS record in a zone"`, then create **A `aws` → `<EIP>`, proxied false (DNS only), TTL auto**. Don't change any other record. Then from the laptop: `dig +short aws.dhwanijain.me A @1.1.1.1`, expected `<EIP>`.

The owner then checks the dashboard: the new record shows the Elastic IP with a grey cloud, and the mail records are unchanged.

- [ ] **Step 2: HTTPS for the test name**

```bash
ssh career-aws 'sudo certbot --nginx -d aws.dhwanijain.me --non-interactive --agree-tos -m <OWNER_EMAIL> --redirect && sudo certbot renew --dry-run 2>&1 | tail -1'
```

Expected: `Successfully deployed certificate` and `Congratulations, all simulated renewals succeeded`.

- [ ] **Step 3: Test like a visitor**

```bash
bash <<'EOF'
H=aws.dhwanijain.me
curl -sI http://$H | sed -n '1p;/^location/Ip'
P=$(curl -s -w "\n%{http_code}" https://$H/); echo "status $(echo "$P"|tail -1) banner $(echo "$P"|grep -c 'Showing saved content') role $(echo "$P"|grep -c 'HUM Nutrition')"
curl -s -o /dev/null -w "privacy %{http_code}\n" https://$H/privacy
curl -s https://$H/health
echo | openssl s_client -connect $H:443 -servername $H 2>/dev/null | openssl x509 -noout -subject -issuer -dates
EOF
```

Expected:
- `http` gives `301` to https.
- `status 200 banner 0 role ≥1`, and `privacy 200`.
- `/health` returns `{"status":"ok",…}`.
- The certificate is `CN = aws.dhwanijain.me`, from Let's Encrypt.

Write the results to `docs/evidence/aws-ec2-rds.md` with the date, what was tested, and what wasn't verified. Redact the EIP as `<EIP>`.

---

## Task 9: Cut over the domain (guide §11)

**Railway's trial ended around 2026-11-07, and the apex has returned 404 from Railway since then (checked 2026-11-08).** There's no fresh dump and no rollback target. The owner confirmed the data hasn't changed since the Oct 29 backup, so what Task 6 restored is current.

**Approval gate:** the owner approves the DNS change.

- [ ] **Step 1: Point the apex at EC2 (Cloudflare CLI)**

Change the apex record from `CNAME → 8udvcs1q.up.railway.app` to **A `dhwanijain.me` → `<EIP>`, DNS only**. Leave `www`, MX, SPF/DKIM TXT and `aws` untouched. The `_railway-verify` TXT can be deleted, since nothing uses it any more. Verify with `dig +short dhwanijain.me A @1.1.1.1` and `@8.8.8.8`: both should return `<EIP>`.

- [ ] **Step 2: Add the apex to the certificate**

```bash
ssh career-aws 'sudo certbot --nginx -d aws.dhwanijain.me -d dhwanijain.me --expand --non-interactive --redirect && sudo certbot renew --dry-run 2>&1 | tail -1'
```

- [ ] **Step 3: Verify like a visitor**

Repeat Task 8 Step 3 with `H=dhwanijain.me`, plus `curl -sI https://www.dhwanijain.me` (expect a 301 to the root) and `dig +short dhwanijain.me MX` (expect Zoho unchanged). Append the results to the evidence file.

- [ ] **Step 4: Merge and redeploy from `main`**

```bash
git rm railway.json
uv run pytest -q 2>&1 | tail -1
git commit -am "chore: retire Railway; site runs on EC2 + RDS"
git switch main && git merge --no-ff aws-ec2-rds-migration && git push
ssh career-aws '~/career-platform/deploy/aws/deploy.sh main'
curl -s -o /dev/null -w "%{http_code}\n" https://dhwanijain.me/
git branch -d aws-ec2-rds-migration && git push origin --delete aws-ec2-rds-migration
```

Expected: `Deployed <sha>: /health 200, / 200`, then `200`.

- [ ] **Step 5: README (guide §12)**

Update the README to cover:
- The chosen architecture and why.
- How the database is backed up and restored: RDS keeps 1 day of backups, plus `pg_dump` files outside AWS.
- The tests that passed on `aws.dhwanijain.me`.
- The cost: $26.50/month, paid from Free plan credits, and the account closes when they run out.
- What's next.
- A **Mermaid** diagram: Cloudflare DNS → Nginx (where TLS ends) → Uvicorn → RDS (inside the VPC, with its backups), SSH as the only admin path, and `www` redirected by Cloudflare.

Drop the Railway-era limitation lines. Tick the live 503 check in `TASKS.md`. Optionally, the owner deletes the Railway project, which has no running services.

---

## Task 10: Teardown runbook (record only, do not run)

For the end of the semester, or if the owner abandons AWS. Run it top to bottom only with the owner's go-ahead. A final snapshot is kept unless the owner says otherwise.

```bash
bash <<'EOF'
set -euo pipefail
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1; source ~/.config/career-platform/aws/ids.env
aws rds modify-db-instance --db-instance-identifier career-db --no-deletion-protection --apply-immediately >/dev/null
aws rds delete-db-instance --db-instance-identifier career-db --final-db-snapshot-identifier career-db-final-$(date -u +%Y%m%d)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID >/dev/null; aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID
aws ec2 release-address --allocation-id $EIP_ALLOC          # an unattached EIP keeps billing
aws rds wait db-instance-deleted --db-instance-identifier career-db
aws rds delete-db-subnet-group --db-subnet-group-name career-db-subnets
aws ec2 delete-security-group --group-id $DB_SG
aws ec2 delete-security-group --group-id $WEB_SG
aws ec2 delete-key-pair --key-name career-aws
# Leftovers check: should print nothing but the final snapshot.
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=career-platform --query 'ResourceTagMappingList[].ResourceARN' --output text
EOF
```

If `get-resources` is denied, check for leftovers from the root login with Tag Editor. The final snapshot costs about $0.095/GB-month. Delete it with `aws rds delete-db-snapshot` once it's no longer needed. The apex DNS record must also be changed or removed, so nothing points at a released IP.

---

## Redacted Values

| Placeholder | How to get it |
|---|---|
| `<EIP>` | `grep EIP= ~/.config/career-platform/aws/ids.env` |
| `<RDS_ENDPOINT>` | `grep RDS_ENDPOINT= ~/.config/career-platform/aws/ids.env` |
| `<AWS_ACCOUNT_ID>` | `aws sts get-caller-identity --profile isba-4775 --query Account --output text` |
| `<OWNER_EMAIL>` | The address the owner chooses for Let's Encrypt account notices. Kept out of this public repo |
| `<PASSWORD>` | Never needed by hand. It's in `~/.config/career-platform/aws/career-app.pw` and the server's `.env` |

---

## Execution Log

Updated as tasks complete. Newest last.

### 2026-11-03: Plan written

Branch `aws-ec2-rds-migration` created from `main` at `89b52d3`. No AWS resources exist. Account limits were probed with `--dry-run` (see Starting State).

### 2026-11-03: Tasks 2, 3 and 4 (security groups, RDS, key, EC2)

- **Task 0:** Step 4 (the budget alert) isn't confirmed by the owner yet. Task 1 (deploy files) hasn't run.
- **Task 2:** `career-web-sg` and `career-db-sg` created. The database group allows 5432 from the web group only, with no CIDR. They were created ahead of Task 3 because RDS needs them.
- **Task 3 deviation:** `--backup-retention-period 7` was refused with `FreeTierRestrictionError`, which is how we learned the account is on the Free plan. The owner chose to stay Free, and 1 day was accepted. Subnet group `career-db-subnets` created.
- **Task 4:** instance `career-web`: `t3.micro`, `us-east-1a`, Ubuntu 24.04 (`ami-0d6dd9e8265d48906`, 20261023), IMDSv2 required, standard credits, encrypted 16 GB gp3. The Elastic IP `<EIP>` is attached and survives stop/start.
- **Host key:** the ED25519 key from `ssh-keyscan` matches the instance's boot log (`SHA256:ZcRO8jUjyhIpnE0jUZD0dREvLmHg0wxizkCDafhH/zQ`). The owner hasn't yet approved trusting it, so the first SSH connection hasn't happened.
- **Task 3 verified:** `career-db` is available: PostgreSQL 18.6, `db.t4g.micro`, `us-east-1a`, Single-AZ, not public, encrypted, 20 GB gp3, 1-day backups, deletion protection on, one security group. The endpoint is saved in `ids.env`.

### 2026-11-08: Tasks 1, 5, 6, 7. COMPLETE

- **Task 1:** deploy files and 13 tests, 61 passing overall. Committed as `cdb0801` on the branch.
- **Before Task 5:**
  - The laptop's IP had changed since 2026-11-03, so the port-22 rule was re-pointed.
  - The RDS master password was rotated, because 6 characters of it were printed to the transcript by mistake during a secrets scan.
  - The fresh `ssh-keyscan` still matched the boot-log ED25519 fingerprint, and that key was pinned.
- **Task 5:** Ubuntu 24.04.5. PGDG `pg_restore`/`psql` **18.6**. Python 3.13.18. 114 RDS CA certificates. `sslmode=disable` was rejected (`no pg_hba.conf entry … no encryption`). `verify-full` connected with `t|TLSv1.3`.
- **Task 6:**
  - `career_app` owns `career`.
  - The server's `.env` is mode 600.
  - The Oct 29 dump (sha256 `7440740f34d2892f…`) restored in **248 ms**.
  - `init_db` ran as `career_app`, 14 tables.
  - Counts are identical to the backup's: 1/4/5/16/3/8/18/18/2/1/5/0/0/0.
  - The spot checks found "Dhwani Jain" and the current role "HUM Nutrition".
- **Task 6 deviation:** the first `scp` in the combined block stopped the script without printing an error. Re-run on its own, it succeeded. The sequence check failed on shell quoting, so it was skipped (`pg_restore` restores sequence values).
- **Task 7:**
  - `Deployed cdb0801: /health 200, / 200`. Uvicorn listens on `127.0.0.1:8000` only.
  - From the laptop: 200, banner 0, projects-unavailable 0, role present, `/privacy` 200, port 8000 `000`.
  - With the 5432 rule revoked: **503** in 4 s, profile visible, "Projects temporarily unavailable". With it restored: **200** with no restart.
  - Stop/start kept the Elastic IP, and the homepage came back 200.

### 2026-11-08: Tasks 8 and 9 (test subdomain, cutover). COMPLETE

- **Task 8:**
  - `A aws.dhwanijain.me → <EIP>`, DNS only, created with `cf dns records create`. A before/after diff showed one record added.
  - Certbot was registered **without an email** (the owner's choice; the guide doesn't require one).
  - Certificate from Let's Encrypt YE2, valid to 2027-02-06.
  - All visitor checks passed (`docs/evidence/aws-ec2-rds.md`).
  - My first static-file check used a wrong path (`/static/css` is a folder). The page's real stylesheet returns 200.
- **Task 9:**
  - The apex `CNAME → Railway` was overwritten as `A → <EIP>`, DNS only, at **2026-11-08 23:14 UTC**. The diff showed only that record changed. `_railway-verify` was left in place.
  - 1.1.1.1 and 8.8.8.8 both answered `<EIP>` within the first check.
  - `certbot --expand` now covers both names (Let's Encrypt YE1, valid to 2027-02-06). `certbot renew --dry-run --no-random-sleep-on-renew` succeeded.
  - `https://dhwanijain.me` returns 200 from nginx with the full page. `www` returns 301 to the root. The MX records are unchanged (Zoho).
- **README (guide §12)** updated with an AWS Mermaid diagram. `docs/evidence/ex07.md` written. The owner adds the two screenshots (`ex07-dns.png`, `ex07-billing.png`).

