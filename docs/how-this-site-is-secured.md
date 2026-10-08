# How this site is secured

My resume site runs at <https://dhwanijain.me> on an Azure VM. This file explains how the
connection between a visitor and my server gets encrypted, and how somebody can check that
themselves.

## The certificate

**Who issued it.** Let's Encrypt, a free certificate authority. A certificate authority, or CA,
is a third party that browsers already trust. My server can't vouch for itself, because an
imposter would say exactly the same thing. So Let's Encrypt checked that I actually control my
domain, and then signed my certificate.

Mine was signed by their intermediate CA `YE2`, which chains up to the root `ISRG Root X2`. That
root already ships inside Chrome and macOS, which is why visitors get a padlock instead of a
warning.

**What it covers.** Two names: `dhwanijain.me` and `www.dhwanijain.me`. Both show up in the
certificate's Subject Alternative Name field. That field is the one that matters, because the
`subject` line only lists the first name. If I only looked at `subject` I'd have no proof the
`www` version was covered at all.

**When it expires.** October 6, 2026 to January 4, 2027. Let's Encrypt keeps certificates short
on purpose. If my private key ever got stolen it stops being useful fast, and a short lifetime
forces renewal to be automatic instead of something I forget about.

## How renewal works

Certbot set up a systemd timer called `certbot.timer`. It wakes up twice a day and runs
`certbot renew`, which looks at every certificate on the machine and does nothing unless one is
within 30 days of expiring. So nothing actually happens until early December. When it does, the
certificate renews and Nginx reloads without me logging in at all.

I checked this two ways, because they prove two different things.

**The timer is scheduled.**

```
timer enabled: enabled
NEXT: Thu 2026-10-08 04:19:18 UTC    LAST: Wed 2026-10-07 15:00:38 UTC
```

That tells me renewal will run, even after a reboot. It doesn't tell me it would work.

**The dry run works.**

```
$ sudo certbot renew --dry-run

Simulating renewal of an existing certificate for dhwanijain.me and www.dhwanijain.me
Congratulations, all simulated renewals succeeded:
  /etc/letsencrypt/live/dhwanijain.me/fullchain.pem (success)
```

The dry run goes through the whole process against Let's Encrypt's staging server. It uses the
real challenge, the real Nginx plugin and the real file paths, but it doesn't save anything and
doesn't count against the five certificates a week I'm allowed for this domain. Put together,
the timer says renewal will fire and the dry run says it'll succeed when it does.

## Which ports are open, and to who

| Port | Open to | Why it's open |
|---|---|---|
| 22 (SSH) | Only my laptop | This is how I administer the VM. The NSG rule is a single `/32` pinned to my laptop's public address, so everyone else gets dropped before they ever reach the machine. Password login is off too, so only my ed25519 key works. |
| 80 (HTTP) | Anyone | Let's Encrypt's HTTP-01 challenge grabs a token over port 80 to prove I control the domain, so I can't close this and still have certificates. It also serves the 301 that sends every visitor to HTTPS. |
| 443 (HTTPS) | Anyone | This is where people actually read the site, encrypted. |
| 8000 | Nobody | Uvicorn listens on `127.0.0.1:8000`. That's the loopback address, so it only takes connections from the VM itself. There's no firewall rule for 8000 and there doesn't need to be. |

Two separate things have to be gotten past for SSH, not one: the NSG rule and the key.

**What it costs.** My laptop's address comes from whatever network I'm on, so it changes, and I
have to re-point that rule every time it does. The tempting shortcut is opening the source to
`0.0.0.0/0` so it works from anywhere, but that hands port 22 to the whole internet. I'd rather
re-point a rule.

## Where encryption starts and ends

It **starts** in the visitor's browser, the moment it opens the TLS connection. It **ends** at
Nginx on my VM, which holds the private key and does the decrypting. That's called TLS
termination.

Nginx then hands the decrypted request to Uvicorn at `127.0.0.1:8000` over plain HTTP. That
sounds like a hole but it isn't one. `127.0.0.1` is the loopback interface, which the operating
system handles internally, so that traffic never touches a network card or a cable or a router.
There's no wire for anyone to tap. Encrypting it would mean another key to manage, to defend
against an attacker who'd already be inside the machine and could just read the app's memory.

Two limits I think are worth being upfront about.

**The domain name isn't encrypted.** During the handshake the browser sends the site's name in
the clear so the server knows which certificate to hand back. Somebody watching the network can
see a visitor went to `dhwanijain.me`. They can't see which page, what got typed, or what came
back.

**The private key never leaves the VM.** It lives at
`/etc/letsencrypt/live/dhwanijain.me/privkey.pem` and only root can read it. Anyone who copied it
could pretend to be my site, which is the same reason my SSH private key never leaves my laptop.
The direction flips between the two though. With SSH my laptop proves who it is to the server.
With HTTPS the server proves who it is to every visitor.

## How a customer can check this themselves

1. Open <https://dhwanijain.me>
2. Click the icon just to the left of the domain in the address bar
3. Click **Connection is secure**
4. Click **Certificate is valid** to open the certificate viewer
5. Read **Issued to**, **Issued by**, and the dates, and compare them to the output below

The nice part is that a customer never has to trust me. They're trusting a certificate authority
their browser already shipped with, and that CA checked I control the domain before it signed
anything.

## Evidence

```
$ openssl s_client -connect dhwanijain.me:443 -servername dhwanijain.me </dev/null 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates

subject=CN = dhwanijain.me
issuer=C = US, O = Let's Encrypt, CN = YE2
notBefore=Oct  6 21:03:37 2026 GMT
notAfter=Jan  4 21:03:36 2027 GMT
```

And the Subject Alternative Name extension, which is the part that proves both names are covered:

```
$ openssl s_client -connect dhwanijain.me:443 -servername dhwanijain.me </dev/null 2>/dev/null \
    | openssl x509 -noout -ext subjectAltName

X509v3 Subject Alternative Name:
    DNS:dhwanijain.me, DNS:www.dhwanijain.me
```
