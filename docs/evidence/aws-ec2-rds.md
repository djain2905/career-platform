# AWS EC2 + RDS: test-subdomain checks

Checked 2026-11-08 (UTC), on branch `aws-ec2-rds-migration` at `cdb0801`, before the cutover. The Elastic IP is
written as `<EIP>` because this repo is public. The plan is
[`docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md`](../superpowers/plans/2026-11-03-aws-ec2-rds-migration.md),
and the deviations are in [`migration-notes.md`](../../migration-notes.md).

## DNS

| Check | Result |
|---|---|
| Record added with the Cloudflare CLI | `A aws.dhwanijain.me → <EIP>`, DNS only |
| Other records | Unchanged. A before/after diff of `cf dns records list` showed one record added, none changed or removed |
| `dig @1.1.1.1`, `dig @8.8.8.8`, `nslookup` | All three return `<EIP>` |

## HTTPS

| Check | Result |
|---|---|
| Certificate | `CN = aws.dhwanijain.me`, issuer Let's Encrypt `YE2`, valid 2026-11-08 → 2027-02-06 |
| How | `certbot --nginx -d aws.dhwanijain.me --redirect`, registered without an email (owner's choice) |
| `http://aws.dhwanijain.me` | `301` → `https://aws.dhwanijain.me/` |
| Where TLS ends | Nginx on the instance (`Server: nginx/1.24.0 (Ubuntu)`) |

## The app

| Check | Result |
|---|---|
| `https://aws.dhwanijain.me/` | `200`. No "Showing saved content" banner, no "Projects temporarily unavailable", current role "HUM Nutrition" present |
| `/privacy` | `200` |
| `/static/css/styles.css` (the only stylesheet the page links) | `200` |
| `/health` | `{"status":"ok","app":"Career Platform"}` |
| `/docs` | `404` (the auto-generated API docs stay off) |
| Google tag | Present on the page |
| Port 8000 from the internet | Closed (`000`). Uvicorn listens on `127.0.0.1:8000` only |

## Data and the database

| Check | Result |
|---|---|
| Backup restored | Oct 29 Railway dump, sha256 `7440740f34d2892f…`, restored in 248 ms as `career_app` |
| Row counts | Identical to the backup: person_profile 1, contact_method 4, role_experience 5, experience_highlight 16, project 3, project_highlight 8, skill 18, skill_proficiency 18, education_record 2, certification 1, achievement 5, content_section 0, tag 0, entity_tag 0 |
| PostgreSQL stays private | RDS `PubliclyAccessible = false`. Its security group allows 5432 only from the web server's security group |
| TLS to RDS | `sslmode=disable` refused (`no pg_hba.conf entry … no encryption`). `verify-full` connects with TLSv1.3 |
| Database outage | 5432 rule revoked: `503`, profile still shown, "Projects temporarily unavailable". Rule restored: `200` with no restart |
| Instance stop/start | Elastic IP unchanged, homepage `200` with no manual step |

## Not verified yet

- The real domain `dhwanijain.me` still points at Railway, which has returned `404` since the trial ended. That's for the cutover.
- `certbot renew --dry-run` was still in its random pre-run delay when this was written. Its result is in the plan's Execution Log.
- Visual check in a browser (padlock and layout): for the owner.
- No load testing. The site gets very little traffic.
