# Project 1 — final checks (2026-10-21)

**Run:** 2026-10-21, about 21:16–21:18 UTC (14:16–14:18 PDT), from my laptop.
**Run by:** my coding agent (Claude Code) at my request. I reviewed the output below.
Commands and results are copied as they came back. Nothing here is an expected result.

---

## 1. DNS — what the public sees

Cloudflare's public resolver over HTTPS (`https://cloudflare-dns.com/dns-query`):

| Name | Type | TTL | Answer |
|---|---|---|---|
| `dhwanijain.me` | NS | 86400 | `anna.ns.cloudflare.com.`, `finley.ns.cloudflare.com.` |
| `dhwanijain.me` | A | 60 | `69.46.46.53` (Railway edge, from the flattened CNAME) |
| `www.dhwanijain.me` | A | 300 | `104.21.63.252`, `172.67.173.178` (Cloudflare proxy) |
| `dhwanijain.me` | MX | 300 | `10 mx.zoho.com.`, `20 mx2.zoho.com.`, `50 mx3.zoho.com.` |
| `dhwanijain.me` | TXT | 300 | `"v=spf1 include:zohomail.com ~all"`, `"zoho-verification=zb13840999.zmverify.zoho.com"` |
| `_dmarc.dhwanijain.me` | TXT | 300 | `"v=DMARC1; p=none; rua=mailto:dhwani@dhwanijain.me"` |
| `zmail._domainkey.dhwanijain.me` | TXT | 300 | `"v=DKIM1; k=rsa; p=MIGfMA0G…"` (public key, truncated here) |

## 2. DNS — the zone as configured

`cf dns records list --zone dhwanijain.me`, summarized:

| Type | Name | Proxy | Content | Purpose | Last modified |
|---|---|---|---|---|---|
| CNAME | `dhwanijain.me` | DNS only | `8udvcs1q.up.railway.app` | Website → Railway. Cloudflare flattens it to A records at the root. | 2026-10-08 |
| TXT | `_railway-verify.dhwanijain.me` | DNS only | `railway-verify=…` | Proves to Railway that I own the domain | 2026-10-08 |
| A | `www.dhwanijain.me` | **Proxied** | `192.0.2.1` (placeholder, never contacted) | Exists only so Cloudflare answers for `www` and its redirect rule sends visitors to the root | 2026-10-20 |
| MX ×3 | `dhwanijain.me` | DNS only | `mx.zoho.com` (10), `mx2.zoho.com` (20), `mx3.zoho.com` (50) | Incoming mail → Zoho | 2026-10-13 |
| TXT | `dhwanijain.me` | DNS only | `v=spf1 include:zohomail.com ~all` | SPF: Zoho's servers may send for the domain | 2026-10-13 |
| TXT | `dhwanijain.me` | DNS only | `zoho-verification=…` | Proves to Zoho that I own the domain | 2026-10-13 |
| TXT | `zmail._domainkey.dhwanijain.me` | DNS only | `v=DKIM1; k=rsa; p=…` | DKIM public key Zoho signs with | 2026-10-13 |
| TXT | `_dmarc.dhwanijain.me` | DNS only | `v=DMARC1; p=none; rua=…` | DMARC: monitor only, reports to my address | 2026-10-13 |

Nothing points at the old Azure VM address `4.155.216.147` any more. On 2026-10-13 the `www`
record still did (see `dns-before-zoho.md`).

## 3. HTTPS and redirects

```text
$ curl -sS -o /dev/null -w "%{http_code} -> %{redirect_url}\n" http://dhwanijain.me/
301 -> https://dhwanijain.me/

$ curl -sS -o /dev/null -w "%{http_code}\n" https://dhwanijain.me/
200

$ curl -sSI https://dhwanijain.me/ | grep -i -E "^server|^x-railway"
server: railway-hikari
x-railway-request-id: -fm9FR6RS6WGM6DTaP71AA
x-railway-edge: lax1

$ curl -sS -o /dev/null -w "%{http_code} -> %{redirect_url}\n" http://www.dhwanijain.me/
301 -> https://dhwanijain.me/

$ curl -sS -o /dev/null -w "%{http_code} -> %{redirect_url}\n" https://www.dhwanijain.me/
301 -> https://dhwanijain.me/
```

Both `http://www` and `https://www` land on the root. The `server: railway-hikari` and
`x-railway-edge` headers show the root is answered by Railway's edge.

## 4. Certificates

