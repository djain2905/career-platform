# Operate the Site on the VM — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Career Platform site from a hand-started process on port 8000 into a real service reachable at `http://dhwanijain.me` with no port number, which survives a VM restart with nobody logged in.

**Architecture:** Nginx becomes the only program facing the internet, listening on port 80. It forwards every request to Uvicorn on `127.0.0.1:8000` — the loopback address, which never leaves the machine — so Uvicorn becomes unreachable from outside the VM. Uvicorn runs two workers under systemd, which starts it at boot and restarts it after a crash. The domain reaches the VM because Cloudflare answers DNS for `dhwanijain.me` with the VM's static public IP, with the proxy off (DNS only) so visitors connect straight to the VM.

**Tech Stack:** Ubuntu 24.04.4 LTS (Azure VM), Nginx 1.24.0, Uvicorn 0.30.6, FastAPI 0.115.0, Python 3.13.15, systemd, SQLite, Cloudflare DNS, Namecheap (registrar)

**Spec:** Course session handouts — "Operate your site on the VM" (Session 10, 2026-10-01) and its successor "Secure your site with HTTPS" (Session 11, 2026-10-06). Application spec: `docs/superpowers/specs/2026-09-15-career-platform-app-spec.md`. Prior deployment state: `docs/superpowers/plans/2026-09-24-azure-vm-migration.md` and `docs/evidence/ex03.md`.

## VM Details

Confirmed live via `az` and SSH on 2026-10-06.

| Property | Value |
|---|---|
| VM name | `vm-career-platform` |
| Resource group | `rg-career-platform` |
| Region | `westus2` |
| OS | Ubuntu 24.04.4 LTS |
| Public IP | `4.155.216.147` (Standard SKU, **Static**) |
| Private IP | `172.16.0.4` |
| Admin user | `azureuser` |
| SSH | `ssh career-vm` (alias in `~/.ssh/config`; key `~/.ssh/isba4775_azure`) |
| App root | `/home/azureuser/career-platform` |
| NSG | `vm-career-platform-nsg` |
| Subscription | Personal (`<PERSONAL_SUBSCRIPTION_ID>`), **not** LMU |

## Global Constraints

- **No step opens port 8000 to the internet.** Port 8000 is loopback-only from Task 1 onward. If any step appears to require opening it, the step is wrong.
- **The app never runs as root.** `User=azureuser` in the systemd unit, unchanged.
- **Azure resource changes are the owner's, made in the portal.** This plan never runs `az network nsg rule create` or any other mutating `az` command. Tasks 3 and 5 are owner-executed and say so.
- **Namecheap and Cloudflare changes are the owner's.** The agent has no credentials for either. Task 4 verifies the result; it does not perform the change.
- **Service name is `career-platform`**, already created by the 2026-09-24 migration. This plan modifies its unit file rather than creating a new service.
- **Dependency versions are frozen:** `fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `jinja2==3.1.4`, `python-dotenv==1.0.1`. Nothing in this plan upgrades them.
- **No repo files change and no tests are added.** All configuration lives on the VM, outside the git working tree. The only repo change is this plan file itself.
- **Personal data stays out of git.** `data/resume.db` is gitignored and must remain so.
- **Every section is reversible.** Each task ends with an "Undo" block that restores the prior state.
- **`server_name` is `dhwanijain.me www.dhwanijain.me`** from Task 2 onward, so Session 11's Certbot run finds the correct server block.

## Review Focus

Conditions the handout implies but no task's main path exercises. Each has its check folded into the owning task.

1. **Nginx's default welcome site shadowing the real one** — if `/etc/nginx/sites-enabled/default` survives, visitors may get "Welcome to nginx" instead of the resume. Checked in Task 2, Step 6.
2. **`HEAD /` returning 405** — `app/main.py` registers only `@app.get("/")`, so `curl -I` against the app returns `405 Method Not Allowed` with `allow: GET`. This is not an outage. Task 3 verifies with `curl -i` (GET) and records the 405 as expected behavior.
3. **The service starting but never being enabled** — `start` and `enable` are different; without `enable` the site does not return after a restart. Asserted explicitly in Task 1, Step 7 and proven in Task 5.
4. **The app starting in the wrong working directory** — `DATABASE_URL=sqlite:///./data/resume.db` is relative, so a wrong `WorkingDirectory=` silently serves the demo placeholder profile instead of real data. Task 1, Step 8 verifies real content, not just a 200.
5. **Campus Wi-Fi blocking the new domain** — LMU's network returns a "Web Page Blocked" page for domains it has not reviewed. This is indistinguishable from a broken site in a browser. Task 4 verifies from public resolvers and from the VM itself, never from the campus browser alone.

