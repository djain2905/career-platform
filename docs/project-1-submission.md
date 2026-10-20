# Project 1 Submission — Career Platform

**Repository:** https://github.com/djain2905/career-platform
**Live site:** https://dhwanijain.me/
**Privacy page:** https://dhwanijain.me/privacy

## Evidence

### Domain email and Google Analytics (Exercise 06)

[docs/evidence/ex06.md](evidence/ex06.md), checked 2026-10-19 (Pacific):

- **Deployed tag:** the Google tag (`G-V64QT2T9EG`) is in the shared template
  `app/templates/base.html`, so it loads once on every page. The live page
  source of `/` and `/privacy` showed exactly one tag with that ID.
- **Observed `page_view`:** GA4 Realtime showed `page_view` after I loaded
  the live site in my own browser.
- **Observed outbound click:** after one click on the GitHub link, Realtime
  showed `click` with `link_url` = `https://github.com/djain2905`,
  `link_domain` = `github.com` and `outbound` = `true`.
- **Interpretation:** the outbound click shows that a visitor clicked the link
  to my GitHub, which tells me which outside profiles people are drawn to. GA4
  records the click, not whether the GitHub page loaded. It can't tell
  me who the visitor was or why they clicked: a recruiter, a classmate and an
  accidental click all look the same.
- **Email:** Zoho Mail at `dhwanijain.me` received, replied and sent; SPF, DKIM
  and DMARC passed in the outside mailbox.
