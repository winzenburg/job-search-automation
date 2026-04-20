#!/usr/bin/env python3
"""
Antigravity Pipeline Orchestrator
Generates the customized Resume and Cover Letter and renders them to PDFs ready for submission.
"""

import sys
import os
from pathlib import Path
from customize_application_sonnet import load_voice_guide, fetch_job_posting_via_openclaw, call_sonnet_for_cover_letter, call_sonnet_for_resume, save_application
from text_to_pdf import create_resume_pdf

OUTPUT_DIR = Path(__file__).parent / "customized_applications"

def run_pipeline(company, job_url):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY environment variable not set.")
        return None

    print(f"Running pipeline for {company} at {job_url}...")
    voice_guide = load_voice_guide()
    
    # In a real run, you'd integrate the real text. For now we use the stubbed fetcher.
    job_posting = fetch_job_posting_via_openclaw(job_url)
    
    cover_letter = call_sonnet_for_cover_letter(company, job_posting, voice_guide, api_key)
    resume_text = call_sonnet_for_resume(company, job_posting, api_key)
    
    cl_path, resume_path = save_application(company, cover_letter, resume_text)
    
    # Convert them to PDF
    pdf_resume_path = os.path.splitext(resume_path)[0] + ".pdf"
    pdf_cl_path = os.path.splitext(cl_path)[0] + ".pdf"
    
    create_resume_pdf(resume_text, pdf_resume_path)
    create_resume_pdf(cover_letter, pdf_cl_path)
    
    print(f"\n✅ Ready for Antigravity Submission!")
    print(f"Resume PDF: {pdf_resume_path}")
    print(f"Cover Letter PDF: {pdf_cl_path}")
    
    return pdf_resume_path, pdf_cl_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        pass # In real use, parse args
    else:
        run_pipeline(sys.argv[1], sys.argv[2])