---

## Task 1: Bind Uvicorn to loopback with two workers

**For a beginner:** Right now Uvicorn listens on `0.0.0.0:8000`. `0.0.0.0` means "every network interface" — anyone who can reach the VM on port 8000 reaches the app directly, skipping the front door. The only thing preventing that today is the absence of a firewall rule, which is luck rather than design. Changing it to `127.0.0.1` means the app answers only to programs running on the VM itself. Nginx is one of those programs, so the site still works, but nothing outside can bypass Nginx. The `--workers 2` flag makes Uvicorn run one main process plus two worker processes, so a single worker crashing does not take the site down.

**Files:**
- Modify (on the VM): `/etc/systemd/system/career-platform.service`
- Backup (on the VM): `/home/azureuser/career-platform.service.bak`

**Where this runs:** All steps over SSH on the VM (`ssh career-vm`).

**Interfaces:**
- Consumes: the existing `career-platform` service and the `.venv` at `/home/azureuser/career-platform/.venv`.
- Produces: an app reachable only at `127.0.0.1:8000`, which Task 2's `proxy_pass` depends on.

- [ ] **Step 1: Back up the current unit file**

```bash
ssh career-vm 'sudo cp /etc/systemd/system/career-platform.service /home/azureuser/career-platform.service.bak && ls -la /home/azureuser/career-platform.service.bak'
```

Expected: the backup file is listed. This is what the Undo block restores.

- [ ] **Step 2: Record the current state for comparison**

```bash
ssh career-vm 'sudo ss -ltnp | grep 8000'
```

Expected: one line showing `0.0.0.0:8000`. Save this output — Step 6 compares against it.

- [ ] **Step 3: Write the new unit file**

Replace the whole file. Two lines change: `ExecStart` now points at the venv's own `uvicorn` binary rather than `uv run` (so startup does not depend on `uv` resolving the environment), binds `127.0.0.1`, and adds `--workers 2`.

```bash
ssh career-vm 'sudo tee /etc/systemd/system/career-platform.service > /dev/null <<EOF
[Unit]
Description=Career Platform FastAPI site
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/career-platform
ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'
```

- [ ] **Step 4: Show the new file and confirm the changed lines**

```bash
ssh career-vm 'cat /etc/systemd/system/career-platform.service'
```

Expected: `ExecStart` reads `--host 127.0.0.1 --port 8000 --workers 2`. `User=azureuser` and `WorkingDirectory=/home/azureuser/career-platform` are unchanged.

- [ ] **Step 5: Reload systemd and restart the service**

`daemon-reload` makes systemd reread unit files from disk; without it, systemd keeps using the old definition.

```bash
ssh career-vm 'sudo systemctl daemon-reload && sudo systemctl restart career-platform && sleep 3 && systemctl is-active career-platform'
```

Expected: `active`

- [ ] **Step 6: Verify the listening address changed**

```bash
ssh career-vm 'sudo ss -ltnp | grep 8000'
```

Expected: `127.0.0.1:8000`, and **no** `0.0.0.0:8000` line. If `0.0.0.0` is still present, the service did not pick up the new unit — rerun `daemon-reload`.

- [ ] **Step 7: Verify the service is enabled, not merely started**

`start` runs it now. `enable` makes it start at every boot. Task 5's restart test depends on `enable`.

```bash
ssh career-vm 'systemctl is-enabled career-platform'
```

Expected: `enabled`. If it says `disabled`, run `sudo systemctl enable career-platform` and check again.

- [ ] **Step 8: Verify the app serves real data, not the demo profile**

A 200 alone does not prove the database was found — the app falls back to a placeholder profile when it cannot read `data/resume.db`. Check for actual content.

```bash
ssh career-vm 'curl -sS http://127.0.0.1:8000 | grep -ci "dhwani"'
```

Expected: a count of 1 or greater. A `0` means the app started in the wrong directory and is serving the demo profile — check `WorkingDirectory=`.

- [ ] **Step 9: Confirm the process tree**

