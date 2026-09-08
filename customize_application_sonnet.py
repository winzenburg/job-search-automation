#!/usr/bin/env python3
"""
Application Customization Engine — Sonnet API Integration
Uses Claude 3.5 Sonnet for intelligent cover letter + resume customization
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from role_targeting import founder_leak_terms, should_apply, targeting_prompt_block

SCRIPT_DIR = Path(__file__).parent
VOICE_GUIDE_PATH = SCRIPT_DIR / "VOICE_GUIDE.md"
MASTER_RESUME_PATH = SCRIPT_DIR / "templates" / "MASTER_RESUME.md"
OUTPUT_DIR = SCRIPT_DIR / "customized_applications"
RECIPIENT_EMAIL = "ryanwinzenburg@gmail.com"


def load_voice_guide():
    """Load the voice/tone guide for Sonnet customization."""
    if VOICE_GUIDE_PATH.exists():
        return VOICE_GUIDE_PATH.read_text()
    else:
        print("[ERROR] Voice guide not found at", VOICE_GUIDE_PATH)
        return ""


def load_master_resume() -> str:
    """Employment-led resume used as the only experience source of truth."""
    if MASTER_RESUME_PATH.exists():
        return MASTER_RESUME_PATH.read_text()
    print("[ERROR] Master resume not found at", MASTER_RESUME_PATH)
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


def _message_text(message) -> str:
    parts = []
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def _complete_with_leak_retry(client, system_prompt, user_prompt, max_tokens):
    """Generate copy, then rewrite once if founder/startup language leaked."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = _strip_fences(_message_text(message))
    leaks = founder_leak_terms(text)
    if not leaks:
        return text

    print(f"[WARN] Founder language leaked ({', '.join(leaks)}); rewriting…")
    retry_prompt = (
        user_prompt
        + "\n\nThe previous draft used these banned terms: "
        + ", ".join(leaks)
        + ". Rewrite the entire document with those removed. "
        "Do not mention founding, startups, or parallel companies."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": retry_prompt}],
    )
    return _strip_fences(_message_text(message))


def call_sonnet_for_cover_letter(
    company,
    job_posting,
    voice_guide,
    openai_api_key=None,
    job_title="",
):
    """
    Call Claude to generate a cover letter aimed at THIS job title.
    """
    import anthropic

    api_key = openai_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set. Cannot call Sonnet.")
        return "[ERROR: API key not configured]"

    title = job_title or company
    print(f"\n[SONNET] Cover letter for {company} — {title}...")

    system_prompt = (
        "You write short, specific cover letters for product design and "
        "design-operations jobs. Follow VOICE_GUIDE and ROLE TARGETING exactly. "
        "Output only the letter — no preamble, no markdown fences."
    )

    user_prompt = f"""VOICE_GUIDE:
{voice_guide}

{targeting_prompt_block(title)}

COMPANY: {company}
JOB TITLE: {title}
JOB URL: {job_posting['url']}

JOB POSTING:
{job_posting['content']}

MASTER RESUME (only source of experience — do not invent employers or metrics):
{load_master_resume()}

Write a 4-paragraph cover letter for this exact role. Sentence one names the job title.
Proof comes from employed roles. Independent consulting is at most one clause.
"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        cover_letter = _complete_with_leak_retry(
            client, system_prompt, user_prompt, max_tokens=1200
        )
        print("[✓] Cover letter generated")
        return cover_letter

    except Exception as e:
        print(f"[ERROR] Sonnet cover letter failed: {e}")
        return f"[Error: {str(e)}]"


def call_sonnet_for_resume(company, job_posting, api_key=None, job_title=""):
    """
    Call Claude to produce a full ATS resume aimed at THIS job title.
    """
    import anthropic

    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set.")
        return "[ERROR: API key not configured]"

    title = job_title or company
    print(f"[SONNET] Resume for {company} — {title}...")

    system_prompt = (
        "You customize one master resume for a single job posting. "
        "You may rewrite the headline and summary, drop irrelevant bullets, "
        "and reorder roles. You may not add employers, invent metrics, or "
        "describe the candidate as a founder. Output markdown resume only."
    )

    user_prompt = f"""{targeting_prompt_block(title)}

COMPANY: {company}
JOB TITLE: {title}

JOB POSTING:
{job_posting['content']}

MASTER RESUME:
{load_master_resume()}

Produce a complete one-to-two page ATS resume:
1. Name / contact from the master resume
2. Headline matching this job title (not a higher title)
3. 3–4 line summary for THIS role family
4. Experience: keep employed roles; trim independent consulting to 2–3 role-relevant bullets; drop the customization notes section
5. Skills trimmed to this posting
6. Integrate posting keywords only where they are true

Output markdown only (headings, bullets). No commentary.
"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resume_text = _complete_with_leak_retry(
            client, system_prompt, user_prompt, max_tokens=4096
        )
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
        print("Usage: python3 customize_application_sonnet.py <company> <job_url> [job_title]")
        print("\nExample:")
        print("  python3 customize_application_sonnet.py Dropbox https://... 'Director, Product Design'")
        print("\nEnvironment:")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)
    
    company = sys.argv[1]
    job_url = sys.argv[2]
    job_title = sys.argv[3] if len(sys.argv) > 3 else ""

    if job_title and not should_apply(job_title):
        print(f"[SKIP] '{job_title}' is outside the design/UX roles we apply to.")
        print("See ROLE_TARGETING.md")
        sys.exit(0)
    
    print(f"\n{'='*70}")
    print("APPLICATION CUSTOMIZATION (role-targeted)")
    print(f"{'='*70}")
    print(f"Company:     {company}")
    print(f"Title:       {job_title or '(from posting)'}")
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
    cover_letter = call_sonnet_for_cover_letter(
        company, job_posting, voice_guide, api_key, job_title=job_title
    )
    print()
    
    # 4. Customize resume
    print("[4/6] Customizing resume via Sonnet...")
    resume_customization = call_sonnet_for_resume(
        company, job_posting, api_key, job_title=job_title
    )
    print()
    
    # 5. Save files
    print("[5/6] Saving customized documents...")
    cl_path, resume_path = save_application(company, cover_letter, resume_customization)
    print()
    
    # 6. Prepare email
    print("[6/6] Preparing email delivery...")
    email_subject = f"Role-targeted application ready: {company}"
    email_body = f"""Hi Ryan,

Materials for {company}{' — ' + job_title if job_title else ''} are ready.

These were generated under the role-targeting rules:
- Employment-led resume (no founder companies)
- Cover letter aimed at this job title, not a higher one
- Independent work framed as consulting, if used at all

Files:
- Cover letter: {cl_path.name}
- Resume: {resume_path.name}

Review before submit. If a sentence could be read as "I'll leave when a company takes off," cut it.

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