```text
$ echo | openssl s_client -connect dhwanijain.me:443 -servername dhwanijain.me 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates -text | grep -E "subject=|issuer=|notBefore|notAfter|DNS:"
subject= /CN=dhwanijain.me
issuer= /C=US/O=Let's Encrypt/CN=YE1
notBefore=Oct  8 21:23:48 2026 GMT
notAfter=Jan  6 21:23:47 2027 GMT
                DNS:dhwanijain.me

$ (same for www.dhwanijain.me)
subject= /CN=dhwanijain.me
issuer= /C=US/O=Let's Encrypt/CN=YE2
notBefore=Oct  6 20:41:27 2026 GMT
notAfter=Jan  4 20:41:26 2027 GMT
                DNS:*.dhwanijain.me, DNS:dhwanijain.me
```

| Name | Who serves the certificate | Covers | Valid | Renewal |
|---|---|---|---|---|
| `dhwanijain.me` | Railway's edge | `dhwanijain.me` | 2026-10-08 → 2027-01-06 | Railway renews it automatically. I don't run or see the renewal. |
| `www.dhwanijain.me` | Cloudflare's proxy (because `www` is proxied) | `*.dhwanijain.me`, `dhwanijain.me` | 2026-10-06 → 2027-01-04 | Cloudflare's edge certificate, renewed by Cloudflare |

The certificate Certbot issued on the Azure VM (2026-10-06 → 2027-01-04, see
`docs/how-this-site-is-secured.md`) no longer serves anything; the VM is deleted (section 7).

## 5. Live page

```text
$ curl -sS https://dhwanijain.me/ | grep -o -E "Showing saved content|G-V64QT2T9EG|<h2 id=\"h-projects\">Projects" | sort | uniq -c
   1 <h2 id="h-projects">Projects
   2 G-V64QT2T9EG

$ curl -sS https://dhwanijain.me/health
{"status":"ok","app":"Career Platform"}
```

The live page has no "Showing saved content" banner, so it was a live database read. The Google
tag ID appears twice because the tag loads the script with the ID and then configures it.

## 6. Database failure, empty table and recovery (local, after the fix)

Run against my local Docker PostgreSQL (`career-pg-test`, database `career_dev`, seeded with
`scripts/seed_resume.py`), with the app started once by
`uvicorn app.main:app --port 8765 --workers 2` and **not restarted** during the test.
This is a deliberate test failure: I stopped the database container on purpose.

```text
[21:18:19Z] 1 healthy
  status 200
     1 <h1>Dhwani Jain</h1>
     1 L&#39;Oréal Consumer Intelligence
[21:18:20Z] 2 database stopped            (docker stop career-pg-test)
  status 503
     1 <h1>Dhwani Jain</h1>
     1 Projects temporarily unavailable
     1 Showing saved content
[21:18:24Z] 3 database started, app not restarted   (docker start career-pg-test)
  status 200
     1 <h1>Dhwani Jain</h1>
     1 L&#39;Oréal Consumer Intelligence
```

The empty-table case is covered by `tests/test_pages.py::test_empty_project_table_returns_200_with_a_message`
(200 and "No projects published yet"). Full suite: `uv run pytest` → **48 passed**.

**Not yet run on Railway.** This test was local. Stopping Railway's PostgreSQL would take the real
site down, so I haven't done it there.

## 7. Azure

```text
$ az vm list -o tsv | wc -l
0
$ az resource list --query "[].{n:name,t:type}" -o tsv
vm-career-platform-ip     Microsoft.Network/publicIPAddresses
vm-career-platform-nsg    Microsoft.Network/networkSecurityGroups
vnet-westus2-1            Microsoft.Network/virtualNetworks
NetworkWatcher_westus2    Microsoft.Network/networkWatchers
```

The VM is deleted, as the instructor directed. Its static public IP, NSG and virtual network
still exist in `rg-career-platform`. The Azure evidence from while it ran is kept in
`docs/evidence/ex03.md` and `docs/superpowers/plans/2026-10-01-operate-the-vm.md`.

## 8. Railway (after `railway login`, later on 2026-10-21)

```text
$ railway status --json        (summarized)
active deployment  436928c3-db9e-4abb-abf3-5a2d729fd3ac   created 2026-10-20 21:43 UTC   RUNNING
source             repo djain2905/career-platform, branch main, commit e0c21b0
plan               trial
builder            Railpack, Python 3.13.16, uv

$ railway variables --service career-platform --kv    (values hidden)
DATABASE_URL=postgresql://<user:pass>@postgres.railway.internal:5432/railway
(no APP_ENV or APP_NAME)
```

The web service reaches PostgreSQL over Railway's private network. The Postgres service has no
public URL.

## Not checked here

- **Railway PostgreSQL contents.** With no public URL, the live data couldn't be compared from my
  laptop. Running the read-only check inside Railway (`railway ssh`) needs an SSH key registered
  to my Railway account, which I haven't added.
