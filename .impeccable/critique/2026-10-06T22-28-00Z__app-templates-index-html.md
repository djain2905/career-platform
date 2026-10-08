---
target: app/templates/index.html
total_score: 18
max_score: 32
na_heuristics: 5,10
p0_count: 0
p1_count: 4
target_identity: "file:/Users/dhwanijain/isba-4775/career-platform/app/templates/index.html"
target_fingerprint: "sha256:2beb81aeee8b6469b8b0283929b02c3077763cf218661a717c5d2c0ad9b8666b"
target_path: /Users/dhwanijain/isba-4775/career-platform/app/templates/index.html
timestamp: 2026-10-06T22-28-00Z
slug: app-templates-index-html
---
**Method: dual-agent** (A: design review, unanchored · B: detector + browser evidence, isolated)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 1 | No aria-current, no scroll-spy, zero :focus rules in 215 lines of CSS |
| 2 | Match System / Real World | 3 | Experience breaks reverse-chronology; unglossed jargon |
| 3 | User Control and Freedom | 3 | No skip link past 8 targets; no back-to-top |
| 4 | Consistency and Standards | 3 | Nav "Awards" vs heading "Awards & Leadership"; rel= on hero links only |
| 5 | Error Prevention | n/a | Read-only page, no inputs |
| 6 | Recognition Rather Than Recall | 3 | "Expected May 2027" four screens down |
| 7 | Flexibility and Efficiency | 1 | No resume PDF. No @media print. No per-project links despite slug |
| 8 | Aesthetic and Minimalist Design | 2 | Inverted hierarchy: h2 12.8px vs .bullets li 15.04px |
| 9 | Error Recovery | 2 | MINIMAL path renders empty <main> while cache-note says "some sections" |
| 10 | Help and Documentation | n/a | Single-page resume |
| **Total** | | **18/32** | **Acceptable** |

## Design Specificity Verdict

Any ISBA student could swap in their own name and ship this unchanged. #2563eb is Tailwind blue-600;
font stack is system default; four unreconciled corner radii; one component renders Experience,
Projects and Education at identical weight.

Deterministic scan: CLI (static template) = 2 findings. Browser (rendered page) = 11-12:
8x line-length (94-105 chars, target <80), 2x low-contrast (span.tag, 4.3:1 vs AA 4.5:1),
1x hero-eyebrow-chip, 1x kicker-above-heading. Console header said 11 while listing 12.

Agreement: design review independently computed 4.27:1 on .tag and independently criticized the
eyebrow chip. Detector won on line-length, which the review only treated qualitatively.

Overlays: injection succeeded during the run; servers stopped and tab closed per cleanup. No
overlay currently visible.

## Overall Impression

Writing is excellent, engineering is sophisticated, design is coasting on both. Biggest
opportunity: a data-analytics portfolio that visualizes nothing. Zero <img> in template, zero
raster assets in app/static/ (verified).

## What's Working

1. Degraded-read architecture — load_profile() returns identical dict shape from live SQLite,
   snapshot JSON and MINIMAL, so the template never branches on provenance.
2. PRIVATE_CONTACT_TYPES filtered at one chokepoint (repository.py:25) before the snapshot write.
3. Nav mirrors section conditions link-for-link; nav can never advertise a section that doesn't render.

## Priority Issues

No P0.

[P1] Duplicate project bullet (VERIFIED in data/snapshot.json). "Automated weekly data pipelines
via GitHub Actions and built an LLM-queryable brand knowledge base from 19 scraped sources."
appears under BOTH L'Oreal/Lancome AND LMU Datathon. Fix: delete from Datathon, replace with real
methodology bullet. -> /impeccable clarify

[P1] No primary action, no resume PDF. Three identical contact pills; no PDF in project; no
availability/graduation above fold; p.summary is null so positioning slot renders empty.
-> /impeccable shape

[P1] Anchor nav scrolls targets under the sticky nav. No scroll-padding-top or scroll-margin-top
anywhere (verified count 0). Zero focus styles. -> /impeccable harden

[P1] Projects section has no artifacts. Two of three projects have repo_url AND external_url null.
Zero images. "Featured" tag asserts a sort/filter system that doesn't exist. -> /impeccable layout

[P2] Inverted type hierarchy + WCAG failure. h2 12.8px < .bullets li 15.04px (verified).
.tag fails AA at 4.3:1. -> /impeccable typeset

## Persona Red Flags

Riley (stress tester): duplicated bullet; rel="noopener noreferrer" on hero links but not footer;
Experience ordered by order_index not date; "Leading research" present tense under closed range.

Sam (accessibility): zero :focus/outline declarations in 215 lines; Awards abandons article.entry
+ h3 for ul.awards + <strong> so heading navigation can't reach any award; no prefers-color-scheme.

Casey (mobile): .sticky-nav a has zero padding -> ~22px tap target vs 44px minimum, 20px apart;
contact links only in hero, decision moment is six screens down at Awards.

## Minor Observations

- og:image, og:url, canonical, favicon all absent; LinkedIn preview renders blank
- No JSON-LD Person markup despite structured data
- "JSON" listed as peer skill to Docker and dbt
- Awards restates Projects verbatim
- Two awards have description: null and are the last content on the page
- education[0].description is 8 course names in one unpunctuated run-on
- No @media print
- role="status" on static first-paint content
