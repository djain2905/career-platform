# DNS Records Before Zoho Mail Setup

**Date:** 2026-10-13
**Captured:** 2026-10-13 21:11 UTC
**Zone:** `dhwanijain.me` (Cloudflare)
**Records:** 9

Snapshot of every DNS record in the zone before changing anything for Zoho
Mail. If the email setup goes wrong, these are the values to restore.

## How it was captured

```sh
cf dns records list --zone dhwanijain.me
```

## Records

| Type | Name | Content | Priority | TTL | Proxy | Record ID |
|---|---|---|---|---|---|---|
| A | `www.dhwanijain.me` | `4.155.216.147` | — | auto | DNS only | `adc1fa81099c918c5ac8eee0deacbdb7` |
| CNAME | `dhwanijain.me` | `8udvcs1q.up.railway.app` | — | auto | DNS only | `dceca0a113293b548c0ac03a9bc033e5` |
| MX | `dhwanijain.me` | `eforward5.registrar-servers.com` | 20 | auto | DNS only | `0b0b48d3aed7aae66c36fb1cd42a6a77` |
| MX | `dhwanijain.me` | `eforward4.registrar-servers.com` | 15 | auto | DNS only | `d7af7a31a792772687994969c11ac128` |
| MX | `dhwanijain.me` | `eforward3.registrar-servers.com` | 10 | auto | DNS only | `e807d16b26c708e3e17f05dfb2002b39` |
| MX | `dhwanijain.me` | `eforward2.registrar-servers.com` | 10 | auto | DNS only | `641fe0c892ac0356644249483ccb3763` |
| MX | `dhwanijain.me` | `eforward1.registrar-servers.com` | 10 | auto | DNS only | `7dc403e8f2f2387e2e6244ded0699fc0` |
| TXT | `dhwanijain.me` | `"v=spf1 include:spf.efwd.registrar-servers.com ~all"` | — | auto | DNS only | `bdf5561022d4fcd220d23b6228956c9f` |
| TXT | `_railway-verify.dhwanijain.me` | `"railway-verify=357bd6479608dfcec11128f1b871667ec0f3ba33aba819f782a45efa437bc9af"` | — | auto | DNS only | `56737696b9c3cb2834854d8fd903c6df` |

## Raw output

```json
[
  {
    "id": "adc1fa81099c918c5ac8eee0deacbdb7",
    "name": "www.dhwanijain.me",
    "type": "A",
    "content": "4.155.216.147",
    "proxiable": true,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:51:47.32697Z",
    "modified_on": "2026-10-06T20:51:47.32697Z"
  },
  {
    "id": "dceca0a113293b548c0ac03a9bc033e5",
    "name": "dhwanijain.me",
    "type": "CNAME",
    "content": "8udvcs1q.up.railway.app",
    "proxiable": true,
    "proxied": false,
    "ttl": 1,
    "settings": {
      "flatten_cname": false
    },
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-08T22:18:55.448815Z",
    "modified_on": "2026-10-08T22:18:55.448815Z"
  },
  {
    "id": "0b0b48d3aed7aae66c36fb1cd42a6a77",
    "name": "dhwanijain.me",
    "type": "MX",
    "content": "eforward5.registrar-servers.com",
    "priority": 20,
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.099067Z",
    "modified_on": "2026-10-06T20:50:24.099067Z"
  },
  {
    "id": "d7af7a31a792772687994969c11ac128",
    "name": "dhwanijain.me",
    "type": "MX",
    "content": "eforward4.registrar-servers.com",
    "priority": 15,
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.089175Z",
    "modified_on": "2026-10-06T20:50:24.089175Z"
  },
  {
    "id": "e807d16b26c708e3e17f05dfb2002b39",
    "name": "dhwanijain.me",
    "type": "MX",
    "content": "eforward3.registrar-servers.com",
    "priority": 10,
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.079763Z",
    "modified_on": "2026-10-06T20:50:24.079763Z"
  },
  {
    "id": "641fe0c892ac0356644249483ccb3763",
    "name": "dhwanijain.me",
    "type": "MX",
    "content": "eforward2.registrar-servers.com",
    "priority": 10,
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.071052Z",
    "modified_on": "2026-10-06T20:50:24.071052Z"
  },
  {
    "id": "7dc403e8f2f2387e2e6244ded0699fc0",
    "name": "dhwanijain.me",
    "type": "MX",
    "content": "eforward1.registrar-servers.com",
    "priority": 10,
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.060541Z",
    "modified_on": "2026-10-06T20:50:24.060541Z"
  },
  {
    "id": "bdf5561022d4fcd220d23b6228956c9f",
    "name": "dhwanijain.me",
    "type": "TXT",
    "content": "\"v=spf1 include:spf.efwd.registrar-servers.com ~all\"",
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-06T20:50:24.108704Z",
    "modified_on": "2026-10-06T20:50:24.108704Z"
  },
  {
    "id": "56737696b9c3cb2834854d8fd903c6df",
    "name": "_railway-verify.dhwanijain.me",
    "type": "TXT",
    "content": "\"railway-verify=357bd6479608dfcec11128f1b871667ec0f3ba33aba819f782a45efa437bc9af\"",
    "proxiable": false,
    "proxied": false,
    "ttl": 1,
    "settings": {},
    "meta": {},
    "comment": null,
    "tags": [],
    "created_on": "2026-10-08T22:20:06.207345Z",
    "modified_on": "2026-10-08T22:20:06.207345Z"
  }
]
```