```bash
ssh career-vm 'systemctl status career-platform --no-pager | sed -n "/CGroup/,$p"'
```

Expected: four processes under the service's cgroup — the main `uvicorn` process, two `spawn_main` workers, and one `resource_tracker` helper.

Do **not** verify this with `ps -ef | grep uvicorn`: that returns only one line. Uvicorn starts its workers through Python's `multiprocessing`, so a worker's command line reads `spawn_main`, not `uvicorn`, and the grep misses them. The main process is the one systemd reports as `Main PID`; the workers are its children, which `ps -ef | awk '$3==<MainPID>'` lists. (`ps` truncates `azureuser` to `azureus+`. The `resource_tracker` helper is normal.)

**Undo Task 1:**

```bash
ssh career-vm 'sudo cp /home/azureuser/career-platform.service.bak /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload && sudo systemctl restart career-platform && systemctl is-active career-platform'
```

---

## Task 2: Install Nginx as the front door

**For a beginner:** Nginx is a web server built to face the internet. It handles slow connections, malformed requests and (from Session 11) HTTPS, before any of that reaches Python. Here it acts as a *reverse proxy*: it accepts every request on port 80 and hands it to Uvicorn on `127.0.0.1:8000`, then passes the answer back. A `server { ... }` block holds the settings for one site — which port to listen on, which domain names to match, and where to send requests. Naming the domain in `server_name` now (instead of the placeholder `_`) is what lets Certbot find this block in Session 11.

Changing `server_name` does **not** change where DNS sends visitors. DNS decides which machine they reach; `server_name` decides which block on that machine answers them.

**Files:**
- Create (on the VM): `/etc/nginx/sites-available/career-platform`
- Create (on the VM): symlink `/etc/nginx/sites-enabled/career-platform`
- Remove (on the VM): symlink `/etc/nginx/sites-enabled/default`

**Where this runs:** All steps over SSH on the VM.

**Interfaces:**
- Consumes: Uvicorn listening on `127.0.0.1:8000` from Task 1.
- Produces: Nginx listening on `0.0.0.0:80` with `server_name dhwanijain.me www.dhwanijain.me`. Session 11's `certbot --nginx` modifies this exact file.

- [ ] **Step 1: Install Nginx**

```bash
ssh career-vm 'sudo apt-get update && sudo apt-get install -y nginx && nginx -v'
```

Expected: `nginx version: nginx/1.24.0 (Ubuntu)`

- [ ] **Step 2: Confirm Nginx is listening and serving its default page**

```bash
ssh career-vm 'systemctl is-active nginx && curl -sI http://localhost | head -1'
```

Expected: `active`, then `HTTP/1.1 200 OK` — this is still Nginx's own welcome page, not the site. Step 4 replaces it.

- [ ] **Step 3: Write the site configuration**

`proxy_pass` is the line that hands each request to Uvicorn. The `proxy_set_header` lines pass along what Nginx knows about the original request — the hostname the visitor asked for, their IP address, and whether they arrived over HTTP or HTTPS — which would otherwise be lost, since Uvicorn only ever sees a connection from `127.0.0.1`.

```bash
ssh career-vm 'sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;

    server_name dhwanijain.me www.dhwanijain.me;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF'
```

- [ ] **Step 4: Enable this site and disable the default one**

`sites-available` holds every site Nginx knows about; `sites-enabled` holds symlinks to the ones it actually serves. Nginx ships a sample welcome site that answers every request not matched by name — if it stays enabled it can shadow the real site.

```bash
ssh career-vm 'sudo ln -sf /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform && sudo rm -f /etc/nginx/sites-enabled/default && ls -la /etc/nginx/sites-enabled/'
```

Expected: `career-platform` is listed; `default` is gone.

- [ ] **Step 5: Test the configuration before loading it**

`nginx -t` parses the config without applying it, so a typo cannot take the site down.

```bash
ssh career-vm 'sudo nginx -t'
```

Expected: `syntax is ok` and `test is successful`. On failure, the message names the file and line number — fix that line and retest before reloading.

- [ ] **Step 6: Reload Nginx and confirm the site answers through it**

A reload makes Nginx reread its settings without dropping connections.

```bash
ssh career-vm 'sudo systemctl reload nginx && curl -sS http://localhost | grep -ci "dhwani"'
```

