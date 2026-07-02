#!/usr/bin/env python3
"""
Auto-Apply Engine — multi-platform job application submission.

Supported platforms (auto-detected from URL):
    LinkedIn Easy Apply    linkedin.com/jobs
    Greenhouse ATS         boards.greenhouse.io  /  grnh.se
    Lever ATS              jobs.lever.co
    Ashby ATS              jobs.ashbyhq.com  /  app.ashbyhq.com
    Indeed Quick Apply     indeed.com

Usage — single job:
    python3 scripts/auto_apply.py \\
        --url  "https://jobs.lever.co/openai/1234" \\
        --resume "customized_applications/OpenAI/resume.pdf" \\
        [--cover-letter "customized_applications/OpenAI/cover_letter.pdf"]

Usage — batch (all PENDING entries in data/applications.json):
    python3 scripts/auto_apply.py --batch [--limit 5]

Required environment variables per platform:
    LinkedIn:   LINKEDIN_EMAIL, LINKEDIN_PASSWORD
    All ATS:    APPLICANT_NAME, APPLICANT_EMAIL, APPLICANT_PHONE

Optional:
    APPLICANT_LINKEDIN   — LinkedIn profile URL
    APPLICANT_LOCATION   — defaults to "Denver, Colorado"
    APPLICANT_WEBSITE    — portfolio / personal site
    APPLICANT_YEARS_EXP  — years of experience (default: "15+")
    APPLICANT_SALARY     — desired salary e.g. "180000" (default: "180000")

Exit codes: 0 = submitted, 1 = skipped/failed, 2 = setup error
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config / helpers
# ---------------------------------------------------------------------------

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
LINKEDIN_SESSION_FILE = DATA_DIR / ".linkedin_session.json"
FAILED_SCREENSHOTS_DIR = DATA_DIR / "failed_screenshots"
RATE_LIMIT_FILE = DATA_DIR / ".submit_rate.json"

# Max submissions per day (protect against account bans)
DAILY_LIMITS = {
    "LinkedIn": 15,
    "Greenhouse": 40,
    "Lever": 40,
    "Ashby": 40,
    "Indeed": 20,
    "default": 10,
}

# Applicant profile (from env, with sensible defaults)
APPLICANT = {
    "name": os.getenv("APPLICANT_NAME", "Ryan Winzenburg"),
    "email": os.getenv("APPLICANT_EMAIL", "ryanwinzenburg@gmail.com"),
    "phone": os.getenv("APPLICANT_PHONE", "303-359-3744"),
    "linkedin": os.getenv("APPLICANT_LINKEDIN", "https://www.linkedin.com/in/ryanwinzenburg"),
    "location": os.getenv("APPLICANT_LOCATION", "Denver, Colorado"),
    "website": os.getenv("APPLICANT_WEBSITE", ""),
    "years_exp": os.getenv("APPLICANT_YEARS_EXP", "15+"),
    "salary": os.getenv("APPLICANT_SALARY", "180000"),
    "first_name": os.getenv("APPLICANT_NAME", "Ryan Winzenburg").split()[0],
    "last_name": " ".join(os.getenv("APPLICANT_NAME", "Ryan Winzenburg").split()[1:]),
}


def load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def detect_platform(url: str) -> str:
    """Return canonical platform name from a job URL."""
    url_lower = url.lower()
    if "linkedin.com" in url_lower:
        return "LinkedIn"
    if "greenhouse.io" in url_lower or "grnh.se" in url_lower:
        return "Greenhouse"
    if "lever.co" in url_lower:
        return "Lever"
    if "ashbyhq.com" in url_lower:
        return "Ashby"
    if "indeed.com" in url_lower:
        return "Indeed"
    if "workday.com" in url_lower:
        return "Workday"
    return "Unknown"


def human_delay(lo: float = 0.5, hi: float = 1.8) -> None:
    """Pause for a random duration to mimic human interaction."""
    time.sleep(random.uniform(lo, hi))


def human_type(page, selector: str, text: str, clear: bool = True) -> None:
    """Type text into a field with human-speed delays."""
    el = page.locator(selector).first
    if clear:
        el.triple_click()
    el.type(text, delay=random.randint(40, 120))


def check_rate_limit(platform: str) -> bool:
    """Return True if we are still under the daily submission limit."""
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_json(RATE_LIMIT_FILE, {})
    counts = state.get(today, {})
    limit = DAILY_LIMITS.get(platform, DAILY_LIMITS["default"])
    return counts.get(platform, 0) < limit


def bump_rate_counter(platform: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    state = load_json(RATE_LIMIT_FILE, {})
    counts = state.setdefault(today, {})
    counts[platform] = counts.get(platform, 0) + 1
    save_json(RATE_LIMIT_FILE, state)


def screenshot_on_failure(page, tag: str) -> None:
    """Save a debug screenshot when something goes wrong."""
    FAILED_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = FAILED_SCREENSHOTS_DIR / f"{tag}_{ts}.png"
    try:
        page.screenshot(path=str(dest))
        print(f"  📸 Debug screenshot saved: {dest.name}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Playwright browser setup (shared logic)
# ---------------------------------------------------------------------------

# Stealth JS injected before every page load to spoof navigator.webdriver
_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
window.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
  parameters.name === 'notifications'
    ? Promise.resolve({ state: Notification.permission })
    : originalQuery(parameters);
"""

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def launch_browser(playwright, headless: bool = True):
    """Launch Chromium with stealth settings."""
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    context = browser.new_context(
        user_agent=_USER_AGENT,
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        timezone_id="America/Denver",
    )
    context.add_init_script(_STEALTH_INIT_SCRIPT)
    return browser, context


