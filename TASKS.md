# Project 1 gaps

From the requirements audit on 2026-10-20 against `95b51b2`. Each line names the file or check that closes it.

## 1. Profile and project data

- [x] On DB failure, show the profile, show "Projects temporarily unavailable" and return 503 instead of serving the snapshot with 200 — `app/repository.py`, `app/main.py`, `app/templates/index.html`, `tests/test_repository.py`
- [x] Show a deliberate message when the projects table is empty instead of hiding the section — `app/templates/index.html`
- [ ] Add a project entry, clearly labeled, describing this website as a work in progress — `scripts/seed_resume.py` plus a row in Railway Postgres
- [x] Explain why SQLite was the first database engine — README "Decisions" section
- [ ] Check live (done locally 2026-10-21, not on Railway): DB down gives 503 with profile visible, DB back gives 200 with projects on refresh, no restart — dated result in `docs/evidence/`

## 2. Azure deployment

- [x] Explain which settings made the site survive a restart (systemd enable, loopback bind, Nginx site) — README or `docs/superpowers/plans/2026-10-01-operate-the-vm.md`
- [x] Tick the completed task checkboxes to match the execution log — `docs/superpowers/plans/2026-10-01-operate-the-vm.md`
- [x] Record the VM's current state (running, stopped or deleted, and per whose instruction) — README costs/cleanup section

## 3. Domain and HTTPS

- [x] Make `www` a proxied record with a Cloudflare redirect rule to the root, not `A 4.155.216.147` — Cloudflare DNS
- [x] Verify `http://www` and `https://www` both land on the root with a valid certificate — dated `curl -I` output in `docs/evidence/`
- [x] Record the Railway certificate's hostname, issuer, validity and renewal — `openssl s_client` output in `docs/evidence/`
- [x] Write a table of the final DNS records and their purposes, with verification — `docs/evidence/` (from `cf dns records list` / `dig`)
- [x] ~~Add a dated note to `docs/how-this-site-is-secured.md`~~ Left as my own Ex04 write-up; the Railway certificate is recorded in `docs/evidence/project-1-final-checks.md` instead
- [x] Commit the before-Zoho DNS snapshot — `docs/evidence/dns-before-zoho.md`

## 4. Railway and PostgreSQL migration

- [ ] Record the real change made to the original data before the copy, and show it on Railway — Railway plan execution log
- [ ] ~~Compare the rendered page on the VM and on Railway~~ Can't now, VM deleted; recorded as a limitation — Railway plan execution log
- [x] Log Task 7 (deploy, variables, Railway-domain checks, redeploy) — logged 2026-10-21 after `railway login` — `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
- [x] Log Task 8 (cutover date, DNS changes, post-cutover checks) — `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
- [x] Log Task 9 or note why it changed — `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
- [x] Fill in the Task 0 findings (service names, deploy source, Railway host) — `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
- [x] Write a rollback procedure that covers data written after cutover and no longer relies on the VM — README rollback section
- [x] Compare who manages the OS, runtime, web entry point, TLS, code, configuration, DB software, data and DNS on Azure vs Railway, plus what's still yours — README
- [x] Link the spec and the Railway plan — README and `docs/project-1-submission.md`

## 5. Reviewed change through Railway

- [x] Confirm GitHub is connected to Railway and record the deploy branch — Railway dashboard, note in README
- [ ] Record the diff review and local check for one change — README or `docs/evidence/`
- [x] Tie that commit's SHA to its Railway deployment and the live behavior — Railway deployment ID + dated `curl` in `docs/evidence/`
- [x] Write how to restore a previous version for code and for database changes — README rollback section

## 6. Zoho email

- [x] Create the header analysis — `docs/evidence/zoho-header-check.md`
- [x] Add the before-MX message line, with the Namecheap forwarding MX in mind — `docs/evidence/ex06.md`
- [x] Record and explain the final MX, SPF, DKIM and DMARC records — `docs/evidence/ex06.md` or `zoho-header-check.md`
- [x] Link `ex06.md` and `zoho-header-check.md` — README and `docs/project-1-submission.md`

## 7. GA4

- [x] Explain how browser activity reaches GA4 (gtag.js → dataLayer → collect request) and what the checks prove — `docs/evidence/ex06.md` or README

## 8. Engineering record

- [x] Live address, what the site does, setup and update steps — `README.md`
- [x] Azure and Railway diagrams with locations, protocols, ports, data flow, email and analytics paths — `README.md` or a linked diagram file
- [x] At least two decisions with alternatives (Railway migration, managed vs self-hosted email) — `README.md`
- [x] Link the investigated failures (`docs/evidence/ex03.md`, `docs/evidence/ex05.md`, marked as simulation) and remaining limitations — `README.md`
- [x] Short reflection — `README.md`
- [x] Costs or credits, Railway trial end date, expiry dates, cleanup plans — `README.md`
- [x] Add the final commit SHA and links for submission items 1–8 — `docs/project-1-submission.md`
- [x] Run `uv run pytest` and record the result — README or `docs/evidence/`
