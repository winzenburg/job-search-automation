# Role-targeted applications (Sep 2026)

**Decision:** Applications should look like a designer applying for the posted job — not like a founder hedging until a company works.

This replaces the earlier “AI-augmented design operations architect / transformation” pitch for outbound applications. That pitch conflated founder work, consulting, design ops, PM, and executive leadership. It reads as overqualified and temporary.

---

## What hiring managers were seeing

- LinkedIn and the site lead with Founder (Winzinvest, Casimir, Foundpath, Kinlet).
- Cover letters opened as a principal/VP-level operator offering to transform the company.
- The daily sweep applied to anything with “staff/director/head” plus “design” somewhere in the description: data engineering, people ops, motion design, product management, brand, tax, sales.

None of that matches “Principal Product Designer” or “Director, Product Design.” It confirms the fear: *they won’t stay; this is a parking place.*

---

## Rules going forward

1. **Title must be a design/UX/design-ops/design-leadership job.** Description-only matches are out. See `role_targeting.py`.
2. **Resume is employment-led.** CVS Health, Life Time, Pitney Bowes, Buildout, DOI, Level 3, MapQuest, Aspenware. Independent work is *consulting*, not founding, and it is not the headline.
3. **Cover letter matches the altitude of the posting.** IC letters sound like a designer. Director letters sound like a design director. Nobody gets the founder biography.
4. **Do not mention parallel companies** in application materials. Don’t volunteer them; don’t “spin” them. If they come up in an interview, talk about them as past/adjacent craft — not as the reason you’re applying.
5. **One job family per application.** Customize from `templates/MASTER_RESUME.md` + `VOICE_GUIDE.md`. Never a generalist “I can do anything” packet.

---

## Role families

| Family | Examples | You sound like |
|---|---|---|
| `product_design_ic` | Principal / Staff / Senior Product Designer, UX Designer | Hands-on product designer |
| `design_leadership` | Director / Head / VP of Product Design, Design Manager | Design manager or director of a product-design team |
| `design_ops_systems` | Design Systems Lead, Design Operations | Systems and operating-rhythm specialist |

Out of scope (do not generate materials): PM-without-design, engineering, data, people/HR, sales, brand/motion/graphic, program/project ops, customer success.

---

## Why this is not a lie

You have 15+ years of employed product-design and design-ops work. That is the job. Founder work is real and it is also *more than these roles are buying.* Application materials should sell what they are buying.

LinkedIn and winzenburg.com still tell the founder story. Recruiters who click through will see it. Updating the LinkedIn headline/About to match the employment-led resume is the next surface (see `LINKEDIN_OPTIMIZATION.md`). Until then, don’t send the founder site in cover letters.

---

## Engine

- Classifier: `role_targeting.py`
- Master resume: `templates/MASTER_RESUME.md`
- Letter voice: `VOICE_GUIDE.md`
- Generator: `customize_application_sonnet.py` (loads both + targeting block)
- Gates: `job_search_scanner.filter_opportunities`, `scripts/apply_jobs.py`

If a posting fails `should_apply(title)`, skip it. Do not “customize harder.”