Expected: a count of 1 or greater, proving Nginx proxied to the app and the app found the database. A `0` with a 200 status means the default welcome page is still being served — recheck Step 4.

- [ ] **Step 7: Confirm which program answered**

```bash
ssh career-vm 'curl -sI http://localhost | grep -i server'
```

Expected: `Server: nginx/1.24.0 (Ubuntu)`. Both programs did the work — Nginx took the request and set this header, Uvicorn produced the body.

- [ ] **Step 8: Confirm port 8000 is still loopback-only**

```bash
ssh career-vm 'sudo ss -ltnp | grep -E ":80|:8000"'
```

Expected: `0.0.0.0:80` (nginx) and `127.0.0.1:8000` (uvicorn). There must be no `0.0.0.0:8000`.

**Undo Task 2:**

```bash
ssh career-vm 'sudo rm -f /etc/nginx/sites-enabled/career-platform && sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx'
```

To remove Nginx entirely: `ssh career-vm 'sudo apt-get remove -y nginx nginx-common && sudo systemctl is-active nginx'` (expect `inactive`).

---

## Task 3: Open port 80 (owner-executed, Azure portal)

**For a beginner:** Nginx is listening, but the network security group — Azure's firewall in front of the VM — still drops everything except SSH. Until a rule allows port 80, a visitor's request never reaches the VM at all, so the browser hangs and then times out. That timeout is different from a `502` or a `503`: a timeout means nothing answered, a `502` means Nginx answered but the app behind it did not, and a `503` means the app answered but its database did not.

**Where this runs:** Steps 1–2 in the Azure portal, by the owner. Steps 3–5 from the laptop's prompt.

**Interfaces:**
- Consumes: Nginx listening on `0.0.0.0:80` from Task 2.
- Produces: port 80 reachable from the internet. Session 11's Certbot HTTP-01 challenge depends on this rule existing.

- [ ] **Step 1: Confirm the current rules before changing anything**

Run from the laptop (read-only, safe for the agent):

```bash
az network nsg rule list -g rg-career-platform --nsg-name vm-career-platform-nsg --query "[].{name:name, port:destinationPortRange, source:sourceAddressPrefix, prio:priority, access:access}" -o table
```

Expected: only `Allow-SSH-Laptop` on port 22. If a `Temp-HTTP-8000` rule appears, delete it in the portal — port 8000 stays closed from here on.

- [ ] **Step 2: Add the inbound rule in the portal**

**Owner action.** Azure portal → the VM → **Networking** → **Network settings** → **Add inbound port rule**:

| Field | Value |
|---|---|
| Source | `Any` |
| Source port ranges | `*` |
| Destination | `Any` |
| Service | `Custom` |
| Destination port ranges | `80` |
| Protocol | `TCP` |
| Action | `Allow` |
| Priority | `320` |
| Name | `Allow-HTTP-80` |

Unlike the temporary port 8000 rule, this one stays. Port 80 is meant to be public, because Nginx is the program built to face the internet.

- [ ] **Step 3: Verify the rule exists**

```bash
az network nsg rule list -g rg-career-platform --nsg-name vm-career-platform-nsg --query "[].{name:name, port:destinationPortRange, source:sourceAddressPrefix, prio:priority}" -o table
```

Expected: `Allow-HTTP-80`, port `80`, source `*`, priority `320`.

- [ ] **Step 4: Verify the site answers over the public internet by IP**

This works regardless of DNS, which is why it comes before Task 4. Use lowercase `-i`, not `-I`: the app registers only `GET`, so a `HEAD` request returns `405 Method Not Allowed` with `allow: GET`. That 405 is expected and does not mean the site is down.

```bash
curl -sS -i http://4.155.216.147 | head -1
curl -sS http://4.155.216.147 | grep -ci "dhwani"
```

Expected: `HTTP/1.1 200 OK`, then a count of 1 or greater.

- [ ] **Step 5: Confirm port 8000 is closed from outside**

```bash
curl -sS -m 10 -o /dev/null -w "%{http_code}\n" http://4.155.216.147:8000 ; echo "exit=$?"
```

Expected: a timeout (non-zero exit, typically 28). A successful response means port 8000 is exposed and a rule must be removed.

**Undo Task 3:** In the portal, delete the `Allow-HTTP-80` inbound rule. The site becomes unreachable from the internet while remaining reachable from the VM via `curl http://localhost`.

