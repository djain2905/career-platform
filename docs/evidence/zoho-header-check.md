# Zoho header check — dhwanijain.me

**Message analyzed:** my reply "Re: Test 01: inbound", sent from my `@dhwanijain.me` address in
Zoho webmail on 2026-10-19 at 21:06 PDT, received by my LMU Outlook (Microsoft 365) mailbox.
**Headers viewed:** 2026-10-19, in Outlook's message source. Addresses removed; domain-level
results unchanged. The same excerpt is in [ex06.md](ex06.md#2-spf-dkim-and-dmarc).
**DNS records checked:** 2026-10-21 (see [project-1-final-checks.md](project-1-final-checks.md#1-dns--what-the-public-sees)).

## The headers

```text
Authentication-Results: mx.microsoft.com 1; spf=pass (sender IP is
 165.173.180.52) smtp.mailfrom=dhwanijain.me; dkim=pass (signature was
 verified) header.d=dhwanijain.me;dmarc=pass action=none
 header.from=dhwanijain.me;compauth=pass reason=100
Received-SPF: Pass (protection.outlook.com: domain of dhwanijain.me designates
 165.173.180.52 as permitted sender) receiver=protection.outlook.com;
 client-ip=165.173.180.52; helo=sender6-of-o52.zoho.com; pr=C
ARC-Authentication-Results: i=2; mx.microsoft.com 1; spf=pass ... dmarc=pass
 (p=none sp=none pct=100) action=none header.from=dhwanijain.me;
 dkim=pass (signature was verified) header.d=dhwanijain.me; arc=pass
```

## What each check means and which DNS record it used

| Check | Header result | DNS record the receiver looked up | What it proves |
|---|---|---|---|
| **SPF** | `spf=pass`, sender IP `165.173.180.52`, HELO `sender6-of-o52.zoho.com` | `dhwanijain.me TXT "v=spf1 include:zohomail.com ~all"` | The server that delivered the message is on the list of servers my domain allows to send. `include:zohomail.com` pulls in Zoho's list. |
| **DKIM** | `dkim=pass`, `header.d=dhwanijain.me` | `zmail._domainkey.dhwanijain.me TXT "v=DKIM1; k=rsa; p=…"` | Zoho signed the message with my domain's private key, the public key in my DNS verified it, and the signed parts weren't changed on the way. |
| **DMARC** | `dmarc=pass`, `p=none` | `_dmarc.dhwanijain.me TXT "v=DMARC1; p=none; rua=mailto:dhwani@dhwanijain.me"` | The visible From domain (`dhwanijain.me`) matches the domain SPF and DKIM passed for. `p=none` tells receivers to deliver even if it failed, and send reports. |
| **compauth** | `pass` | — | Microsoft's own overall verdict, combining the above. |

**MX** isn't in these headers because it's used for mail coming *to* me. It's checked by DNS:
`dhwanijain.me MX 10 mx.zoho.com, 20 mx2.zoho.com, 50 mx3.zoho.com`. Test 01 (2026-10-13, from
my LMU Outlook to my domain address) arrived in the Zoho inbox, which shows senders found Zoho
through those records. See [ex06.md](ex06.md#1-email-tests).

## Earlier result that differed

Test 02 (2026-10-13, a new message from my domain address) showed SPF and DKIM passing but
`dmarc=bestguesspass`. That's Microsoft's result when a domain has **no** DMARC record. The DMARC
record was published after that test; the 2026-10-19 reply shows `dmarc=pass (p=none)`.

## Open items

- DMARC is still `p=none`, so a receiver won't reject mail that fails. The next step is
  `p=quarantine` once the aggregate reports show only Zoho sending for the domain.
- Whether DMARC aggregate reports have arrived at the `rua` address isn't recorded here.
