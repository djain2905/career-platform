# Impeccable design activity

**Date:** 2026-10-07
**Target:** `app/templates/index.html` (the public resume page)
**Live site:** <https://dhwanijain.me>

## What I ran

I installed the Impeccable plugin and ran `/impeccable critique` against the resume page. The
command runs two assessments that are kept isolated from each other on purpose: a design review
that forms its judgment from the source and the live page, and a deterministic detector that
scans the markup and then re-scans the rendered DOM in a browser. They stay separate so the
detector's findings can't anchor the human-style review.

The browser pass couldn't reach <https://dhwanijain.me> from campus WiFi — LMU's filter resets
the TLS connection — so it fell back to running the app on localhost and injecting the detector
there. That turned out to matter. The static scan of the template only found 2 issues, because
it sees `{{ data.profile.full_name }}` instead of real text. The rendered page produced 11, since
rules that measure actual line lengths and repeated elements only work once real data is in.

Full critique snapshot: `.impeccable/critique/2026-10-06T22-28-00Z__app-templates-index-html.md`

## What it found

The page scored **18/32** on Nielsen's heuristics (two were marked not applicable: error
prevention, since the page has no inputs, and help and documentation, since a one-page resume has
no features to learn). The verdict on design specificity was blunt: any ISBA student could swap
their name in and ship the page unchanged.

The findings I acted on:

| Issue | Why it mattered |
|---|---|
| A project bullet was duplicated verbatim across two unrelated projects | The L'Oréal pipeline bullet also appeared under the LMU Datathon, which analyzed EMT meal break regulations. On the one page whose whole claim is analytical precision, a visible copy-paste error undercuts every number on it. |
| No focus styles at all | All 215 lines of CSS had no `:focus` or `outline` rule, so keyboard users got only the browser default ring. |
| Anchor links scrolled targets under the sticky nav | No `scroll-padding-top` anywhere, so clicking "Experience" hid the heading you just asked for. |
| Awards weren't headings | Awards used `<strong>` instead of `<h3>`, so a screen reader navigating by heading couldn't reach "1st Place - LMU Datathon". |
| Inverted type hierarchy | `h2` was 12.8px while body copy was 15.04px, making section labels the smallest type on the page. |
| `.tag` failed WCAG AA | 4.27:1 against its background, below the 4.5:1 threshold and too small to qualify for the large-text exemption. |
| Tap targets under 44px | Nav links were ~22px tall, half the minimum, on a page recruiters screen from phones. |

## What I changed

Commit `a987583`. Content fix: removed the duplicated bullet, so the Datathon now describes only
work that was actually part of it. Accessibility: added `:focus-visible` styling, `scroll-padding-top`
and `scroll-margin-top`, a skip link, `aria-labelledby` on sections, award titles as `h3`, 44px tap
targets, and an `aria-current` scroll-spy so the nav reports where the reader is. Type and contrast:
`.tag` went from 4.27:1 to 6.09:1, `h2` is now larger than body copy, body is 16px, and prose is
capped at 68ch to fix the 94-105 character lines the detector measured. I also removed the location
eyebrow above my name, and added a dark color scheme, print styles and JSON-LD markup.

Every change was verified on the live site after deploying.

## What I left undone, and why

Four findings need content I'd have to write rather than code I could fix:

- The Datathon needs a real methodology bullet where the duplicated one was removed.
- `person_profile.summary` is still null, so the positioning line in the hero renders nothing.
- There's no resume PDF, which the critique called the recruiter's most-used accelerator.
- No project screenshots and no `og:image`, so the link still previews blank on LinkedIn.

## One thing worth knowing about the detector

After my changes the CLI detector reports 35 findings, up from 2. These are false positives. The
static scanner doesn't respect `@media (prefers-color-scheme: dark)` scoping, so it pairs my
dark-mode colors against light-mode backgrounds — combinations like `#9fb0c4 on #ffffff` that never
appear together on a real page. I computed every genuine pair in both schemes by hand and they all
pass AA. The "line-height 0.13x" findings are a parsing artifact too; nothing in the stylesheet is
below 1.1.

The lesson I took from that: a deterministic tool is useful precisely because it doesn't have
opinions, but it still needs someone who understands the code to tell a real finding from an
artifact of how it parses.
