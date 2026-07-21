# Applications Log

_Last updated: 2026-07-21 15:48 UTC_

**Total applications:** 19  
**Submitted:** 0  
**Needs manual apply (no automation for this source):** 7  
**Failed (needs review):** 12  
**Materials ready, not yet attempted:** 0

---

## Needs Manual Apply

_These came from a job board listing rather than a direct application link, so auto-submit couldn't handle them. Apply manually via the link._

- **[garden3d](https://weworkremotely.com/remote-jobs/garden3d-head-of-design)** — Head of Design  
  Source:  | Generated: 2026-07-20
  Resume: `Resume_garden3d.pdf`

- **[garden3d](https://remotive.com/remote-jobs/marketing/head-of-marketing-communications-2091068)** — Head of Marketing & Communications  
  Source:  | Generated: 2026-07-17
  Resume: `Resume_garden3d.pdf`

- **[TE Connectivity](https://weworkremotely.com/remote-jobs/te-connectivity-staff-mechanical-product-development-engineer-integrated-predictive-analysis)** — Staff Mechanical Product Development Engineer- Integrated Predictive Analysis  
  Source:  | Generated: 2026-07-16
  Resume: `Resume_TE_Connectivity.pdf`

- **[TE Connectivity](https://weworkremotely.com/remote-jobs/te-connectivity-product-manager-iii-remote)** — PRODUCT MANAGER III (Remote)  
  Source:  | Generated: 2026-07-16
  Resume: `Resume_TE_Connectivity.pdf`

- **[Canva](https://himalayas.app/companies/canva/jobs/staff-front-end-engineer-design-systems)** — Staff Front-End Engineer - Design Systems  
  Source:  | Generated: 2026-07-14
  Resume: `Resume_Canva.pdf`

- **[Stripe](https://himalayas.app/companies/stripe/jobs/staff-product-manager-dashboard)** — Staff Product Manager, Dashboard  
  Source:  | Generated: 2026-07-14
  Resume: `Resume_Stripe.pdf`

- **[INNERGY](https://remoteOK.com/remote-jobs/remote-director-of-customer-success-innergy-1134738)** — Director of Customer Success  
  Source:  | Generated: 2026-07-13
  Resume: `Resume_INNERGY.pdf`

## Failed (Needs Review)

_Auto-submit attempted these but hit an error -- check `data/failed_screenshots/` for details._

- **[](https://www.linkedin.com/jobs/view/head-of-product-design-at-trm-labs-4441282745)** — Head of Product Design  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/director-product-design-at-bubble-4424710894)** — Director, Product Design  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/director-of-product-design-avail-at-realtor-com-4429351578)** — Director of Product Design, Avail  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/director-product-design-at-fetch-4437401927)** — Director, Product Design  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/design-director-product-design-at-instrument-4432034373)** — Design Director, Product Design  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/director-of-product-design-at-qualia-4432687941)** — Director of Product Design  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

- **[](https://www.linkedin.com/jobs/view/design-director-ux-ui-brand-remote-us-based-full-time-at-variate-4439355330)** — Design Director (UX/UI/Brand) (Remote, US-Based, Full-time)  
  Source:  | Reason: LinkedIn login failed (CAPTCHA or wrong credentials)

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
