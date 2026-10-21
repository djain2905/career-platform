# career-platform

My personal résumé site, and the start of the career platform I'm building this semester.
It shows my profile, experience, projects, skills and education, read from a PostgreSQL
database on every request.

**Live:** <https://dhwanijain.me> (`www.dhwanijain.me` redirects there)
**Runs on:** Railway (FastAPI + Uvicorn, Railway PostgreSQL), DNS on Cloudflare, email on Zoho
Mail, analytics in Google Analytics 4. It ran on an Azure Ubuntu VM until 2026-10-08.
**Project 1 evidence index:** [docs/project-1-submission.md](docs/project-1-submission.md)

| Where it came from | File |
|---|---|
| Application spec | [docs/superpowers/specs/2026-09-15-career-platform-app-spec.md](docs/superpowers/specs/2026-09-15-career-platform-app-spec.md) |
| Implementation plan | [docs/superpowers/plans/2026-09-15-implementation-plan.md](docs/superpowers/plans/2026-09-15-implementation-plan.md) |
| Azure VM migration plan | [docs/superpowers/plans/2026-09-24-azure-vm-migration.md](docs/superpowers/plans/2026-09-24-azure-vm-migration.md) |
| Operating the VM (Nginx, workers, HTTPS, restart) | [docs/superpowers/plans/2026-10-01-operate-the-vm.md](docs/superpowers/plans/2026-10-01-operate-the-vm.md) |
| Railway + PostgreSQL migration plan | [docs/superpowers/plans/2026-10-08-railway-postgres-migration.md](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md) |

---

## What the site does

- `/` renders my profile from PostgreSQL: name, headline, contact links (email, LinkedIn,
  GitHub), experience, projects, skills, education and awards. My phone number is stored but
  never rendered (`PRIVATE_CONTACT_TYPES` in `app/repository.py`).