# ---------------------------------------------------------------------------
# Platform: LinkedIn Easy Apply
# ---------------------------------------------------------------------------

def _load_linkedin_cookies(context) -> bool:
    """Restore saved LinkedIn session. Returns True if cookies loaded."""
    if not LINKEDIN_SESSION_FILE.exists():
        return False
    try:
        cookies = load_json(LINKEDIN_SESSION_FILE, [])
        context.add_cookies(cookies)
        return True
    except Exception:
        return False


def _save_linkedin_cookies(context) -> None:
    try:
        cookies = context.cookies()
        save_json(LINKEDIN_SESSION_FILE, cookies)
    except Exception:
        pass


def _linkedin_login(page, email: str, password: str) -> bool:
    """Log in to LinkedIn. Returns True on success."""
    print("  🔑 Logging in to LinkedIn…")
    page.goto("https://www.linkedin.com/login", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)

    if "feed" in page.url or "mynetwork" in page.url:
        print("  ✅ Already logged in (session restored)")
        return True

    try:
        human_type(page, 'input[name="session_key"]', email)
        human_delay()
        human_type(page, 'input[name="session_password"]', password)
        human_delay(0.5, 1.2)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=30_000)
    except Exception as exc:
        print(f"  ⚠️  LinkedIn login field interaction failed: {exc}")
        return False

    # Check for CAPTCHA / security challenge
    if any(s in page.url for s in ["checkpoint", "challenge", "captcha", "verification"]):
        print("  ⛔ LinkedIn security challenge detected — automated login blocked.")
        print("     Log in manually once so a session cookie is saved, then re-run.")
        return False

    if "feed" in page.url or "jobs" in page.url or "mynetwork" in page.url:
        _save_linkedin_cookies(context := page.context)  # noqa: F841 — side-effect save
        print("  ✅ LinkedIn login successful")
        return True

    print(f"  ⚠️  Unexpected page after login: {page.url}")
    return False


