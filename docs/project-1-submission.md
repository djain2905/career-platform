# Project 1 Submission — Career Platform

**Student:** Dhwani Jain
**Repository:** https://github.com/djain2905/career-platform
**Live site:** https://dhwanijain.me/
**Final commit SHA:** <!-- TODO(Dhwani): fill in after the last commit, then submit the same SHA in Brightspace -->

Times are Pacific unless marked UTC. Anything not verified is marked as such.

---

## 1. README, spec and plans

- [README](../README.md): what the site does, setup, update, rollback, architecture, decisions,
  failures, limitations, reflection, costs
- [Application spec](superpowers/specs/2026-09-15-career-platform-app-spec.md) and
  [implementation plan](superpowers/plans/2026-09-15-implementation-plan.md)
- Deployment plans: [Azure VM migration](superpowers/plans/2026-09-24-azure-vm-migration.md),
  [operating the VM](superpowers/plans/2026-10-01-operate-the-vm.md),
  [Railway + PostgreSQL migration](superpowers/plans/2026-10-08-railway-postgres-migration.md)

## 2. Diagrams

- [Railway and Azure architecture](../README.md#architecture), including the email and analytics
  paths
- [Request path, step by step](diagrams/request-path.png)

## 3. Migration: plan, data comparison, cutover, rollback

- **Plan, written before the change:** commit `85eb981` (2026-10-08), ahead of the code commits
  `b64c875`, `80a79a9`, `8262c58`, `b3e1f96`, `1fb7fc3`
- **Dependency inventory and SQLite → PostgreSQL conversion:** plan, "Starting State" and Tasks
  1–4; [README: the migration](../README.md#the-migration-what-moved-and-who-manages-what)
- **Source/target data comparison (2026-10-08):** plan execution log, Task 6. Row counts
  1/4/5/16/3/8/18/18/2/1/5/0/0/0, and 14 of 14 tables identical in a script my coding agent ran
  (script not committed).
- **Not done:** a deliberate real data change before the copy, and a rendered-page comparison
  between the VM and Railway
- **Cutover:** the root CNAME to Railway was created 2026-10-08 22:18 UTC (Cloudflare record
  metadata); Railway's certificate notBefore is 2026-10-08 21:23 UTC. Post-cutover checks:
  [final checks §1–5](evidence/project-1-final-checks.md) (2026-10-21)
- **Rollback, including data written after cutover:** [README: roll back](../README.md#roll-back-a-bad-change)
- **Who manages what on Azure vs Railway:** [README table](../README.md#the-migration-what-moved-and-who-manages-what)

## 4. Azure HTTP and restart evidence; final DNS and HTTPS

- **Azure:** [ex03.md](evidence/ex03.md) (VM, SSH, first deploy);
  [operate-the-vm Record and Execution Log](superpowers/plans/2026-10-01-operate-the-vm.md#record):
  listening ports, public/private IPs, NSG rules, Nginx, 2 workers, TLS, and the
  2026-10-08 restart test (both services active 9 s after boot)
- **HTTPS explanation (Ex04, my own words):** [how-this-site-is-secured.md](how-this-site-is-secured.md).
  It describes the Azure setup; the Railway certificate is recorded in final checks §4.
- **Final DNS and HTTPS (2026-10-21):** [final checks](evidence/project-1-final-checks.md): DNS
  records and their purpose, root 200 over HTTPS from Railway, `http://` → 301, `http://www` and
  `https://www` → 301 to the root, certificate names, issuers and dates
- **Before the Zoho change:** [dns-before-zoho.md](evidence/dns-before-zoho.md) (2026-10-13)

## 5. A reviewed change through Railway

Railway deploys from the GitHub repo `djain2905/career-platform`, branch `main`, on every push
(`railway status`, 2026-10-21). Secrets are only in Railway variables: the web service's
`DATABASE_URL` is a reference to the Postgres service's private address
(`postgres.railway.internal:5432`), never stored in the repo.

**The change: install the GA4 tag on every page**

| Step | Evidence |
|---|---|
| Change and its check, committed together | Commit `de29565` (2026-10-15 15:11 PDT): `app/templates/base.html` gets the tag, `tests/test_google_tag.py` checks every page renders it exactly once |
| Railway deployment | `884a58f5-146b-4be9-ac7b-951f028db9d6`, commit `de29565`, created 2026-10-15 22:11 UTC, status SUCCESS (`railway deployment list`). It stayed the active deployment until `ad2391f4` (a docs-only commit) at 2026-10-20 04:19 UTC. |
| Behavior at the domain | 2026-10-19 ~21:11 PDT (04:11 UTC on the 20th, while `884a58f5` was live): the live source of `/` and `/privacy` had one tag with `G-V64QT2T9EG`, and GA4 Realtime recorded `page_view` and the outbound `click` ([ex06.md §3](evidence/ex06.md#3-google-analytics)). Rechecked 2026-10-21: [final checks §5](evidence/project-1-final-checks.md#5-live-page). |
| Recovery | [README: roll back a bad change](../README.md#roll-back-a-bad-change), for code and data |

Not recorded at the time: my own review of the `de29565` diff and a local run before pushing.

**A second change, not yet deployed:** the database-failure fix (503 and "Projects temporarily
unavailable"), commit `c4e3154`. I read its diff before it was committed; my coding agent ran the
tests (48 passed) and the local database-down test
([final checks §6](evidence/project-1-final-checks.md#6-database-failure-empty-table-and-recovery-local-after-the-fix)).
It was pushed to `main` on 2026-10-21, but Railway's builds were down in every region that day
("Railway Platform Outage — Major Outage" on Railway's status page), so no deployment was created
before submission. The live site still runs deployment `436928c3` (commit `e0c21b0`).

## 6. Zoho email

- [ex06.md](evidence/ex06.md): before Zoho's records, Test 00 **bounced** (2026-10-13 14:08,
  while Namecheap's forwarding MX was still in place); then received (2026-10-13), replied
  (2026-10-19) and new outgoing (2026-10-13), each reaching the inbox
- [zoho-header-check.md](evidence/zoho-header-check.md): SPF, DKIM and DMARC pass, with the DNS
  record each used
- MX, SPF, DKIM and DMARC records as published: [final checks §1–2](evidence/project-1-final-checks.md)

## 7. GA4

- [ex06.md §3](evidence/ex06.md#3-google-analytics): GA4 Realtime on 2026-10-19 at about 21:11
  showed `page_view` and an outbound `click` (`link_url` = `https://github.com/djain2905`,
  `outbound` = `true`), with screenshots
- **Install:** commit `de29565` puts the tag in `app/templates/base.html`, so every page loads it
  once (`tests/test_google_tag.py`)
- **How the data gets there:** the page's HTML loads `gtag.js` from `googletagmanager.com`.
  Running in the visitor's browser, it sends a `page_view` hit over HTTPS to
  `google-analytics.com` when the page loads. GA4's enhanced measurement listens for clicks on
  links to other domains and sends a `click` event with `link_url`, `link_domain` and
  `outbound`. My server never sees these hits; they go straight from the browser to Google.
- **What my check shows:** the events arrived from a real browser visit and the parameters match
  the link I clicked. It doesn't show who the visitor was or why they clicked, and a browser
  that blocks Google Analytics sends nothing.
- **Why the click matters:** it shows which outside profiles visitors follow, such as my GitHub.

## 8. Failures, decisions, reflection, costs, limitations

- [Investigated failures](../README.md#investigated-failures): [ex03.md](evidence/ex03.md)
  (build and Azure), [ex05.md](evidence/ex05.md) (DNS/TLS, course simulation), the `www` record,
  and the deliberate database-down test
- [Decisions](../README.md#decisions)
- [Reflection](../README.md#reflection)
- [Costs and cleanup](../README.md#costs-and-cleanup)
- [Limitations](../README.md#limitations)
