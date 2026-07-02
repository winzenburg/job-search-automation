#!/usr/bin/env python3
"""
Application Engine
Reads newly discovered jobs from the scanner, generates tailored PDF
resume + cover letter for each match, attempts auto-submission via
scripts/auto_apply.py, and logs everything to data/applications.json
and APPLICATIONS.md.

Usage:
    python3 scripts/apply_jobs.py [--limit N] [--dry-run] [--no-submit]

Environment:
    ANTHROPIC_API_KEY  — required for AI customization
    LINKEDIN_EMAIL / LINKEDIN_PASSWORD — enables LinkedIn Easy Apply
    APPLICANT_EMAIL / APPLICANT_PHONE  — used for ATS form-fill
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
        "## Auto-Submit Engine",
        "",
        "The pipeline auto-detects the platform (LinkedIn, Greenhouse, Lever, Ashby, Indeed)",
        "and submits using `scripts/auto_apply.py`.",
        "",
        "**Required GitHub Secrets** (see `SETUP_SECRETS.md` for full guide):",
        "",
        "| Secret | Purpose |",
        "|--------|---------|",
        "| `LINKEDIN_EMAIL` | LinkedIn account email |",
        "| `LINKEDIN_PASSWORD` | LinkedIn account password |",
        "| `APPLICANT_PHONE` | Phone number for ATS forms |",
        "| `ANTHROPIC_API_KEY` | AI resume customization |",
        "",
        "**Manual fallback** — if auto-submit is blocked:",
        "1. Open the job URL",
        "2. Upload the PDF from `customized_applications/<Company>/`",
        "3. Paste the cover letter",
        "",
    ]

    APPLICATIONS_MD.write_text("\n".join(lines))
    print(f"✅ Updated {APPLICATIONS_MD.name}")


# ---------------------------------------------------------------------------
# Auto-submit via scripts/auto_apply.py
# ---------------------------------------------------------------------------

def attempt_auto_submit(opp: dict, resume_pdf: str, cover_letter_pdf: str) -> bool:
    """
    Route the job through the multi-platform auto_apply engine.
    Returns True if successfully submitted.
    """
    from scripts.auto_apply import submit  # type: ignore[import]

    print(f"  🤖 Attempting auto-submit for {opp.get('company')}…")
    result = submit(
        url=opp.get("url", ""),
        resume_pdf=resume_pdf if resume_pdf and Path(resume_pdf).exists() else None,
        cover_letter_pdf=cover_letter_pdf if cover_letter_pdf and Path(cover_letter_pdf).exists() else None,
    )
    return bool(result.get("success"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Apply to discovered jobs")
    parser.add_argument("--limit", type=int, default=5, help="Max new jobs to process per run (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling the AI")
    parser.add_argument("--no-submit", action="store_true", help="Generate materials but skip auto-submission")
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

        # Attempt auto-submit (all supported platforms)
        submitted = False
        if not args.no_submit:
            submitted = attempt_auto_submit(opp, str(resume_pdf), str(cover_letter_pdf))

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