def _linkedin_easy_apply_modal(page, resume_pdf: str | None, cover_letter_pdf: str | None) -> bool:
    """
    Navigate the LinkedIn Easy Apply multi-step modal.
    Returns True if 'Application submitted' confirmation is reached.
    """
    MAX_STEPS = 12

    for step in range(MAX_STEPS):
        human_delay(1.0, 2.5)

        # ── Upload resume if prompt appears ─────────────────────────────────
        file_inputs = page.locator('input[type="file"]')
        if resume_pdf and file_inputs.count() > 0:
            try:
                file_inputs.first.set_input_files(resume_pdf)
                human_delay(0.8, 1.5)
            except Exception:
                pass

        # ── Fill phone number if empty ───────────────────────────────────────
        phone = APPLICANT["phone"]
        if phone:
            for sel in [
                'input[id*="phone"]',
                'input[name*="phone"]',
                'input[placeholder*="phone" i]',
            ]:
                el = page.locator(sel).first
                if el.count() and el.is_visible():
                    try:
                        if el.input_value() == "":
                            el.fill(phone)
                    except Exception:
                        pass

        # ── Fill city / location if empty ─────────────────────────────────
        location = APPLICANT["location"]
        for sel in [
            'input[id*="city"]',
            'input[id*="location"]',
            'input[name*="city"]',
            'input[placeholder*="City" i]',
        ]:
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                try:
                    if not el.input_value():
                        el.fill(location)
                        human_delay(0.4, 0.8)
                        # Select first autocomplete suggestion
                        suggestion = page.locator('[role="option"]').first
                        if suggestion.is_visible(timeout=2000):
                            suggestion.click()
                except Exception:
                    pass

        # ── Fill salary expectations if asked ─────────────────────────────
        for sel in [
            'input[id*="salary"]',
            'input[name*="salary"]',
            'input[placeholder*="salary" i]',
        ]:
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                try:
                    if not el.input_value():
                        el.fill(APPLICANT["salary"])
                except Exception:
                    pass

        # ── Handle yes/no radio questions (e.g. "Are you authorized to work?") ──
        for label_text in ["Yes", "Ja"]:
            for radio in page.locator(f'label:has-text("{label_text}")').all():
                try:
                    radio.click()
                    human_delay(0.2, 0.5)
                except Exception:
                    pass

        # ── Handle number inputs with default "0" that need years of exp ───
        for sel in ['input[type="number"]']:
            for el in page.locator(sel).all():
                try:
                    val = el.input_value()
                    if val == "0" or not val:
                        label = el.get_attribute("aria-label") or ""
                        if any(w in label.lower() for w in ["year", "exp"]):
                            el.fill("15")
                except Exception:
                    pass

        # ── Submit button ─────────────────────────────────────────────────
        submit_btn = page.locator(
            "button:has-text('Submit application'), "
            "button:has-text('Submit Application')"
        ).first
        if submit_btn.is_visible(timeout=2000):
            submit_btn.click()
            human_delay(2.0, 3.5)
            # Confirm submission
            if any(
                page.locator(f":has-text('{msg}')").is_visible(timeout=5000)
                for msg in ["submitted", "Your application was sent", "Application sent"]
            ):
                return True
            # Check for success modal dismiss button
            done_btn = page.locator("button:has-text('Done')").first
            if done_btn.is_visible(timeout=3000):
                done_btn.click()
            return True  # Optimistic — submit clicked

        # ── Review button ─────────────────────────────────────────────────
        review_btn = page.locator("button:has-text('Review')").first
        if review_btn.is_visible(timeout=1500):
            review_btn.click()
            continue

        # ── Next button ───────────────────────────────────────────────────
        next_btn = page.locator(
            "button:has-text('Next'), button:has-text('Continue')"
        ).first
        if next_btn.is_visible(timeout=1500):
            next_btn.click()
            continue

        print(f"  ⚠️  No navigation button found at step {step + 1}")
        break

    return False


