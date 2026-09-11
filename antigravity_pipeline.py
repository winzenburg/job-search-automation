#!/usr/bin/env python3
"""
Antigravity Pipeline Orchestrator
Generates a role-targeted resume and cover letter PDF for one posting.
"""

import os
import sys
from pathlib import Path

from customize_application_sonnet import (
    call_sonnet_for_cover_letter,
    call_sonnet_for_resume,
    fetch_job_posting_via_openclaw,
    load_voice_guide,
    save_application,
)
from role_targeting import should_apply
from text_to_pdf import create_resume_pdf

OUTPUT_DIR = Path(__file__).parent / "customized_applications"


def run_pipeline(company, job_url, job_title=""):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY environment variable not set.")
        return None

    if job_title and not should_apply(job_title):
        print(f"[SKIP] Out of scope for role-targeted applications: {job_title}")
        return None

    print(f"Running pipeline for {company} — {job_title or job_url}...")
    voice_guide = load_voice_guide()

    job_posting = fetch_job_posting_via_openclaw(job_url)

    cover_letter = call_sonnet_for_cover_letter(
        company, job_posting, voice_guide, api_key, job_title=job_title
    )
    resume_text = call_sonnet_for_resume(
        company, job_posting, api_key, job_title=job_title
    )

    cl_path, resume_path = save_application(company, cover_letter, resume_text)

    pdf_resume_path = os.path.splitext(resume_path)[0] + ".pdf"
    pdf_cl_path = os.path.splitext(cl_path)[0] + ".pdf"

    create_resume_pdf(resume_text, pdf_resume_path)
    create_resume_pdf(cover_letter, pdf_cl_path)

    print("\nReady for submission")
    print(f"Resume PDF: {pdf_resume_path}")
    print(f"Cover Letter PDF: {pdf_cl_path}")

    return pdf_resume_path, pdf_cl_path


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        run_pipeline(sys.argv[1], sys.argv[2], title)
