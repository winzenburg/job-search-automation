#!/usr/bin/env python3
"""
Application Customization Engine — Sonnet API Integration
Uses Claude 3.5 Sonnet for intelligent cover letter + resume customization
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import base64

# Configuration
SCRIPT_DIR = Path(__file__).parent
VOICE_GUIDE_PATH = SCRIPT_DIR / "VOICE_GUIDE.md"
OUTPUT_DIR = SCRIPT_DIR / "customized_applications"
RECIPIENT_EMAIL = "ryanwinzenburg@gmail.com"


def load_voice_guide():
    """Load the voice/tone guide for Sonnet customization."""
    if VOICE_GUIDE_PATH.exists():
        return VOICE_GUIDE_PATH.read_text()
    else:
        print("[ERROR] Voice guide not found at", VOICE_GUIDE_PATH)
        return ""


def fetch_job_posting_via_openclaw(url: str) -> dict:
    """
    Fetch job posting content from the job URL.

    Strategy (in priority order):
    1. Ashby API  — structured JSON, richest content
    2. Greenhouse API — structured JSON
    3. Lever API — structured JSON
    4. HTTP fallback — strip HTML tags from raw page

    Returns a dict with 'url', 'content', and 'fetched_at'.
    """
    import urllib.request
    import urllib.parse
    import re

    print(f"[FETCH] Retrieving job posting from: {url}")
    content = ""

    try:
        # ── Ashby structured fetch ──────────────────────────────────────────
        # URL pattern: jobs.ashbyhq.com/{company}/{uuid}
        ashby_match = re.search(r"ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", url)
        if ashby_match:
            company_slug = ashby_match.group(1)
            job_id = ashby_match.group(2)
            api_url = (
                f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
                f"?includeCompensation=true"
            )
            req = urllib.request.Request(
                api_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            for posting in data.get("jobPostings", []):
                if posting.get("id") == job_id:
                    content = posting.get("descriptionPlain", "") or posting.get("description", "")
                    break

        # ── Greenhouse structured fetch ─────────────────────────────────────
        # URL pattern: boards.greenhouse.io/{company}/jobs/{id}
        elif "greenhouse.io" in url:
            gh_match = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
            if gh_match:
                company_slug = gh_match.group(1)
                job_id = gh_match.group(2)
                api_url = f"https://boards.greenhouse.io/{company_slug}/jobs/{job_id}?content=true"
                req = urllib.request.Request(
                    api_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                content = data.get("content", "") or data.get("description", "")

        # ── Lever structured fetch ──────────────────────────────────────────
        # URL pattern: jobs.lever.co/{company}/{uuid}
        elif "lever.co" in url:
            lever_match = re.search(r"lever\.co/([^/]+)/([0-9a-f-]{36})", url)
            if lever_match:
                company_slug = lever_match.group(1)
                job_id = lever_match.group(2)
                api_url = f"https://api.lever.co/v0/postings/{company_slug}/{job_id}"
                req = urllib.request.Request(
                    api_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                desc = data.get("description", "") or ""
                lists = data.get("lists", [])
                list_text = "\n".join(
                    f"{lst.get('text','')}: {lst.get('content','')}" for lst in lists
                )
                content = f"{desc}\n{list_text}".strip()

    except Exception as e:
        print(f"  ⚠️  Structured fetch failed ({e}), falling back to HTML scrape")

    # ── HTML fallback ───────────────────────────────────────────────────────
    if not content:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                }
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                raw_html = r.read().decode("utf-8", errors="replace")

            # Strip tags and compress whitespace
            no_tags = re.sub(r"<[^>]+>", " ", raw_html)
            content = re.sub(r"\s{2,}", " ", no_tags).strip()[:6000]

        except Exception as e:
            print(f"  ⚠️  HTML fallback also failed: {e}")
            content = "(Job posting content could not be fetched — apply manually)"

    # Strip HTML entities from any fetched content
    content = re.sub(r"&[a-z]+;", " ", content)
    content = re.sub(r"&#\d+;", " ", content)
    content = content.strip()[:6000]

    print(f"[✓] Fetched {len(content)} chars of job content")
    return {
        "url": url,
        "content": content,
        "fetched_at": datetime.now().isoformat(),
    }


def call_sonnet_for_cover_letter(company, job_posting, voice_guide, openai_api_key=None):
    """
    Call Claude 3.5 Sonnet to generate customized cover letter.
    Uses ANTHROPIC_API_KEY environment variable if openai_api_key not provided.
    """
    import anthropic
    
    api_key = openai_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set. Cannot call Sonnet.")
        return "[ERROR: API key not configured]"
    
    print(f"\n[SONNET] Customizing cover letter for {company}...")
    
    system_prompt = """You are an expert career advisor crafting principal-level UX/Design cover letters.
