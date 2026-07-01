#!/usr/bin/env python3
"""
Application Engine
Reads newly discovered jobs from the scanner, generates tailored PDF
resume + cover letter for each match, and logs everything to
data/applications.json and APPLICATIONS.md.

Usage:
    python3 scripts/apply_jobs.py [--limit N] [--dry-run]

Environment:
    ANTHROPIC_API_KEY  — required for AI customization

LinkedIn / Indeed Easy Apply:
    The script flags "Easy Apply" eligible roles in the log.
    To submit them automatically set:
        LINKEDIN_EMAIL, LINKEDIN_PASSWORD   (GitHub Secrets)
    then install playwright:
        pip install playwright && playwright install chromium
    and the auto-submit section below will handle the flow.
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

DATA_DIR = PROJECT_DIR / "data"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
APPLICATIONS_MD = PROJECT_DIR / "APPLICATIONS.md"
SCANNER_STATE = PROJECT_DIR / "scanner_state.json"
OUTPUT_DIR = PROJECT_DIR / "customized_applications"

EASY_APPLY_SOURCES = {"Indeed", "LinkedIn", "Himalayas", "RemoteOK"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def applied_urls(applications: list[dict]) -> set[str]:
    return {a["url"] for a in applications}


def is_easy_apply(opp: dict) -> bool:
    source = opp.get("source", "")
    url = opp.get("url", "")
    return (
        any(s in source for s in EASY_APPLY_SOURCES)
        or "easyapply" in url.lower()
        or "apply" in url.lower()
    )


# ---------------------------------------------------------------------------
# Application generation
# ---------------------------------------------------------------------------

def generate_application_materials(opp: dict, api_key: str) -> tuple[str, str] | None:
    """
    Call the Antigravity pipeline to generate resume + cover letter PDFs.
    Returns (resume_pdf_path, cover_letter_pdf_path) or None on failure.
    """
    from antigravity_pipeline import run_pipeline
    company = opp.get("company", "Unknown")
    url = opp.get("url", "")

    try:
        result = run_pipeline(company, url)
        if result:
            return result  # (resume_pdf, cover_letter_pdf)
    except Exception as e:
        print(f"  ⚠️  Pipeline failed for {company}: {e}")
    return None


# ---------------------------------------------------------------------------
# Application tracking
# ---------------------------------------------------------------------------

def record_application(
    applications: list[dict],
    opp: dict,
    resume_pdf: str,
    cover_letter_pdf: str,
    submitted: bool = False,
) -> list[dict]:
    record = {
        "id": str(uuid.uuid4())[:8],
        "company": opp.get("company", "Unknown"),
        "title": opp.get("title", "Unknown"),
        "source": opp.get("source", ""),
        "url": opp.get("url", ""),
        "location": opp.get("location", "Remote"),
        "salary": opp.get("salary", 0),
        "discovered_at": opp.get("foundDate", datetime.now().isoformat()),
        "applied_at": datetime.now().isoformat(),
        "submitted": submitted,
        "easy_apply": is_easy_apply(opp),
        "resume_pdf": resume_pdf,
        "cover_letter_pdf": cover_letter_pdf,
        "status": "submitted" if submitted else "materials_ready",
        "notes": "",
    }
    applications.append(record)
    return applications


# ---------------------------------------------------------------------------
# Markdown log
# ---------------------------------------------------------------------------

def rebuild_applications_md(applications: list[dict]) -> None:
    lines = [
        "# Applications Log",
        "",
        f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"**Total applications:** {len(applications)}  ",
        f"**Submitted:** {sum(1 for a in applications if a.get('submitted'))}  ",
        f"**Materials ready:** {sum(1 for a in applications if not a.get('submitted'))}",
        "",
        "---",
        "",
    ]

    # Group by status
    submitted = [a for a in applications if a.get("submitted")]
    ready = [a for a in applications if not a.get("submitted")]

    if submitted:
        lines += ["## Submitted", ""]
        for a in sorted(submitted, key=lambda x: x.get("applied_at", ""), reverse=True):
            lines.append(
                f"- **[{a['company']}]({a['url']})** — {a['title']}  "
            )
            lines.append(
                f"  Source: {a['source']} | Applied: {a['applied_at'][:10]} | "
                f"Easy Apply: {'yes' if a['easy_apply'] else 'no'}"
            )
            lines.append("")

    if ready:
        lines += ["## Materials Ready (Pending Submission)", ""]
        for a in sorted(ready, key=lambda x: x.get("applied_at", ""), reverse=True):
            lines.append(
                f"- **[{a['company']}]({a['url']})** — {a['title']}  "
            )
            lines.append(
                f"  Source: {a['source']} | Generated: {a['applied_at'][:10]} | "
                f"{'⚡ Easy Apply eligible' if a['easy_apply'] else 'Manual apply'}"
            )
            if a.get("resume_pdf"):
                lines.append(f"  Resume: `{Path(a['resume_pdf']).name}`")
            if a.get("cover_letter_pdf"):
                lines.append(f"  Cover Letter: `{Path(a['cover_letter_pdf']).name}`")
            lines.append("")

    if not applications:
        lines += ["_No applications yet. Run `python3 scripts/apply_jobs.py` to start._", ""]

    lines += [
        "---",
        "",
        "## How to Submit",
        "",
        "### Easy Apply (LinkedIn / Indeed)",
        "1. Open the job URL from above",
        "2. Click Easy Apply / Quick Apply",
        "3. Upload the PDF from `customized_applications/<Company>/`",
        "4. Paste the cover letter text",
        "",
        "### Greenhouse / Lever / Ashby portals",
        "1. Open the job URL",
        "2. Upload resume PDF",
        "3. Paste or upload cover letter",
        "",
        "### Auto-submit (experimental)",
        "Set `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` in GitHub Secrets,",
        "then run `python3 scripts/linkedin_easy_apply.py`.",
        "",
    ]

    APPLICATIONS_MD.write_text("\n".join(lines))
    print(f"✅ Updated {APPLICATIONS_MD.name}")


# ---------------------------------------------------------------------------
# LinkedIn Easy Apply (browser automation framework)
# ---------------------------------------------------------------------------

def attempt_linkedin_easy_apply(opp: dict, resume_pdf: str) -> bool:
    """
    Submit a LinkedIn Easy Apply application using Playwright.
    Requires LINKEDIN_EMAIL + LINKEDIN_PASSWORD environment variables
    and: pip install playwright && playwright install chromium

    Returns True if successfully submitted, False otherwise.
    """
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    if not email or not password:
        print("  ℹ️  LinkedIn credentials not set — skipping auto-submit")
        return False

    url = opp.get("url", "")
    if "linkedin.com" not in url:
        return False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⚠️  playwright not installed — run: pip install playwright && playwright install chromium")
        return False

    print(f"  🤖 Attempting LinkedIn Easy Apply for {opp.get('company')}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Log in to LinkedIn
            page.goto("https://www.linkedin.com/login", timeout=30000)
            page.fill('input[name="session_key"]', email)
            page.fill('input[name="session_password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=20000)

            # Navigate to job
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Click Easy Apply button
            easy_apply_btn = page.locator("button:has-text('Easy Apply')").first
            if not easy_apply_btn.is_visible(timeout=5000):
                print("  ⚠️  No Easy Apply button found")
                browser.close()
                return False

            easy_apply_btn.click()
            page.wait_for_timeout(2000)

            # Upload resume if file upload prompt appears
            file_input = page.locator('input[type="file"]').first
            if file_input.is_visible(timeout=3000):
                file_input.set_input_files(resume_pdf)
                page.wait_for_timeout(1500)

            # Step through modal pages (Next → Review → Submit)
            for _ in range(8):
                submit_btn = page.locator("button:has-text('Submit application')").first
                if submit_btn.is_visible(timeout=2000):
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    print(f"  ✅ Submitted LinkedIn Easy Apply for {opp.get('company')}")
                    browser.close()
                    return True

                next_btn = page.locator("button:has-text('Next')").first
                if next_btn.is_visible(timeout=2000):
                    next_btn.click()
                    page.wait_for_timeout(1500)
                else:
                    break

            browser.close()
            print("  ⚠️  Could not complete Easy Apply flow — manual review needed")
            return False

    except Exception as e:
        print(f"  ⚠️  LinkedIn Easy Apply failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Apply to discovered jobs")
    parser.add_argument("--limit", type=int, default=5, help="Max new jobs to process per run (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling the AI")
    parser.add_argument("--force-url", type=str, help="Process a specific job URL directly")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("[ERROR] ANTHROPIC_API_KEY not set. Export it or use --dry-run.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("APPLICATION ENGINE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Limit: {args.limit} | Dry run: {args.dry_run}")

    # Load state
    applications: list[dict] = load_json(APPLICATIONS_FILE, [])
    scanner_state: dict = load_json(SCANNER_STATE, {"opportunities": {}})
    already_applied = applied_urls(applications)

    # --force-url: single job override
    if args.force_url:
        opps_to_process = [{
            "source": "Manual",
            "title": "Forced",
            "company": args.force_url.split("/")[2],
            "location": "Remote",
            "salary": 0,
            "url": args.force_url,
            "foundDate": datetime.now().isoformat(),
        }]
    else:
        all_opps = list(scanner_state.get("opportunities", {}).values())
        opps_to_process = [
            opp for opp in all_opps
            if opp.get("url") not in already_applied
        ][:args.limit]

    print(f"\nNew eligible jobs: {len(opps_to_process)}")

    if not opps_to_process:
        print("No new jobs to process. Run the scanner first.")
        rebuild_applications_md(applications)
        return

    new_apps = 0
    for opp in opps_to_process:
        company = opp.get("company", "Unknown")
        title = opp.get("title", "")
        source = opp.get("source", "")
        url = opp.get("url", "")

        print(f"\n{'─'*60}")
        print(f"  Company:  {company}")
        print(f"  Role:     {title}")
        print(f"  Source:   {source}")
        print(f"  URL:      {url}")
        print(f"  Easy Apply eligible: {is_easy_apply(opp)}")

        if args.dry_run:
            print("  [DRY RUN] Would generate materials here")
            continue

        # Generate application materials
        result = generate_application_materials(opp, api_key)
        if not result:
            print(f"  ⚠️  Skipping {company} — materials generation failed")
            continue

        resume_pdf, cover_letter_pdf = result

        # Attempt auto-submit for LinkedIn Easy Apply
        submitted = False
        if "linkedin.com" in url:
            submitted = attempt_linkedin_easy_apply(opp, resume_pdf)

        # Record in tracker
        applications = record_application(applications, opp, str(resume_pdf), str(cover_letter_pdf), submitted)
        new_apps += 1

        status = "✅ Submitted" if submitted else "📄 Materials ready"
        print(f"  {status}: {company}")

    # Save and rebuild log
    save_json(APPLICATIONS_FILE, applications)
    rebuild_applications_md(applications)

    print(f"\n{'='*70}")
    print(f"Done: {new_apps} new applications processed")
    print(f"Total tracked: {len(applications)}")
    print(f"Log: {APPLICATIONS_MD}")
    print("=" * 70)


if __name__ == "__main__":
    main()
