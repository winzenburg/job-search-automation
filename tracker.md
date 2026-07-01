# Job Search Tracker

**Started:** February 10, 2026  
**Last Updated:** July 1, 2026  
**Status:** Active — Outreach Ready  
**Target:** Head of Design Operations, VP/Director of Design, Principal Design Technologist, AI Design Ops Lead  
**Criteria:** $180k+, Remote or Colorado, AI transformation focus

---

## Quick Stats

| Metric | Count | Goal |
|--------|-------|------|
| **Companies Targeted** | 22 | 30 |
| **Decision-Makers Identified** | 29 | 40 |
| **Outreach Messages Ready** | 29 | — |
| **Warm Intros Requested** | 0 | 5 |
| **Direct Company Outreach Sent** | 0 | 15 |
| **Active Conversations** | 0 | 5 |
| **Interviews Scheduled** | 0 | 2 |

---

## Pipeline Status (July 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| Company Discovery | ✅ Done | 22 companies across 5 tiers |
| Contact Research | ✅ Done | 29 verified decision-makers |
| Message Generation | ✅ Done | 29 messages in `data/outreach/pending/` |
| Outreach Sent | ⏳ Ready | Review `LINKEDIN_OUTREACH.md` then send |
| Follow-ups | ⏳ Waiting | Schedule 7-day follow-ups after sending |
| Applications | ⏳ Running | Daily scanner active on GitHub Actions |

---

## Warm Introductions

| Contact Name | Company | Connector | Status | Date Requested | Notes |
|--------------|---------|-----------|--------|----------------|-------|
| | | | | | |

**Status Options:** Requested, Intro Made, Conversation Scheduled, Completed, Not Relevant

---

## Recruiters

| Recruiter Name | Firm | Specialty | Date Contacted | Status | Companies Discussed | Next Action |
|----------------|------|-----------|----------------|--------|-------------------|-------------|
| | | | | | | |

---

## Direct Company Outreach

| Company | Contact Name | Title | Channel | Date | Status | Next Action |
|---------|--------------|-------|---------|------|--------|-------------|
| | | | | | | |

**Status Options:** Researching, Contacted, Responded, Conversation Scheduled, Interview Process, Not Interested, No Response  
**Channel Options:** LinkedIn DM, Email, Warm Intro, Recruiter, Other

---

## Interviews in Process

| Company | Role | Stage | Contact | Next Step | Date |
|---------|------|-------|---------|-----------|------|
| | | | | | |

---

## Target Company Priority List

### Tier 1: Colorado-Based (Immediate Priority)
- [ ] Gusto (Denver) — CDO Amy Thibodeau
- [ ] Databricks (Denver) — VP Ryan Donahue
- [ ] Salesforce (Denver) — EVP/CDO Kat Holmes, SVP Jason Day
- [ ] Workday (Boulder) — CDO Jeff Gelfuso
- [ ] Palantir (Denver) — distributed design, no central exec

### Tier 2: AI-Native
- [ ] OpenAI — Head of Product Design Ian Silber
- [ ] Anthropic — Head of Design Joel Lewenstein
- [ ] Perplexity — VP Design Henry Modisett
- [ ] Runway — CCO Jamie Umpherson
- [ ] Scale AI — Head of Product Design role OPEN

### Tier 3: Design Tools
- [ ] Figma — CDO Loredana Crisan
- [ ] Notion — Head of Design (via Ashby feed)
- [ ] Linear — Head of Design Conor Muirhead
- [ ] Framer — CPO Jorn van Dijk
- [ ] Webflow — VP Design Kevin Wong

### Tier 4: Fintech/SaaS
- [ ] Stripe — Head of Design Katie Dill
- [ ] Brex — CDO Matt Bango
- [ ] Ramp — VP Design Diego Zaks ⭐ Highest AI alignment
- [ ] Airtable — VP Design Jaime Mariko McFarland
- [ ] Plaid — Head of Design Christophe Tauziet

### Tier 5: Consumer/Enterprise
- [ ] Duolingo — CDO Ryan Sims
- [ ] Asana — VP Design Manesh John
- [ ] Loom/Atlassian — Head of Design Stu Smith
- [ ] Canva — CDO Christina (CJ) Jones
- [ ] Miro — VP Design Ari Liusaari

---

## Notes & Insights

### July 2026 (Restart)
- Full pipeline rebuilt: 22 companies, 29 contacts, 29 outreach messages
- Added 4 new job board sources: Indeed, Built In, Himalayas, Remotive
- Application engine built: auto-generates PDFs + tracks submissions
- GitHub Actions runs daily at 8am MT (2pm UTC) weekdays
- **Next immediate action:** Send outreach using `LINKEDIN_OUTREACH.md`

### February 2026 (Start)
- Framework complete, pipeline initialized

---

## Key Learnings

**What's Working:**
- Automated scanner is finding 10-40 relevant roles per day across 7 sources
- Claude Sonnet generates high-quality, personalized cover letters

**What's Not Working:**
- LinkedIn job scraping blocked — using Himalayas + Indeed RSS as proxy
- Most ATS career feeds (Greenhouse/Lever) are not publicly accessible

**Adjustments Made:**
- Added Ashby API for companies that use it (OpenAI, Notion, Linear, Miro, Airtable)
- Added targeted Himalayas company search for 16 named companies
- Built LinkedIn Easy Apply framework (needs credentials in GitHub Secrets to activate)

---

**Highest Priority Action:** Open `LINKEDIN_OUTREACH.md` and send the Tier 1 messages today.
