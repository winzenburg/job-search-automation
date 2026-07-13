# Applications Log

_Last updated: 2026-07-13 16:40 UTC_

**Total applications:** 6  
**Submitted:** 0  
**Needs manual apply (no automation for this source):** 1  
**Failed (needs review):** 5  
**Materials ready, not yet attempted:** 0

---

## Needs Manual Apply

_These came from a job board listing rather than a direct application link, so auto-submit couldn't handle them. Apply manually via the link._

- **[INNERGY](https://remoteOK.com/remote-jobs/remote-director-of-customer-success-innergy-1134738)** — Director of Customer Success  
  Source:  | Generated: 2026-07-13
  Resume: `Resume_INNERGY.pdf`

## Failed (Needs Review)

_Auto-submit attempted these but hit an error -- check `data/failed_screenshots/` for details._

- **[Runyon Design](https://himalayas.app/companies/runyon-design/jobs/design-strategy-director)** — Design Strategy Director  
  Source:  | Reason: Unsupported platform: Unknown

- **[StackBlitz](https://himalayas.app/companies/stackblitz/jobs/engineering-manager-front-end-ui-ux)** — Engineering Manager - Front-End  (UI/UX)  
  Source:  | Reason: Unsupported platform: Unknown

- **[Kettle](https://himalayas.app/companies/wearekettle/jobs/director-product-design)** — Director, Product Design  
  Source:  | Reason: Unsupported platform: Unknown

- **[BrowserStack](https://weworkremotely.com/remote-jobs/browserstack-manager-product-design)** — Manager - Product Design  
  Source:  | Reason: Unsupported platform: Unknown

- **[Hospitable](https://weworkremotely.com/remote-jobs/hospitable-staff-ui-ux-product-designer-usa-emea-remote-1)** — Staff UI/UX Product Designer (USA/EMEA - Remote)  
  Source:  | Reason: Unsupported platform: Unknown

---

## Auto-Submit Engine

The pipeline auto-detects the platform (LinkedIn, Greenhouse, Lever, Ashby, Indeed)
and submits using `scripts/auto_apply.py`.

**Required GitHub Secrets** (see `SETUP_SECRETS.md` for full guide):

| Secret | Purpose |
|--------|---------|
| `LINKEDIN_EMAIL` | LinkedIn account email |
| `LINKEDIN_PASSWORD` | LinkedIn account password |
| `APPLICANT_PHONE` | Phone number for ATS forms |
| `ANTHROPIC_API_KEY` | AI resume customization |

**Manual fallback** — if auto-submit is blocked:
1. Open the job URL
2. Upload the PDF from `customized_applications/<Company>/`
3. Paste the cover letter