---

## Task 4: Switch DNS to Cloudflare and verify (owner-executed, then verified)

**For a beginner:** Two companies do different jobs. **Namecheap is the registrar** — it records that the name is yours and tells the `.me` servers which name servers answer for it. **Cloudflare is the DNS host** — its name servers hold the actual records and answer when anyone looks the domain up. Pointing the registrar at a different DNS host is called *delegation*.

DNSSEC must be turned off at Namecheap **before** the switch. DNSSEC signs the answers for a domain so nobody can forge them. Namecheap produced those signatures; if DNSSEC stays on after Cloudflare takes over, Cloudflare's answers will not match the signatures and the domain can stop resolving entirely.

**Starting state, confirmed 2026-10-06:** the Cloudflare zone for `dhwanijain.me` exists with A records for `@` and `www` pointing at `4.155.216.147`, both set to DNS only. Namecheap's name servers are still `dns1.registrar-servers.com` / `dns2.registrar-servers.com`, and the domain currently resolves to GitHub Pages addresses (`185.199.108-111.153`) left over from an earlier setup. Only the delegation step remains.

**Where this runs:** Step 1 in Namecheap and Cloudflare, by the owner. Steps 2–5 from the laptop's prompt.

**Interfaces:**
- Consumes: the static public IP `4.155.216.147` from the VM details, and port 80 open from Task 3.
- Produces: `dhwanijain.me` and `www.dhwanijain.me` resolving to `4.155.216.147` from public resolvers. Session 11's Certbot run cannot start until this is true.

- [ ] **Step 1: Delegate the domain to Cloudflare**

**Owner action**, in this order:

1. Namecheap → **Domain List** → **Manage** next to `dhwanijain.me` → **Advanced DNS** tab → find **DNSSEC** and confirm its status switch is **off**. Turn it off if it is on.
2. Same page → **Domain** tab → **Nameservers** section → change the dropdown to **Custom DNS**.
3. Paste Cloudflare's two assigned name servers (names like `christina.ns.cloudflare.com`). Use Cloudflare's copy buttons — one wrong letter breaks the switch.
4. Click the **green checkmark** to save.
5. Cloudflare dashboard → **I updated my nameservers**. If it is still waiting, use **Check nameservers now** to force an immediate check.

Propagation takes minutes to a day. Do not wait on it — Tasks 1 through 3 and Task 5 are all independent of DNS.

- [ ] **Step 2: Verify the delegation took effect**

```bash
dig +short dhwanijain.me NS
```

Expected: two `.ns.cloudflare.com` names. If `registrar-servers.com` still comes back, the change has not spread yet or was not saved — recheck the Namecheap Nameservers section and that DNSSEC is off, then check again later.

- [ ] **Step 3: Verify the address from public resolvers**

Your own resolver may hold a cached answer, and on campus it may answer differently. Google's and Cloudflare's public resolvers are what the rest of the internet — including Let's Encrypt — sees.

```bash
dig +short @8.8.8.8 dhwanijain.me A
dig +short @1.1.1.1 dhwanijain.me A
dig +short @8.8.8.8 www.dhwanijain.me A
```

Expected: `4.155.216.147` from all three. An address starting with `104.` or `172.67.` means the Cloudflare proxy is on — set both records to DNS only (gray cloud). The GitHub Pages addresses `185.199.x.x` mean the old Namecheap records are still being served, so the delegation has not completed.

- [ ] **Step 4: Verify the site answers by name**

Run from the VM, which sits outside LMU's network, so a campus block cannot confuse the result:

```bash
ssh career-vm 'curl -sS -i http://dhwanijain.me | head -1; curl -sS http://dhwanijain.me | grep -ci "dhwani"'
```

Expected: `HTTP/1.1 200 OK` and a count of 1 or greater.

- [ ] **Step 5: Note what a campus browser shows**

On LMU Wi-Fi, `http://dhwanijain.me` will likely show a red "Web Page Blocked" malware warning. The site has no malware; LMU blocks domains it has not reviewed, and this one is days old. Review takes days to weeks. Confirm the site genuinely works by loading it on a phone with Wi-Fi off, or over a phone hotspot. Record which method was used.

**Undo Task 4:** In Namecheap, set the Nameservers dropdown back to **Namecheap BasicDNS**. The old host records, including the GitHub Pages A records, resume answering within the propagation window.