Your goal: Generate compelling, authentic cover letters that position the candidate as a strategic design leader.
Follow the VOICE_GUIDE exactly. No preamble—output only the letter."""
    
    user_prompt = f"""VOICE_GUIDE:
{voice_guide}

COMPANY: {company}
JOB URL: {job_posting['url']}

JOB POSTING:
{job_posting['content']}

CANDIDATE BACKGROUND:
- 10+ years in UX/Design/Product across Healthcare (Aetna), Geospatial (MapQuest/AOL), Telecom (Comcast, Level 3), Fintech (Pitney Bowes)
- Expertise: Design Systems, Design Operations, Product Management, AI-augmented workflows
- Leadership: Mentored teams, established frameworks, shaped product roadmaps
- Recent: Swing trading systems, SaaS platforms (Cultivate), design systems (kinetic-ui), caregiver tech (Kinlet)

Generate a principal-level cover letter:
1. Strategic intro (who you are as a leader)
2. 1-2 specific initiatives with quantified business impact
3. Leadership, mentoring, influence
4. Alignment with {company}'s product/mission
5. Calm confidence, no hype
6. 4-5 tight paragraphs

Output: Ready-to-submit letter (no preamble)."""
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        cover_letter = message.content[0].text
        print("[✓] Cover letter generated")
        return cover_letter
    
    except Exception as e:
        print(f"[ERROR] Sonnet cover letter failed: {e}")
        return f"[Error: {str(e)}]"


def call_sonnet_for_resume(company, job_posting, api_key=None):
    """
    Call Claude 3.5 Sonnet to customize resume for the role.
    """
    import anthropic
    
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set.")
        return "[ERROR: API key not configured]"
    
    print(f"[SONNET] Customizing resume for {company}...")
    
    system_prompt = """You are an expert resume advisor for principal-level design leaders.
Customize the resume by reordering bullets, highlighting relevant achievements, and integrating job keywords.
Maintain ATS optimization. Output only the customized sections."""
    
    user_prompt = f"""COMPANY: {company}

JOB POSTING:
{job_posting['content']}

BASE RESUME HIGHLIGHTS:
- 10+ years UX/Design/Product across Healthcare, Fintech, Telecom, Geospatial
- Design Systems, Design Operations, Product Management expertise
- Led initiatives resulting in 35-40% adoption increases, 22% support reduction
- Mentored teams of 4+ designers through high-growth phases
- Established design frameworks enabling 40% faster shipping
- Recent: AI-augmented workflows, SaaS platforms, caregiver tech

Customize the resume for this {company} role:
1. Reorder bullets—lead with most relevant experience
2. Front-load achievements matching job requirements
3. Integrate keywords from job description naturally
4. Highlight leadership, mentoring, systems thinking
5. Preserve quantified impact
6. Maintain ATS optimization

