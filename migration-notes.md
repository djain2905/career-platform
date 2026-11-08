# AWS migration notes

The running log of deviations from the plan, as the guide asks. The plan, with every command and its expected output, is
[`docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md`](docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md).
Its Execution Log has the step-by-step record.

## Decision

I chose **EC2 + Single-AZ RDS PostgreSQL** over EC2 with PostgreSQL on the instance because I want to learn to run
the server (Nginx, Certbot, systemd) without managing the database, and I accept the extra service and the higher
monthly cost (about $26.50 instead of about $13). (Over Lambda: Lambda would need app changes and database-connection
handling, for little gain on a site this small.)

## Backup (guide §2)

| | |
|---|---|
| Backup | `pg_dump` custom format from Railway Postgres 18.6, taken 2026-10-29 22:03 UTC, 40,757 bytes, kept outside the repo (mode 600) |
| Restore test | 2026-10-29, into a local `postgres:18` container. Row counts, content hashes and 14 sequences matched the source, and the app rendered from it |
| Frequency and retention, from now on | RDS automated backups daily, kept **1 day** (the Free plan's limit), plus a manual `pg_dump` before every risky change, kept outside AWS |
| RPO / RTO | RPO: one day. The content changes rarely, and every edit is made by me. RTO: one hour, to restore the latest dump into RDS from the instance |

## Deviations

| Date | Plan or guide said | What happened | Why |
|---|---|---|---|
| 2026-11-03 | RDS backups kept 7 days | Kept **1 day** | `FreeTierRestrictionError`: the account is on the Free plan. I chose to stay Free over upgrading to Paid |
| 2026-11-03 | Security groups in Task 2, with the key | Both groups created during the RDS step; key imported at launch | RDS needs its group, and its rule refers to the web group. The guide does the same |
| 2026-11-03 | Guide §8: Ubuntu 26.04, 20 GB | Ubuntu **24.04**, **16 GB** | The plan matched the Azure VM. I kept the running instance on 2026-11-08 instead of rebuilding it. `pg_restore` 18 comes from the PGDG apt repository |
| 2026-11-03 | Trust the SSH host key on first use | Compared `ssh-keyscan` with the instance's boot log first. ED25519 `SHA256:ZcRO8jUj…zQ` matched | Proves it's my instance before connecting |
| 2026-11-08 | Guide §1: zero-spend budget | A monthly cost budget of **$1** | My choice. It works the same way: it emails me at the first charge not covered by credits |
| 2026-11-08 | Fresh Railway dump at cutover; Railway kept as rollback | **Railway's trial ended around 2026-11-07**, and `dhwanijain.me` has returned 404 from Railway since. The Oct 29 dump is the data to restore | I made no edits after Oct 29, so that dump is current. There's no rollback target, so AWS has to go live |
| 2026-11-08 | Plan cut over the apex directly | Added the guide's test name `aws.dhwanijain.me` (plan Task 8) before cutover (Task 9) | Follows guide §10 |