---

## Task 5: Prove the site survives a restart (owner-executed, then verified)

**For a beginner:** This is the test the previous setup failed. Before, the app ran only because someone started it by hand; a restart ended it for good. Now systemd starts it at boot. `Restart=on-failure` is a separate setting that brings it back after a crash — starting at boot and restarting after a crash are two different things, and this task proves the first one.

**Where this runs:** Step 1 in the Azure portal, by the owner. Steps 2–4 from the laptop over SSH.

**Interfaces:**
- Consumes: the `enabled` service from Task 1 and Nginx from Task 2.
- Produces: evidence that boot time and service start time match, which is the proof that nobody started the app by hand.

- [ ] **Step 1: Restart the VM**

**Owner action.** Azure portal → the VM → **Overview** → **Restart**. Use **Restart**, not **Stop** — Restart reboots Ubuntu while keeping the VM allocated. Wait until the status reads **Running**.

- [ ] **Step 2: Confirm the site came back with nobody logged in**

Give it a minute if it is slow to come up.

```bash
curl -sS -i http://4.155.216.147 | head -1
curl -sS http://4.155.216.147 | grep -ci "dhwani"
```

Expected: `HTTP/1.1 200 OK` and a count of 1 or greater.

- [ ] **Step 3: Capture boot time against service start time**

```bash
ssh career-vm 'echo "=== last boot ==="; uptime -s; echo "=== service active since ==="; systemctl show career-platform -p ActiveEnterTimestamp --value; echo "=== nginx active since ==="; systemctl show nginx -p ActiveEnterTimestamp --value; echo "=== both enabled? ==="; systemctl is-enabled career-platform nginx'
```

Expected: the service timestamp is within roughly a minute of the boot timestamp, and both services report `enabled`. A service start time much later than boot would suggest someone started it manually.

- [ ] **Step 4: Record the results under this task**

Paste the Step 2 and Step 3 output into the Execution Log at the bottom of this plan, under a `Task 5` heading. This output is the Project 1 restart-verification evidence referenced by the Session 11 handout.

**Undo Task 5:** Nothing to undo — this task only observes. The restart is non-destructive.

---

## Task 6: Record the network setup and publish the plan

**For a beginner:** A project needs its network setup explained, not just working. This task writes down every open port and why it is open, then removes anything that should not be public before the file goes to GitHub.

**Files:**
- Modify: `docs/superpowers/plans/2026-10-01-operate-the-vm.md` (this file — the Record section below)

**Where this runs:** Data gathering over SSH and via `az`; editing and committing on the laptop.

**Interfaces:**
- Consumes: the completed state from Tasks 1 through 5.
- Produces: a committed, redacted plan file on GitHub, which the Session 11 handout reads for VM details.

- [ ] **Step 1: Gather every listening port**

```bash
ssh career-vm 'sudo ss -ltnp'
```