- `/privacy` explains what Google Analytics collects.
- `/health` returns `{"status":"ok"}` for Railway's health check. It does **not** touch the
  database (see [Limitations](#limitations)).

**When the database is unavailable** the page still shows my profile from the last saved copy,
with a "Showing saved content" note. The Projects section says **"Projects temporarily
unavailable"** and the response is **HTTP 503**. Saved projects are never shown in place of a
failed query. The next request after the database comes back returns 200 with the projects; no
restart is needed, because every request tries the database first. **An empty project table**
returns 200 with "No projects published yet." This behavior is commit `c4e3154`, pushed
2026-10-21. **It was not yet live at submission:** Railway's builds were down in every region that
day (Railway status: "Railway Platform Outage — Major Outage"), so the live site still runs the
previous deployment, which serves saved projects with a 200. Tested in `tests/test_pages.py` and by
stopping the database on purpose ([final checks §6](docs/evidence/project-1-final-checks.md#6-database-failure-empty-table-and-recovery-local-after-the-fix)).

---

## Architecture

The request path, drawn for the midterm question, is in
[docs/diagrams/request-path.png](docs/diagrams/request-path.png).

### Railway (current)

```mermaid
flowchart LR
  subgraph Visitor["Visitor's device"]
    BR["Browser"]
  end
  subgraph CF["Cloudflare"]
    DNS["Authoritative DNS<br/>@ CNAME → Railway (DNS only)<br/>MX/SPF/DKIM/DMARC for Zoho"]
    PX["Proxy for www<br/>301 → https://dhwanijain.me/"]
  end
  subgraph RW["Railway"]
    EDGE["Edge<br/>:80 → 301, :443<br/>TLS ends here"]
    APP["Container<br/>Uvicorn, 2 workers, on $PORT<br/>FastAPI app"]
    PG[("PostgreSQL<br/>:5432, private network")]
  end
  subgraph G["Google"]
    GTM["googletagmanager.com<br/>gtag.js"]
    GA["GA4 property<br/>G-V64QT2T9EG"]
  end
  subgraph Z["Zoho Mail"]
    ZMX["mx.zoho.com<br/>SMTP :25 in"]
    ZBOX["Mailbox + webmail<br/>HTTPS"]
    ZOUT["Zoho outbound SMTP<br/>signs DKIM"]
  end
  EXT["Outside mail server<br/>e.g. LMU Outlook"]
  DEV["My laptop"] -- "git push (HTTPS)" --> GH["GitHub repo"]
  GH -. "auto-deploy on push to main" .-> APP

  BR -- "DNS query, UDP 53<br/>(via my resolver)" --> DNS
  BR -- "HTTPS :443" --> EDGE
  BR -- "HTTPS :443 (www only)" --> PX
  EDGE -- "plain HTTP, $PORT, private" --> APP
  APP -- "SQL over TCP 5432<br/>private DATABASE_URL" --> PG
  BR -- "HTTPS: load gtag.js" --> GTM
  BR -- "HTTPS: page_view, click" --> GA
  EXT -- "MX lookup, then SMTP :25" --> ZMX --> ZBOX
  ZBOX --> ZOUT -- "SMTP :25 to recipient's MX<br/>recipient checks SPF/DKIM/DMARC in DNS" --> EXT
```

### Azure (2026-09-29 → 2026-10-08, now deleted)

```mermaid
flowchart LR
  BR["Browser"] -- "DNS: @ A 4.155.216.147<br/>(Cloudflare, DNS only)" --> NSG
  LAP["My laptop"] -- "SSH :22<br/>key only, my IP /32 only" --> NSG
  subgraph AZ["Azure westus2, rg-career-platform"]
    NSG["NSG<br/>allow 22 (my IP), 80, 443<br/>8000 not allowed"]
    PIP["Public IP 4.155.216.147<br/>static, held by Azure"]
    subgraph VM["VM vm-career-platform, Ubuntu 24.04, private IP 172.16.0.4"]
      NGX["Nginx<br/>:80 → 301, :443<br/>TLS ends here (Certbot)"]
      UV["Uvicorn, 2 workers<br/>127.0.0.1:8000, systemd"]
      DB[("SQLite file<br/>data/resume.db")]
    end
  end
  NSG --> PIP --> NGX
  NGX -- "plain HTTP over loopback" --> UV
  UV -- "file read, no network" --> DB
```

**What made the Azure site survive a restart** (tested 2026-10-08: both services active 9 seconds
after boot, nobody logged in, see the
[operate-the-vm execution log](docs/superpowers/plans/2026-10-01-operate-the-vm.md#2026-10-08--task-5-restart-test--complete)):
`systemctl enable` for both `career-platform.service` (Uvicorn) and `nginx`, so systemd starts
them at boot rather than me; `Restart=on-failure` in the app's unit; the app bound to
`127.0.0.1:8000`, which exists on every boot; the database being a file on the VM's own disk,
so nothing remote had to come up first; Certbot's certificate and Nginx config stored on disk;
and a **static** public IP, so DNS stayed correct across restarts. SSH needed the NSG rule to
match my laptop's current IP, which changes between networks (ex03, failure 6).

Email and analytics didn't change with the host. Zoho (set up 2026-10-13) and GA4 (installed
2026-10-15) were both added after the move to Railway, so they never ran against the Azure VM.

---

## Set up and update

### Run locally

    docker run -d --name career-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=career_test -p 54329:5432 postgres:17
    docker exec career-pg-test createdb -U postgres career_dev
    export DATABASE_URL=postgresql://postgres:test@localhost:54329/career_dev
    uv run python -m scripts.init_db
    uv run python -m scripts.seed_resume
    uv run uvicorn app.main:app --reload

`.env.example` lists the variables the app reads; an exported variable wins over `.env`.

### Test

    docker start career-pg-test
    uv run pytest

Tests wipe the database at `TEST_DATABASE_URL` (default: the local container above) and refuse
to run against any non-local host.

### Configuration

| Variable | Local | Railway | Azure (retired) |
|---|---|---|---|
| `DATABASE_URL` | local Docker Postgres | reference to the Postgres service's **private** URL, set in Railway variables, never in git | the SQLite file path |
| `PORT` | — (uvicorn default) | set by Railway; `railway.json` starts Uvicorn on it | — (systemd unit used 8000) |
| `RAILWAY_DATABASE_URL` | Railway's **public** Postgres URL, in my local `.env` only, used for the one-time data copy | — | — |
| `APP_ENV`, `APP_NAME` | `.env` | not set; the code's defaults apply | `.env` on the VM |

Secrets live only in `.env` (gitignored) and Railway's variables.

### Deploy an update

1. Change the code and run `uv run pytest`.
2. Run it locally and check the page in a browser.
3. Read the diff (`git diff`), then commit and push to `main`.
4. Railway is connected to the GitHub repo `djain2905/career-platform` and deploys every push to
   `main` (confirmed 2026-10-21 with `railway status`). It builds with Railpack from `pyproject.toml`/`uv.lock`, runs `python -m scripts.init_db`
   (idempotent schema) before deploy, then starts
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2` (`railway.json`).
5. Check the live site: `curl -sS -o /dev/null -w "%{http_code}\n" https://dhwanijain.me/` and the
   page content.

The reviewed change I shipped this way is recorded in the
[submission index](docs/project-1-submission.md#5-a-reviewed-change-through-railway).

---

## Roll back a bad change

**Application code.** Either redeploy the previous successful deployment from the Railway
dashboard (fastest, no Git change), or `git revert <bad-sha>` and push, which deploys a new
commit with the old code. Reverting restores committed files only. It doesn't change Railway
variables, the database, or DNS.

**Database schema.** `app/schema.sql` only ever creates tables and indexes
(`CREATE … IF NOT EXISTS`), and runs before every deploy. Reverting code never drops anything, so
an older version still runs against a newer schema as long as changes are additive. Any
destructive schema change would need its own written down-migration and a backup first.

**Data.** The site has no write path: there's no admin page, and content only changes when I run
a script. So before any data change:

1. Back it up: `pg_dump --format=custom "$RAILWAY_DATABASE_URL" -f ~/backups/career-$(date -u +%Y%m%dT%H%MZ).dump`
   (outside the repo, because it holds personal data).
2. Make the change.
3. To undo: `pg_restore --clean --if-exists --no-owner -d "$RAILWAY_DATABASE_URL" <file>`, then
   reload the page and check it.

Not yet done: I haven't taken or test-restored a backup of Railway's database. See
[Limitations](#limitations).

**Hosting (the migration rollback).** Until the VM was deleted, rollback was DNS only: point the
root record back to A `4.155.216.147`, where the VM still had Nginx, its certificate and the same
data. Because nothing writes to the database, no data could have been written on Railway after
cutover that the VM would have missed. If writes are ever allowed, a rollback would first have to
export the rows changed since cutover and load them into the old database. The VM is now deleted,
so the remaining fallback is rebuilding: deploy from Git on another host and restore a `pg_dump`.

---

## The migration: what moved, and who manages what

The plan was written before anything changed (commit `85eb981`, before the code commits
`b64c875`…`1fb7fc3`). It lists what the target needed: code, runtime, packages, configuration,
secrets, schema and data.

| Need | How it moved |
|---|---|
| Code, `pyproject.toml`, `uv.lock`, `railway.json`, schema | Git |
| Python 3.13 runtime and packages | Railway's builder from the lock file |
| Configuration and secrets | Set by hand in Railway variables (never in Git) |
| Current data (SQLite on the VM) | **Not in Git.** Backed up on the VM with SQLite `.backup`, copied to my laptop, checksum matched, then loaded into Railway Postgres by `scripts/copy_sqlite_to_postgres.py` |
| DNS and certificate | Cloudflare record changed by hand; Railway issued a new certificate |

**SQLite → PostgreSQL compatibility** was converted in code (`?` → `%s`, `AUTOINCREMENT` →
`IDENTITY`, 0/1 → `BOOLEAN`, text dates → `DATE`/`TIMESTAMPTZ`, `executescript` and `PRAGMA`
removed) and tested against local Postgres before cutover. Details: the plan's Starting State
and Tasks 1–4.

**Preserving current data.** The copy kept every id and reset the identity sequences. Before
switching over, my coding agent ran a script comparing every table between the VM's database and
Railway Postgres, and all 14 tables matched (plan execution log, 2026-10-08). That script wasn't
committed. Not done: a deliberate real change to the data before the copy, and a rendered-page
comparison between the two hosts. See [Limitations](#limitations).

**Who manages what**

| | Azure VM (IaaS) | Railway (PaaS) |
|---|---|---|
| Physical hardware, hypervisor | Azure | Railway |
| Operating system and its patches | **Me** (Ubuntu 24.04) | Railway |
| Python runtime, packages | **Me** (`uv sync` over SSH) | Railway builds it; **I** pin versions in `uv.lock` |
| Web entry point | **Me** (Nginx config, NSG rules) | Railway's edge |
| TLS certificate and renewal | **Me** (Certbot + `certbot.timer`) | Railway |
| Process management | **Me** (systemd unit, `--workers 2`) | Railway (restart policy in `railway.json`, which **I** write) |
| Application code | **Me** | **Me** |
| Configuration and secrets | **Me** (`.env` on the VM) | **Me** (Railway variables) |
| Database software | **Me** (SQLite library) | Railway (managed Postgres 18) |
| Data, backups, restores | **Me** | **Me.** Railway runs the server, but the rows and getting them back are still my problem |
| DNS | **Me** (Cloudflare) | **Me** (Cloudflare) |
| Cost and expiry | **Me** | **Me.** The trial ends (see [Costs](#costs-and-cleanup)) |

PaaS took away the OS, runtime, proxy and certificates. It didn't take away my code, my
configuration, my data, my DNS or my bill.

---

## Decisions

Written 2026-10-21, after the work, from the plans and records.

### 1. SQLite first, then PostgreSQL on Railway

- **Chose:** SQLite for the first version and the Azure VM.
- **Alternatives:** PostgreSQL or MySQL installed on the VM.
- **Why:** one person, read-mostly, a few hundred rows. A file next to the app has no server to
  install, secure or keep running, and "the database is local" was literally true. The cost was
  known up front: moving later means converting SQL, which the Railway migration did.
- **Then PostgreSQL**, because a Railway container's disk is rebuilt on every deploy, so a SQLite
  file there would be wiped. A managed Postgres service keeps the data outside the container.

### 2. Move to Railway instead of staying on the VM

- **Alternatives:** keep the Azure VM; or move to Railway but keep SQLite on a volume.
- **Why Railway:** it removes OS patching, Nginx and Certbot from my list, and the course
  moves there. Postgres instead of a volume because the assignment requires it and it's a real
  database service I can reach from my laptop for the copy.
- **Given up:** control and visibility (I can't SSH into the edge or see its logs), a trial
  that expires, and one custom domain only, which is why `www` needs a Cloudflare redirect.

### 3. Managed email (Zoho) instead of self-hosting

- **Alternatives:** run a mail server (Postfix) on the VM; keep Namecheap's email forwarding,
  which was the domain's original MX ([dns-before-zoho.md](docs/evidence/dns-before-zoho.md)).
- **Why Zoho:** a self-hosted server needs a reputable sending IP, spam filtering, TLS, DKIM key
  management and constant uptime, and a new cloud VM's IP is the kind receivers distrust.
  Forwarding can receive but can't send from my address. Zoho's free plan sends and receives as
  me and signs DKIM, and I only maintain the DNS records.
- **Given up:** my mail is stored and run by Zoho, under their free plan's limits.

---

## Investigated failures

| Failure | Kind | Record |
|---|---|---|
| Six problems during the build and Azure migration: no lock file, no `.env` template, database code never committed, the database file tracked in Git, the Azure CLI on the wrong account, SSH timing out (VM deallocated **and** my IP changed). Each has symptom, check, cause, fix and repeated check. | Application / dependency, plus network | [docs/evidence/ex03.md](docs/evidence/ex03.md) |
| Certificate name mismatch caused by a stale DNS record pointing at the old VM. **This is the course's supplied simulation**, not my live domain. | DNS / TLS | [docs/evidence/ex05.md](docs/evidence/ex05.md) |
| `www` still pointed at the Azure VM's IP after the cutover. Before: A `4.155.216.147`, DNS only (snapshot 2026-10-13). Fix: proxied `www` record and a Cloudflare redirect rule (record changed 2026-10-20). Repeated check: `http://www` and `https://www` both 301 to the root with a valid certificate. | DNS | [dns-before-zoho.md](docs/evidence/dns-before-zoho.md), [final checks §2–4](docs/evidence/project-1-final-checks.md) |
| Database down: stopped on purpose (**deliberate test**) to check the 503 behavior and recovery without restart. | Database dependency | [final checks §6](docs/evidence/project-1-final-checks.md#6-database-failure-empty-table-and-recovery-local-after-the-fix) |

## Limitations

- **Railway data not re-compared today.** The 2026-10-08 comparison was run by an uncommitted
  agent script; no deliberate data change was made before the copy, and the two hosts' rendered
  pages weren't compared. Railway's Postgres no longer has a public URL, so I couldn't recheck
  from my laptop. The row counts recorded on Railway (1/4/5/16/3/8/18/18/2/1/5/0/0/0) are
  exactly what `scripts/seed_resume.py` produces, so the live data is most likely the seed
  content, unchanged.
- **Two failed Railway deployments on 2026-10-08** (`0c74dc20`, `bc840260`, both for commit
  `09e1437`, before the Postgres code was on `main`). Their logs are no longer available, so the
  cause wasn't recorded. The next deployment, `b8448c7d` for `8bea26e`, succeeded.
- **No database backup taken or tested** on Railway.
- **`/health` doesn't check the database.** Railway would call a deploy healthy even if Postgres
  were down. The page itself would correctly return 503.
- **The 503 behavior was tested locally**, not by stopping Railway's database.
- **No admin interface.** Content changes need a script.
- **A duplicated résumé bullet** from the source PDF is published (ex03 Known gaps).
- **DMARC is `p=none`** (monitor only), so spoofed mail claiming to be from my domain isn't
  rejected yet.
- **Leftover Azure resources:** the VM is deleted, but its static public IP, NSG and virtual
  network still exist, kept until the instructor's cleanup directions cover them. The IP bills
  about $3.60/month.

---

## Reflection

The biggest shift for me was realizing that a web request isn't one step but several: DNS finds
the address, TCP opens a connection, TLS proves the server is real, and only then does HTTP ask for
the page. That also showed me where TLS ends: on Azure it was Nginx on my own VM, with a
certificate I set up and renewed through Certbot, while on Railway the platform's edge holds the
certificate, so my app only ever sees plain HTTP. Moving between the two showed me the real
difference between running a VM and using a platform: Railway took over the OS, Nginx, the
firewall and certificates, but my code, data, DNS and costs were still mine to manage. If I did
this again, I'd record each check with its date and output as I went, because I had to rebuild my
Railway cutover timeline from DNS timestamps afterward, the logs for two failed deployments had
expired by the time I looked, and the script that compared my old and new databases was never
saved. I'd also review the AI's work more closely along the way, since the mistakes I caught, like
a plan step that overwrote my `.env`, came from reading each step before running it.

---

## Costs and cleanup

Checked 2026-10-21.

| Service | Plan / cost | Expires or renews | Cleanup |
|---|---|---|---|
| Railway (web + Postgres) | Trial: one-time $5.00 credit, 1 GB RAM, 2 vCPU, 1 GB disk. Used so far: **$0.80** (memory $0.76, CPU $0.03, volume $0.007, egress $0.0004). Memory is almost all of it: the web service and Postgres run all the time, whether or not anyone visits. | Dashboard on 2026-10-21: **"17 days or $4.20 left"**, so the trial ends about **2026-11-07**, or sooner if the credit runs out | Migrate to AWS after the midterm, before the trial ends; then delete the Railway project |
| Azure (`rg-career-platform`) | Personal subscription. **Actual cost Sep 1 – Oct 21: $6.64** (Cost Management API): VM compute $1.86 (`Standard_B2ts_v2`, list price $0.0104/hour), OS disk $1.58, static public IP $3.20 | — | VM and disk deleted, as the instructor directed. **Kept for now:** public IP `vm-career-platform-ip`, NSG and virtual network, since the directions covered only the VM. The IP still bills at the list price of $0.005/hour (about $3.60/month) and nothing uses it, so I'll ask the instructor whether to delete it |
| Domain `dhwanijain.me` | Namecheap, privacy protection on | **Expires 2027-09-30. Auto-renew is off,** so it lapses unless I renew it by then | Decide before Sep 2027 |
| Cloudflare DNS | Free | — | Keep |
| Zoho Mail | Forever Free | — | Keep |
| Google Analytics 4 | Free | — | Keep |
| GitHub | Free | — | Keep |
| Certificates | Free (Let's Encrypt via Railway and Cloudflare) | Root: 2027-01-06; `www`: 2027-01-04; renewed by the providers | — |