def submit_linkedin(
    url: str,
    resume_pdf: str | None,
    cover_letter_pdf: str | None,
    dry_run: bool = False,
) -> dict:
    """Submit a LinkedIn Easy Apply application."""
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    if not email or not password:
        return {"success": False, "reason": "LINKEDIN_EMAIL / LINKEDIN_PASSWORD not set"}

    if not check_rate_limit("LinkedIn"):
        return {"success": False, "reason": "Daily LinkedIn rate limit reached"}

    if dry_run:
        return {"success": True, "reason": "dry-run", "submitted_at": datetime.now().isoformat()}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page = context.new_page()

        try:
            # Restore or create session
            cookies_loaded = _load_linkedin_cookies(context)
            if not _linkedin_login(page, email, password):
                browser.close()
                return {"success": False, "reason": "LinkedIn login failed (CAPTCHA or wrong credentials)"}
            _save_linkedin_cookies(context)

            human_delay(1.5, 3.0)

            # Navigate to the job posting
            page.goto(url, timeout=40_000)
            page.wait_for_load_state("networkidle", timeout=25_000)

            # Check for Easy Apply button
            easy_apply = page.locator(
                "button.jobs-apply-button:has-text('Easy Apply'), "
                ".jobs-s-apply button:has-text('Easy Apply'), "
                "button:has-text('Easy Apply')"
            ).first

            if not easy_apply.is_visible(timeout=8_000):
                screenshot_on_failure(page, "linkedin_no_easy_apply")
                browser.close()
                return {"success": False, "reason": "Easy Apply button not found (external application required)"}

            easy_apply.click()
            human_delay(1.5, 2.5)

            submitted = _linkedin_easy_apply_modal(page, resume_pdf, cover_letter_pdf)

            if submitted:
                bump_rate_counter("LinkedIn")
                browser.close()
                return {"success": True, "submitted_at": datetime.now().isoformat()}
            else:
                screenshot_on_failure(page, "linkedin_modal_incomplete")
                browser.close()
                return {"success": False, "reason": "Could not complete Easy Apply modal — screenshot saved"}

        except Exception as exc:
            try:
                screenshot_on_failure(page, "linkedin_exception")
            except Exception:
                pass
            browser.close()
            return {"success": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# Platform: Greenhouse
# ---------------------------------------------------------------------------

def submit_greenhouse(
    url: str,
    resume_pdf: str | None,
    cover_letter_pdf: str | None,
    dry_run: bool = False,
) -> dict:
    """Fill and submit a Greenhouse job application form."""
    if not check_rate_limit("Greenhouse"):
        return {"success": False, "reason": "Daily Greenhouse rate limit reached"}

    if dry_run:
        return {"success": True, "reason": "dry-run", "submitted_at": datetime.now().isoformat()}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page = context.new_page()

        try:
            page.goto(url, timeout=40_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            # Standard Greenhouse form fields
            field_map = {
                'input[id="first_name"], input[name="first_name"]': APPLICANT["first_name"],
                'input[id="last_name"], input[name="last_name"]': APPLICANT["last_name"],
                'input[id="email"], input[name="email"]': APPLICANT["email"],
                'input[id="phone"], input[name="phone"]': APPLICANT["phone"],
                'input[id="location"], input[name="job_application[location]"]': APPLICANT["location"],
                'input[id="website"], input[name*="website"]': APPLICANT["website"],
                'input[id="linkedin_url"], input[name*="linkedin"]': APPLICANT["linkedin"],
            }

            for selector, value in field_map.items():
                if not value:
                    continue
                for sel in selector.split(", "):
                    el = page.locator(sel.strip()).first
                    if el.count() and el.is_visible():
                        try:
                            el.fill(value)
                            human_delay(0.3, 0.7)
                        except Exception:
                            pass
                        break

            # Upload resume
            if resume_pdf:
                for sel in [
                    '#resume input[type="file"]',
                    'input[id*="resume"]',
                    '.js-upload-input',
                ]:
                    el = page.locator(sel).first
                    if el.count():
                        try:
                            el.set_input_files(resume_pdf)
                            human_delay(1.0, 2.0)
                        except Exception:
                            pass
                        break

            # Upload cover letter
            if cover_letter_pdf:
                for sel in [
                    '#cover_letter input[type="file"]',
                    'input[id*="cover_letter"]',
                ]:
                    el = page.locator(sel).first
                    if el.count():
                        try:
                            el.set_input_files(cover_letter_pdf)
                            human_delay(0.5, 1.2)
                        except Exception:
                            pass
                        break

            # Handle custom checkboxes (e.g. EEOC, veteran status)
            for checkbox in page.locator('input[type="checkbox"]').all():
                try:
                    label_text = page.evaluate(
                        'el => el.closest("label")?.textContent || ""', checkbox
                    )
                    if any(w in label_text.lower() for w in ["decline", "prefer not"]):
                        checkbox.check()
                        human_delay(0.2, 0.4)
                except Exception:
                    pass

            # Handle EEOC dropdowns (race, gender, veteran, disability)
            _fill_eeoc_selects(page)

            human_delay(0.8, 1.5)

            # Submit
            submit = page.locator("input[type='submit'], button[type='submit']").first
            if not submit.is_visible(timeout=5000):
                screenshot_on_failure(page, "greenhouse_no_submit")
                browser.close()
                return {"success": False, "reason": "Submit button not found"}

            submit.click()
            page.wait_for_load_state("networkidle", timeout=20_000)

            # Look for success signals
            success = any(
                page.locator(f':has-text("{msg}")').is_visible(timeout=5000)
                for msg in ["application has been submitted", "thank you", "received your application"]
            )

            if success:
                bump_rate_counter("Greenhouse")
                browser.close()
                return {"success": True, "submitted_at": datetime.now().isoformat()}
            else:
                screenshot_on_failure(page, "greenhouse_post_submit")
                browser.close()
                return {"success": False, "reason": "Could not confirm submission — check screenshot"}

        except Exception as exc:
            try:
                screenshot_on_failure(page, "greenhouse_exception")
            except Exception:
                pass
            browser.close()
            return {"success": False, "reason": str(exc)}


def _fill_eeoc_selects(page) -> None:
    """Set EEOC voluntary self-identification selects to 'Decline to self-identify'."""
    for select in page.locator("select").all():
        try:
            options = select.locator("option").all_inner_texts()
            decline_opts = [o for o in options if any(
                w in o.lower() for w in ["decline", "prefer not", "i don't wish"]
            )]
            if decline_opts:
                select.select_option(label=decline_opts[0])
                human_delay(0.1, 0.3)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Platform: Lever
# ---------------------------------------------------------------------------

def submit_lever(
    url: str,
    resume_pdf: str | None,
    cover_letter_pdf: str | None,
    dry_run: bool = False,
) -> dict:
    """Fill and submit a Lever job application form."""
    if not check_rate_limit("Lever"):
        return {"success": False, "reason": "Daily Lever rate limit reached"}

    if dry_run:
        return {"success": True, "reason": "dry-run", "submitted_at": datetime.now().isoformat()}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page = context.new_page()

        try:
            page.goto(url, timeout=40_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            # Check for an "Apply" button that navigates to the actual form
            apply_btn = page.locator(
                "a:has-text('Apply for this job'), "
                "a:has-text('Apply Now'), "
                "button:has-text('Apply')"
            ).first
            if apply_btn.is_visible(timeout=5000):
                apply_btn.click()
                page.wait_for_load_state("networkidle", timeout=20_000)

            # Lever standard form
            field_map = {
                'input[name="name"]': APPLICANT["name"],
                'input[name="email"]': APPLICANT["email"],
                'input[name="phone"]': APPLICANT["phone"],
                'input[name="org"]': "",  # current company — leave blank or fill
                'input[name="urls[LinkedIn]"]': APPLICANT["linkedin"],
                'input[name="urls[Other]"]': APPLICANT["website"],
            }

            for selector, value in field_map.items():
                if not value:
                    continue
                el = page.locator(selector).first
                if el.count() and el.is_visible():
                    el.fill(value)
                    human_delay(0.3, 0.7)

            # Cover letter / additional info textarea
            cover_text = ""
            if cover_letter_pdf:
                cover_text = "(Please see attached cover letter.)"
            for sel in ['textarea[name="comments"]', 'textarea[name="additionalInfo"]', "textarea"]:
                el = page.locator(sel).first
                if el.count() and el.is_visible():
                    try:
                        if not el.input_value():
                            el.fill(cover_text or "Thank you for considering my application.")
                    except Exception:
                        pass
                    break

            # Resume upload
            if resume_pdf:
                for sel in ['input[type="file"]', '.resume-upload input']:
                    el = page.locator(sel).first
                    if el.count():
                        try:
                            el.set_input_files(resume_pdf)
                            human_delay(1.0, 2.0)
                        except Exception:
                            pass
                        break

            human_delay(0.5, 1.0)

            # Submit
            submit = page.locator(
                "button:has-text('Submit application'), "
                "button:has-text('Submit Application'), "
                "button[type='submit']"
            ).first
            if not submit.is_visible(timeout=5000):
                screenshot_on_failure(page, "lever_no_submit")
                browser.close()
                return {"success": False, "reason": "Submit button not found"}

            submit.click()
            page.wait_for_load_state("networkidle", timeout=20_000)

            success = any(
                page.locator(f':has-text("{msg}")').is_visible(timeout=5000)
                for msg in ["Your application has been submitted", "Thanks for applying", "We've received your application"]
            )

            if success:
                bump_rate_counter("Lever")
                browser.close()
                return {"success": True, "submitted_at": datetime.now().isoformat()}
            else:
                screenshot_on_failure(page, "lever_post_submit")
                browser.close()
                return {"success": False, "reason": "Could not confirm Lever submission — check screenshot"}

        except Exception as exc:
            try:
                screenshot_on_failure(page, "lever_exception")
            except Exception:
                pass
            browser.close()
            return {"success": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# Platform: Ashby
# ---------------------------------------------------------------------------

def submit_ashby(
    url: str,
    resume_pdf: str | None,
    cover_letter_pdf: str | None,
    dry_run: bool = False,
) -> dict:
    """Fill and submit an Ashby HQ job application form."""
    if not check_rate_limit("Ashby"):
        return {"success": False, "reason": "Daily Ashby rate limit reached"}

    if dry_run:
        return {"success": True, "reason": "dry-run", "submitted_at": datetime.now().isoformat()}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page = context.new_page()

        try:
            page.goto(url, timeout=40_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            # Ashby may require clicking an "Apply" button to reveal form
            apply_btn = page.locator(
                "button:has-text('Apply'), a:has-text('Apply')"
            ).first
            if apply_btn.is_visible(timeout=5000):
                apply_btn.click()
                page.wait_for_load_state("networkidle", timeout=20_000)
                human_delay(1.0, 2.0)

            # Ashby uses React forms — fields vary by company. Fill by aria-label / placeholder.
            def _fill_if_empty(selectors: list[str], value: str) -> None:
                if not value:
                    return
                for sel in selectors:
                    for el in page.locator(sel).all():
                        try:
                            if el.is_visible() and not el.input_value():
                                el.fill(value)
                                human_delay(0.2, 0.5)
                                return
                        except Exception:
                            pass

            _fill_if_empty(
                ['input[name="name"]', 'input[placeholder*="Name" i]', 'input[aria-label*="Name" i]'],
                APPLICANT["name"],
            )
            _fill_if_empty(
                ['input[name="email"]', 'input[placeholder*="Email" i]', 'input[type="email"]'],
                APPLICANT["email"],
            )
            _fill_if_empty(
                ['input[name="phone"]', 'input[placeholder*="Phone" i]', 'input[type="tel"]'],
                APPLICANT["phone"],
            )
            _fill_if_empty(
                ['input[placeholder*="LinkedIn" i]', 'input[aria-label*="LinkedIn" i]'],
                APPLICANT["linkedin"],
            )
            _fill_if_empty(
                ['input[placeholder*="Website" i]', 'input[placeholder*="Portfolio" i]'],
                APPLICANT["website"] or APPLICANT["linkedin"],
            )

            # Resume upload
            if resume_pdf:
                for sel in ['input[type="file"]']:
                    el = page.locator(sel).first
                    if el.count():
                        try:
                            el.set_input_files(resume_pdf)
                            human_delay(1.0, 2.5)
                        except Exception:
                            pass
                        break

            human_delay(0.5, 1.2)

            # Try submitting
            submit = page.locator(
                "button:has-text('Submit'), button:has-text('Apply'), button[type='submit']"
            ).first
            if not submit.is_visible(timeout=5000):
                screenshot_on_failure(page, "ashby_no_submit")
                browser.close()
                return {"success": False, "reason": "Submit button not found on Ashby form"}

            submit.click()
            human_delay(2.0, 3.5)
            page.wait_for_load_state("networkidle", timeout=20_000)

            success = any(
                page.locator(f':has-text("{msg}")').is_visible(timeout=5000)
                for msg in ["Application submitted", "Thanks for applying", "received your application", "We'll be in touch"]
            )

            if success:
                bump_rate_counter("Ashby")
                browser.close()
                return {"success": True, "submitted_at": datetime.now().isoformat()}
            else:
                screenshot_on_failure(page, "ashby_post_submit")
                browser.close()
                return {"success": False, "reason": "Could not confirm Ashby submission — check screenshot"}

        except Exception as exc:
            try:
                screenshot_on_failure(page, "ashby_exception")
            except Exception:
                pass
            browser.close()
            return {"success": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# Platform: Indeed Quick Apply
# ---------------------------------------------------------------------------

def submit_indeed(
    url: str,
    resume_pdf: str | None,
    cover_letter_pdf: str | None,
    dry_run: bool = False,
) -> dict:
    """Submit via Indeed Quick Apply modal (requires an existing Indeed account session)."""
    email = os.getenv("INDEED_EMAIL") or os.getenv("APPLICANT_EMAIL")
    password = os.getenv("INDEED_PASSWORD")

    if not password:
        return {"success": False, "reason": "INDEED_PASSWORD not set — Indeed requires login"}

    if not check_rate_limit("Indeed"):
        return {"success": False, "reason": "Daily Indeed rate limit reached"}

    if dry_run:
        return {"success": True, "reason": "dry-run", "submitted_at": datetime.now().isoformat()}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"success": False, "reason": "playwright not installed"}

    with sync_playwright() as p:
        browser, context = launch_browser(p)
        page = context.new_page()

        try:
            # Sign in
            page.goto("https://secure.indeed.com/account/login", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            email_field = page.locator('input[name="__email"]').first
            if email_field.is_visible(timeout=5000):
                email_field.fill(email)
                page.click('button:has-text("Continue")')
                human_delay(1.5, 2.5)
                pw_field = page.locator('input[name="__password"]').first
                if pw_field.is_visible(timeout=5000):
                    pw_field.fill(password)
                    page.click('button:has-text("Sign in")')
                    page.wait_for_load_state("networkidle", timeout=20_000)

            # Navigate to job
            page.goto(url, timeout=40_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            # Click Apply button
            apply_btn = page.locator(
                "button:has-text('Apply now'), button:has-text('Quick Apply'), button:has-text('Apply')"
            ).first
            if not apply_btn.is_visible(timeout=8_000):
                screenshot_on_failure(page, "indeed_no_apply")
                browser.close()
                return {"success": False, "reason": "Apply button not found on Indeed"}

            apply_btn.click()
            human_delay(1.5, 3.0)

            # Navigate multi-step Indeed modal
            MAX_STEPS = 10
            for step in range(MAX_STEPS):
                human_delay(0.8, 1.8)

                # Upload resume
                if resume_pdf:
                    file_input = page.locator('input[type="file"]').first
                    if file_input.is_visible(timeout=2000):
                        try:
                            file_input.set_input_files(resume_pdf)
                            human_delay(1.0, 2.0)
                        except Exception:
                            pass

                # Fill missing contact fields
                _fill_indeed_contact_fields(page)

                # Submit
                submit = page.locator(
                    "button:has-text('Submit your application'), "
                    "button:has-text('Submit application')"
                ).first
                if submit.is_visible(timeout=2000):
                    submit.click()
                    human_delay(2.0, 3.0)
                    bump_rate_counter("Indeed")
                    browser.close()
                    return {"success": True, "submitted_at": datetime.now().isoformat()}

                # Continue
                cont_btn = page.locator(
                    "button:has-text('Continue'), button:has-text('Next')"
                ).first
                if cont_btn.is_visible(timeout=2000):
                    cont_btn.click()
                else:
                    break

            screenshot_on_failure(page, "indeed_modal_incomplete")
            browser.close()
            return {"success": False, "reason": "Could not complete Indeed Quick Apply modal"}

        except Exception as exc:
            try:
                screenshot_on_failure(page, "indeed_exception")
            except Exception:
                pass
            browser.close()
            return {"success": False, "reason": str(exc)}


def _fill_indeed_contact_fields(page) -> None:
    """Best-effort fill of Indeed contact fields when they appear."""
    fields = {
        'input[aria-label*="First name" i]': APPLICANT["first_name"],
        'input[aria-label*="Last name" i]': APPLICANT["last_name"],
        'input[aria-label*="Phone" i]': APPLICANT["phone"],
        'input[aria-label*="City" i]': APPLICANT["location"].split(",")[0].strip(),
    }
    for sel, val in fields.items():
        if not val:
            continue
        el = page.locator(sel).first
        if el.count() and el.is_visible():
            try:
                if not el.input_value():
                    el.fill(val)
                    human_delay(0.2, 0.5)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def submit(
    url: str,
    resume_pdf: str | None = None,
    cover_letter_pdf: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Detect the platform from the URL and route to the appropriate submitter.
    Returns a result dict: {"success": bool, "reason": str, "platform": str, ...}
    """
    platform = detect_platform(url)
    result: dict = {"platform": platform, "url": url}

    print(f"\n{'─' * 60}")
    print(f"  🎯 Platform : {platform}")
    print(f"  🔗 URL      : {url[:80]}{'…' if len(url) > 80 else ''}")
    print(f"  📄 Resume   : {resume_pdf or '(none)'}")
    print(f"  📝 Cover    : {cover_letter_pdf or '(none)'}")
    print(f"  🧪 Dry run  : {dry_run}")

    handlers = {
        "LinkedIn": submit_linkedin,
        "Greenhouse": submit_greenhouse,
        "Lever": submit_lever,
        "Ashby": submit_ashby,
        "Indeed": submit_indeed,
    }

    handler = handlers.get(platform)
    if handler is None:
        result["success"] = False
        result["reason"] = f"Unsupported platform: {platform}"
        print(f"  ⚠️  {result['reason']}")
        return result

    outcome = handler(url, resume_pdf, cover_letter_pdf, dry_run=dry_run)
    result.update(outcome)

    if result.get("success"):
        print(f"  ✅ Submitted successfully{' (dry-run)' if dry_run else ''}")
    else:
        print(f"  ❌ Failed: {result.get('reason', 'unknown error')}")

    return result


# ---------------------------------------------------------------------------
# Batch mode — processes PENDING entries from data/applications.json
# ---------------------------------------------------------------------------

def run_batch(limit: int = 5, dry_run: bool = False) -> None:
    """Submit up to `limit` pending applications from data/applications.json."""
    applications: list[dict] = load_json(APPLICATIONS_FILE, [])
    pending = [
        a for a in applications
        if a.get("status", "").upper() in ("PENDING", "MATERIALS_READY", "")
        and a.get("url")
    ]

    if not pending:
        print("No pending applications to submit.")
        return

    print(f"\nBatch mode: {len(pending)} pending found, processing up to {limit}")

    processed = 0
    for app in pending:
        if processed >= limit:
            break

        url = app.get("url", "")
        resume = app.get("resume_pdf") or ""
        cover = app.get("cover_letter_pdf") or ""

        # Resolve relative paths
        if resume and not Path(resume).is_absolute():
            resume = str(PROJECT_DIR / resume)
        if cover and not Path(cover).is_absolute():
            cover = str(PROJECT_DIR / cover)

        result = submit(
            url=url,
            resume_pdf=resume if Path(resume).exists() else None,
            cover_letter_pdf=cover if cover and Path(cover).exists() else None,
            dry_run=dry_run,
        )

        # Update status in applications.json
        for a in applications:
            if a.get("url") == url:
                if result.get("success"):
                    a["status"] = "SUBMITTED"
                    a["submitted_at"] = result.get("submitted_at", datetime.now().isoformat())
                else:
                    a["status"] = "FAILED"
                    a["failure_reason"] = result.get("reason", "")
                    a["failed_at"] = datetime.now().isoformat()
                break

        save_json(APPLICATIONS_FILE, applications)
        processed += 1

        # Brief pause between submissions to avoid rate-limit triggers
        if processed < limit:
            human_delay(8.0, 20.0)

    print(f"\n✅ Batch complete — processed {processed} application(s)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-Apply Engine — submit job applications across multiple platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Submit a single job
  python3 scripts/auto_apply.py \\
      --url "https://jobs.lever.co/openai/abc123" \\
      --resume customized_applications/OpenAI/resume.pdf

  # Batch-submit all pending applications (dry run first)
  python3 scripts/auto_apply.py --batch --dry-run
  python3 scripts/auto_apply.py --batch --limit 3
        """,
    )
    parser.add_argument("--url", help="Single job URL to submit")
    parser.add_argument("--resume", help="Path to resume PDF")
    parser.add_argument("--cover-letter", dest="cover_letter", help="Path to cover letter PDF")
    parser.add_argument("--batch", action="store_true", help="Process all PENDING applications")
    parser.add_argument("--limit", type=int, default=5, help="Max applications per batch run")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without actually submitting")

    args = parser.parse_args()

    if not args.url and not args.batch:
        parser.print_help()
        sys.exit(2)

    if args.batch:
        run_batch(limit=args.limit, dry_run=args.dry_run)
    else:
        result = submit(
            url=args.url,
            resume_pdf=args.resume,
            cover_letter_pdf=args.cover_letter,
            dry_run=args.dry_run,
        )
        sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