Expected: `0.0.0.0:22` (sshd), `0.0.0.0:80` (nginx), `127.0.0.1:8000` (uvicorn), plus `127.0.0.53:53` (Ubuntu's local DNS helper) and matching IPv6 lines. There must be no `0.0.0.0:8000`.

- [ ] **Step 2: Gather both IP addresses**

```bash
ssh career-vm 'hostname -I'
az network public-ip list -g rg-career-platform --query "[].{name:name, ip:ipAddress, alloc:publicIPAllocationMethod}" -o table
```

Note that the public IP appears nowhere on the VM. Azure holds the public address and forwards traffic to the private one, which is why `hostname -I` shows only `172.16.0.4`.

- [ ] **Step 3: Gather the NSG rules**

```bash
az network nsg rule list -g rg-career-platform --nsg-name vm-career-platform-nsg --query "[].{name:name, port:destinationPortRange, source:sourceAddressPrefix, prio:priority, access:access}" -o table
```

- [ ] **Step 4: Fill in the Record section**

Write the gathered output into the **Record** section below, replacing its placeholder note. Give each NSG rule a one-line reason it exists.

- [ ] **Step 5: Redact before committing**

This repository is public. Replace the laptop's public IP with `<LAPTOP_IP>` and the Azure subscription ID with `<PERSONAL_SUBSCRIPTION_ID>` everywhere in this file, then confirm:

```bash
cd /Users/dhwanijain/isba-4775/career-platform
LAPTOP_IP=$(curl -4 -s https://api.ipify.org)
SUB_ID=$(az account show --query id -o tsv)
grep -nE "$LAPTOP_IP|$SUB_ID" docs/superpowers/plans/2026-10-01-operate-the-vm.md || echo "CLEAN - no laptop IP or subscription ID"
```

Expected: `CLEAN`.

The VM's public IP `4.155.216.147` is deliberately **not** redacted. Public DNS now publishes it to anyone who looks up `dhwanijain.me`, so hiding it in this file would protect nothing while making the plan harder to follow. The laptop IP and subscription ID are different — neither is published anywhere, and both identify things beyond this one server.

- [ ] **Step 6: Commit and push**

```bash
cd /Users/dhwanijain/isba-4775/career-platform
git add docs/superpowers/plans/2026-10-01-operate-the-vm.md
git commit -m "docs: add operate-the-vm plan with network record"
git push origin main
```

- [ ] **Step 7: Verify it reached GitHub**

A commit saves it on the laptop; the push is what sends it to GitHub. Open `https://github.com/djain2905/career-platform/blob/main/docs/superpowers/plans/2026-10-01-operate-the-vm.md` and confirm the Record section and the Execution Log are visible.

**Undo Task 6:** `git revert` the commit and push, or `git rm` the file if it should not exist at all.

---

## Redacted Values

Recover the real values locally:

| Placeholder | How to get it |
|---|---|
| `<LAPTOP_IP>` | `curl -4 -s https://api.ipify.org` (dynamic — re-check every session) |
| `<PERSONAL_SUBSCRIPTION_ID>` | `az account list --all -o table` |

`ssh career-vm` works without any of these — `~/.ssh/config` holds the host and key.

---

## Record

Captured 2026-10-07, after HTTPS was added.

### Listening ports (`sudo ss -ltnp`)

| Address:Port | Program | Reachable from |
|---|---|---|
| `0.0.0.0:22` | `sshd` | internet, but NSG restricts the source to one laptop IP |
| `0.0.0.0:80` | `nginx` | internet — redirects every request to HTTPS |
| `0.0.0.0:443` | `nginx` | internet — serves the site over TLS |
| `127.0.0.1:8000` | `uvicorn` (1 main + 2 workers) | **the VM only** — loopback, unreachable from outside |
| `127.0.0.53:53`, `127.0.0.54:53` | `systemd-resolve` | the VM only — Ubuntu's local DNS stub |

Each service also has a matching IPv6 (`[::]`) line. Uvicorn is the exception that
matters: it binds loopback only, so no visitor can bypass Nginx and reach the app directly.

### Addresses

| Kind | Value | Note |
|---|---|---|
| Public IP | `4.155.216.147` | Standard SKU, **Static**. Held by Azure, not configured on the VM |
| Private IP | `172.16.0.4` | The only address the VM knows about itself |

The public IP appears nowhere on the VM. Azure holds it and forwards traffic to the
private address, which is why `hostname -I` returns only `172.16.0.4`.

### NSG inbound rules (`vm-career-platform-nsg`)

| Priority | Name | Port | Source | Why it exists |
|---|---|---|---|---|
| 300 | `Allow-SSH-Laptop` | 22 | `<LAPTOP_IP>` | Administration. Pinned to one address so the rest of the internet cannot reach SSH at all |
| 320 | `Allow-HTTP-800` | 80 | `*` | Public web traffic. Required by Let's Encrypt's HTTP-01 challenge, which fetches a token over port 80 to prove domain control. Now also serves the 301 redirect to HTTPS |
| 330 | `Allow-HTTPS-443` | 443 | `*` | Public web traffic over TLS. This is where visitors actually read the site |

Port 8000 has **no** rule and is never opened. The `Temp-HTTP-8000` rule from the
2026-09-24 migration was deleted before this work began.

The rule at priority 320 is named `Allow-HTTP-800`, not `Allow-HTTP-80`. The trailing
digit is a typo in the name only — its destination port is `80` and it behaves correctly.
Azure cannot rename a rule in place, so correcting it means deleting and recreating it,
which would briefly take the site offline.

### TLS

| Property | Value |
|---|---|
| Issuer | Let's Encrypt (intermediate `YE2`, root `ISRG Root X2`) |
| Names covered | `dhwanijain.me`, `www.dhwanijain.me` |
| Key type | ECDSA |
| Valid | 2026-10-06 21:03:37 UTC → 2027-01-04 21:03:36 UTC (90 days) |
| Renewal | `certbot.timer` (enabled), next run 2026-10-08 04:19 UTC |
| Renewal tested | `sudo certbot renew --dry-run` → *"all simulated renewals succeeded"* |

---

## Execution Log

Updated as sections complete. Newest last.

### 2026-10-06 — Task 1 (Uvicorn on loopback, two workers) — COMPLETE

| Step | Check | Result |
|---|---|---|
| 1 | Backup created | `/home/azureuser/career-platform.service.bak` (318 bytes) |
| 2 | Listening before | `0.0.0.0:8000` (pid 931) |
| 5 | `systemctl is-active` | `active` |
| 6 | Listening after | `127.0.0.1:8000` — no `0.0.0.0:8000` present |
| 7 | `systemctl is-enabled` | `enabled` |
| 8 | Real data served | count `8` (demo profile would give `0`) |
| 9 | Worker processes | Main PID `2086`; workers `2089`, `2090`; `resource_tracker` helper `2088` |

Step 9's original `Expected:` was wrong and has been corrected in place. `ps -ef | grep uvicorn`
returns only one line, because Uvicorn starts workers through Python's `multiprocessing` and a
worker's command line reads `spawn_main` rather than `uvicorn`. The workers were confirmed
through systemd's cgroup tree instead, which lists all four processes under the service.

### 2026-10-06 — Task 2 (Nginx front door) — COMPLETE

| Step | Check | Result |
|---|---|---|
| 1 | Install | `nginx/1.24.0 (Ubuntu)` |
| 2 | Service up | `active`, default page `HTTP/1.1 200 OK` |
| 3 | Site file written | `/etc/nginx/sites-available/career-platform`, `server_name dhwanijain.me www.dhwanijain.me` |
| 4 | Enabled / default removed | `sites-enabled/` contains only `career-platform` |
| 5 | `nginx -t` | `syntax is ok`, `test is successful` |
| 6 | Content through Nginx | `200`, count `8` |
| 7 | Responding program | `Server: nginx/1.24.0 (Ubuntu)` |
| 8 | Listening ports | `0.0.0.0:80` (nginx), `127.0.0.1:8000` (uvicorn) — no `0.0.0.0:8000` |
| — | `Host: dhwanijain.me` match | `200`, confirming the named server block answers |

The site is fully assembled on the VM. It is not yet reachable from the internet: the NSG has no
port 80 rule (Task 3, owner-executed), and public DNS still resolves `dhwanijain.me` to the old
GitHub Pages addresses while the Cloudflare delegation propagates (Task 4).

### 2026-10-06 — Tasks 3 & 4 (port 80, DNS) — COMPLETE

| Check | Result |
|---|---|
| NSG rule added (owner, portal) | `Allow-HTTP-800`, port `80`, source `*`, priority `320` |
| `http://4.155.216.147` | `200`, content count `8` |
| `http://4.155.216.147:8000` | timed out — port 8000 correctly closed |
| `.me` registry delegation | `anna.ns.cloudflare.com`, `finley.ns.cloudflare.com` |
| `1.1.1.1` / `9.9.9.9` | `4.155.216.147` |
| `8.8.8.8` | still cached at GitHub Pages, 1800s TTL remaining |
| `http://dhwanijain.me` from the VM | `200` |
| `http://www.dhwanijain.me` from the VM | `200` |
| From laptop on campus Wi-Fi | `503` — LMU's "Web Page Blocked" filter, not a site fault |

The delegation reached the registry within about a minute of the Namecheap save, far faster than
the 48 hours Namecheap quotes as a worst case. Verification was done against the `.me` registry
servers directly, because public resolvers cache the previous answer and would have reported
stale data for up to an hour afterward.

Two deviations from the plan, both benign. The NSG rule was named `Allow-HTTP-800` rather than
`Allow-HTTP-80`; the destination port is correctly `80`, so behavior is unaffected, but the name
does not match this plan or the handout. An `Allow-HTTPS-443` rule (port `443`, priority `330`)
was also added in the same portal visit — that belongs to the HTTPS work, not this plan, and is
recorded here only because it is present in the NSG.