Output: Customized professional summary + 5-7 top achievements."""
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        resume_text = message.content[0].text
        print("[✓] Resume customized")
        return resume_text
    
    except Exception as e:
        print(f"[ERROR] Sonnet resume failed: {e}")
        return f"[Error: {str(e)}]"


def save_application(company, cover_letter, resume_customization):
    """
    Save customized documents to files.
    """
    company_dir = OUTPUT_DIR / company.replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)
    
    cl_path = company_dir / f"Cover_Letter_{company.replace(' ', '_')}.txt"
    resume_path = company_dir / f"Resume_{company.replace(' ', '_')}.txt"
    
    # Save cover letter
    cl_path.write_text(cover_letter)
    print(f"[✓] Cover letter saved: {cl_path.name}")
    
    # Save resume customization
    resume_path.write_text(resume_customization)
    print(f"[✓] Resume customization saved: {resume_path.name}")
    
    return cl_path, resume_path


def send_via_openclaw_message(recipient, subject, body, attachments=None):
    """
    Send email via OpenClaw message tool.
    This is a wrapper function that would integrate with the message tool.
    """
    print(f"\n[EMAIL] Preparing to send to {recipient}...")
    
    message_data = {
        "to": recipient,
        "subject": subject,
        "body": body,
        "attachments": attachments or [],
    }
    
    print(f"[✓] Email prepared")
    print(f"    Subject: {subject}")
    print(f"    Recipient: {recipient}")
    print(f"    Attachments: {len(attachments or [])} files")
    
    # In production, would call:
    # message(
    #     action="send",
    #     target=recipient,
    #     message=body,
    #     filePath=attachments[0] if attachments else None,
    # )
    
    return True


def main():
    """Main workflow"""
    
    if len(sys.argv) < 3:
        print("Usage: python3 customize_application_sonnet.py <company> <job_url>")
        print("\nExample:")
        print("  python3 customize_application_sonnet.py Anthropic https://boards.greenhouse.io/anthropic/jobs/...")
        print("\nEnvironment:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)
    
    company = sys.argv[1]
    job_url = sys.argv[2]
    
    print(f"\n{'='*70}")
    print(f"🎯 APPLICATION CUSTOMIZATION ENGINE (Sonnet)")
    print(f"{'='*70}")
    print(f"Company:     {company}")
    print(f"Job URL:     {job_url}")
    print(f"Timestamp:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)
    
    print("[✓] API key configured\n")
    
    # 1. Load voice guide
    print("[1/6] Loading voice guide...")
    voice_guide = load_voice_guide()
    if not voice_guide:
        print("[ERROR] Could not load voice guide")
        sys.exit(1)
    print("[✓] Voice guide loaded\n")
    
    # 2. Fetch job posting
    print("[2/6] Fetching job posting...")
    job_posting = fetch_job_posting_via_openclaw(job_url)
    print("[✓] Job posting retrieved\n")
    
    # 3. Generate cover letter
    print("[3/6] Generating cover letter via Sonnet...")
    cover_letter = call_sonnet_for_cover_letter(company, job_posting, voice_guide, api_key)
    print()
    
    # 4. Customize resume
    print("[4/6] Customizing resume via Sonnet...")
    resume_customization = call_sonnet_for_resume(company, job_posting, api_key)
    print()
    
    # 5. Save files
    print("[5/6] Saving customized documents...")
    cl_path, resume_path = save_application(company, cover_letter, resume_customization)
    print()
    
    # 6. Prepare email
    print("[6/6] Preparing email delivery...")
    email_subject = f"✅ Your Customized {company} Application is Ready"
    email_body = f"""Hi Ryan,

Your customized application materials for {company} are ready to review and submit.

**Files:**
📄 Cover Letter: {cl_path.name}
📋 Resume Customization: {resume_path.name}

**What Was Customized:**
✓ Cover letter tailored to {company}'s role and mission
✓ Resume reordered to highlight relevant experience
✓ Keywords from job posting naturally integrated
✓ Your principal-level voice maintained throughout
✓ Business impact and leadership emphasized

**Next Steps:**
1. Review both documents
2. Make any personal edits
3. Copy the cover letter content into the application portal (or submit as PDF)
4. Upload the customized resume

Ready to submit whenever you are.

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Job URL: {job_url}
"""
    
    send_via_openclaw_message(RECIPIENT_EMAIL, email_subject, email_body, [str(cl_path), str(resume_path)])
    
    print(f"\n{'='*70}")
    print(f"✅ CUSTOMIZATION COMPLETE")
    print(f"{'='*70}")
    print(f"Output: {(OUTPUT_DIR / company.replace(' ', '_'))}")
    print(f"Files ready for review and submission")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
