# GitHub Secrets Setup Guide

The Antigravity auto-submit pipeline uses GitHub Secrets to store credentials
and personal info securely. Nothing sensitive lives in the repo.

---

## How to add a secret

1. Go to your repo on GitHub.com
2. **Settings → Secrets and variables → Actions → New repository secret**
3. Add each secret below, then save.

---

## Required secrets

### AI / core pipeline

| Secret | Value | Notes |
|--------|-------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-…` | From console.anthropic.com — drives resume & cover letter generation |

### Applicant profile (used in every ATS form)

These are used by the Playwright form-filler so every Greenhouse / Lever / Ashby
form is completed correctly without human input.

| Secret | Example value | Notes |
|--------|--------------|-------|
| `APPLICANT_NAME` | `Ryan Winzenburg` | Full legal name |
| `APPLICANT_EMAIL` | `ryanwinzenburg@gmail.com` | The email you want applications sent to |
| `APPLICANT_PHONE` | `+13035551234` | Include country code |
| `APPLICANT_LINKEDIN` | `https://www.linkedin.com/in/ryanwinzenburg` | Your LinkedIn profile URL |
| `APPLICANT_LOCATION` | `Denver, Colorado` | City, State — used in location fields |
| `APPLICANT_WEBSITE` | `https://ryanwinzenburg.com` | Portfolio / personal site (optional) |
| `APPLICANT_SALARY` | `180000` | Desired base salary (numeric, no commas) |

### LinkedIn Easy Apply

Enables the LinkedIn Easy Apply automation. Without these, LinkedIn jobs
are still discovered and materials are generated, but not submitted.

| Secret | Value |
|--------|-------|
| `LINKEDIN_EMAIL` | Your LinkedIn login email |
| `LINKEDIN_PASSWORD` | Your LinkedIn login password |

> **Important:** Use a strong, unique password. For accounts with 2-factor
> authentication enabled, you must temporarily disable 2FA or create an
> app-specific password to allow automated login. After the first successful
> automated login, a session cookie is cached at `data/.linkedin_session.json`
> so subsequent logins are cookie-based (more reliable, less suspicious).

### Email reports

| Secret | Value |
|--------|-------|
| `SMTP_USERNAME` | Gmail address to send reports from |
| `SMTP_PASSWORD` | Gmail App Password (not your account password) |

> Generate a Gmail App Password at:
> myaccount.google.com → Security → 2-Step Verification → App passwords

### Indeed Quick Apply (optional)

Only needed if you want auto-submission on Indeed. LinkedIn + ATS portals
(Greenhouse/Lever/Ashby) do not need this.

| Secret | Value |
|--------|-------|
| `INDEED_PASSWORD` | Your Indeed account password |

---

## Platform coverage

Once all secrets above are set, the pipeline handles submissions across:

| Platform | Auto-submit | Notes |
|----------|------------|-------|
| **LinkedIn Easy Apply** | ✅ Full automation | Playwright + stealth mode + session persistence |
| **Greenhouse** | ✅ Full automation | Direct form-fill, resume upload, EEOC selects |
| **Lever** | ✅ Full automation | Direct form-fill, resume upload |
| **Ashby** | ✅ Full automation | React form-fill, resume upload |
| **Indeed Quick Apply** | ✅ Full automation | Requires `INDEED_PASSWORD` |
| **Workday** | ❌ Not supported | Workday blocks automation aggressively |
| **External company ATS** | ❌ Not supported | Too variable; materials generated for manual apply |

---

## Daily run schedule

The workflow runs **Monday–Friday at 8:00 AM Mountain Time** and:

1. Scans 9 job board sources for new opportunities
2. AI-generates a tailored resume + cover letter PDF for each new match
3. Auto-submits to LinkedIn, Greenhouse, Lever, Ashby, and Indeed
4. Commits updated `data/applications.json` and `APPLICATIONS.md` to the repo
5. Emails you a report with attached PDFs

**Daily submission caps** (built-in to prevent account bans):

| Platform | Daily limit |
|----------|------------|
| LinkedIn | 15 |
| Greenhouse | 40 |
| Lever | 40 |
| Ashby | 40 |
| Indeed | 20 |

---

## Manual triggers

```bash
# Dry run — see what would be submitted without actually submitting
python3 scripts/auto_apply.py --batch --dry-run

# Submit a single specific job
python3 scripts/auto_apply.py \
    --url "https://jobs.lever.co/openai/abc123" \
    --resume "customized_applications/OpenAI/resume.pdf" \
    --cover-letter "customized_applications/OpenAI/cover_letter.pdf"

# Generate materials only (no submission)
python3 scripts/apply_jobs.py --limit 10 --no-submit

# Batch-submit all pending
python3 scripts/auto_apply.py --batch --limit 5
```

---

## Debugging

- **Debug screenshots** are saved to `data/failed_screenshots/` whenever a
  browser automation step fails. Check these to see exactly what the browser
  encountered (CAPTCHA, wrong page, changed UI, etc.).

- **Rate tracking** is stored in `data/.submit_rate.json` — check this if
  you suspect the daily limit is being hit.

- **LinkedIn session** is cached in `data/.linkedin_session.json`. Delete
  this file to force a fresh login on the next run.

---

## Security notes

- All secrets are injected as environment variables by GitHub Actions — they
  never appear in logs or source code.
- `data/.linkedin_session.json` is gitignored (cookie cache, not committed).
- `data/.submit_rate.json` is committed so rate limits persist across runs.
- If LinkedIn flags your account for unusual activity, pause the LinkedIn
  automation by removing the `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` secrets
  until the account recovers.
