#!/usr/bin/env python3
"""
Daily Report Builder

Runs after the scanner, generator, and auto-submit steps are all done.
Reads their output and produces:
  1. email_report.html  -- rich HTML email sent via GitHub Actions
  2. Telegram message   -- plain-text summary pushed to your Telegram chat

Environment variables:
    TELEGRAM_BOT_TOKEN  -- from @BotFather
    TELEGRAM_CHAT_ID    -- your numeric chat ID
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
APPLICATIONS_FILE = DATA_DIR / "applications.json"
PENDING_OUTREACH_DIR = DATA_DIR / "outreach" / "pending"
SCANNER_STATE = PROJECT_DIR / "scanner_state.json"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def todays_applications(applications: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split applications into submitted today and materials-ready (not yet submitted)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    submitted_today = [
        a for a in applications
        if a.get("status", "").upper() == "SUBMITTED"
        and a.get("submitted_at", "").startswith(today)
    ]
    materials_ready = [
        a for a in applications
        if a.get("status", "").upper() in
        ("MATERIALS_READY", "PENDING", "FAILED", "MANUAL_REQUIRED", "")
    ]
    return submitted_today, materials_ready


def new_discoveries(state: dict) -> list[dict]:
    """Jobs added to scanner state today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    opps = list(state.get("opportunities", {}).values())
    return [o for o in opps if o.get("foundDate", "").startswith(today)]


def load_pending_outreach() -> list[dict]:
    messages = []
    if PENDING_OUTREACH_DIR.exists():
        for f in sorted(PENDING_OUTREACH_DIR.glob("*.json")):
            try:
                messages.append(json.load(open(f)))
            except Exception:
                pass
    return messages


# ---------------------------------------------------------------------------
# HTML email
# ---------------------------------------------------------------------------

_STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
       font-size: 16px; line-height: 1.6; color: #26262b; max-width: 600px;
       margin: 0 auto; padding: 32px 24px; background: #ffffff; }
p { margin: 0 0 16px; }
h2 { font-size: 17px; font-weight: 600; color: #111; margin: 32px 0 12px; }
.greeting { font-size: 18px; margin-bottom: 20px; }
.summary { color: #4b5563; margin-bottom: 28px; }
.job { margin-bottom: 18px; padding-left: 14px; border-left: 3px solid #e5e7eb; }
.job.submitted { border-left-color: #22c55e; }
.job.pending { border-left-color: #eab308; }
.job.failed { border-left-color: #ef4444; }
.job a { color: #2563eb; text-decoration: none; font-weight: 600; font-size: 15.5px; }
.job .meta-line { color: #6b7280; font-size: 13.5px; margin-top: 2px; }
.note { color: #6b7280; font-size: 14.5px; margin-bottom: 16px; }
.outreach-block { margin-bottom: 24px; }
.outreach-block .who { font-weight: 600; margin-bottom: 6px; }
.outreach-block .who .company { font-weight: 400; color: #6b7280; }
.msg { font-size: 14px; line-height: 1.55; white-space: pre-wrap; background: #f7f7f8;
       border-radius: 8px; padding: 14px 16px; color: #33333a; }
.more { color: #9ca3af; font-size: 14px; font-style: italic; margin-top: 4px; }
.signoff { color: #6b7280; font-size: 14px; margin-top: 36px; }
.footer { font-size: 12.5px; color: #b0b0b8; margin-top: 28px; }
.footer a { color: #9ca3af; }
"""


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _job_line(item: dict, css_class: str, sub: str) -> str:
    company = item.get("company", "a company")
    title = item.get("title", "a role")
    url = item.get("url", "#")
    return f"""<div class="job {css_class}">
  <a href="{url}">{company} &ndash; {title}</a>
  <div class="meta-line">{sub}</div>
</div>"""


def build_html_report(
    submitted: list[dict],
    materials_ready: list[dict],
    discoveries: list[dict],
    outreach: list[dict],
    run_date: str,
) -> str:
    day_label = run_date.split(" ")[0]

    # Friendly opening summary, written as plain sentences
    summary_bits = []
    if submitted:
        summary_bits.append(f"applied to {_plural(len(submitted), 'job')} for you")
    if discoveries:
        summary_bits.append(f"found {_plural(len(discoveries), 'new opening')}")
    if outreach:
        summary_bits.append(f"{_plural(len(outreach), 'outreach message')} ready whenever you want to send them")

    if summary_bits:
        summary_text = "Here's where things stand: " + ", ".join(summary_bits) + "."
    else:
        summary_text = "Quiet day out there, nothing new to report yet."

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{_STYLE}</style></head>
<body>
<p class="greeting">Morning, Ryan.</p>
<p class="summary">{summary_text}</p>
"""

    # Submitted today
    if submitted:
        html += "<h2>Applications sent today</h2>"
        for a in submitted:
            sub = a.get("submitted_at", "")[:16].replace("T", " ") + " UTC"
            html += _job_line(a, "submitted", sub)
    else:
        html += "<h2>Applications sent today</h2>"
        html += '<p class="note">Nothing went out automatically today. That usually means auto-submit isn\'t finding Easy Apply buttons or ATS forms it recognizes, or nothing new matched the search criteria.</p>'

    # Materials ready (not yet submitted)
    if materials_ready:
        html += "<h2>Waiting on you</h2>"
        html += '<p class="note">These have a resume and cover letter ready but couldn\'t be auto-submitted. Worth a quick look.</p>'
        for a in materials_ready[:10]:
            status = a.get("status", "").upper()
            if status == "FAILED":
                css, label = "failed", "couldn't complete the form"
            elif status == "MANUAL_REQUIRED":
                css, label = "pending", "no auto-apply for this source, apply manually"
            else:
                css, label = "pending", "materials ready"
            html += _job_line(a, css, label)
        if len(materials_ready) > 10:
            html += f'<p class="more">...and {len(materials_ready) - 10} more in APPLICATIONS.md.</p>'

    # New discoveries
    if discoveries:
        html += f"<h2>New roles worth a look ({len(discoveries)})</h2>"
        for o in discoveries[:15]:
            location = o.get("location", "Remote")
            source = o.get("source", "")
            sub = f"{location} &middot; via {source}" if source else location
            html += _job_line(o, "", sub)
        if len(discoveries) > 15:
            html += f'<p class="more">...and {len(discoveries) - 15} more.</p>'

    # Outreach queue
    if outreach:
        html += f"<h2>Messages ready to send ({len(outreach)})</h2>"
        html += '<p class="note">A good rhythm is 5 to 8 a day so LinkedIn doesn\'t flag the activity. Here are a few from the queue:</p>'
        for m in outreach[:5]:
            name = m.get("contact_name", "")
            company = m.get("company_name", "")
            msg_text = m.get("message", "").strip()
            html += f"""<div class="outreach-block">
  <div class="who">{name} <span class="company">at {company}</span></div>
  <div class="msg">{msg_text}</div>
</div>"""
        if len(outreach) > 5:
            html += f'<p class="more">The rest are in LINKEDIN_OUTREACH.md, {len(outreach) - 5} more waiting.</p>'

    html += f"""
<p class="signoff">That's everything for {day_label}. Talk tomorrow.</p>
<p class="footer">Sent by your job search automation &middot; <a href="https://github.com/winzenburg/job-search-automation">view the repo</a></p>
</body></html>"""
    return html


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"  Telegram send failed: {exc}")
        return False


def build_telegram_message(
    submitted: list[dict],
    materials_ready: list[dict],
    discoveries: list[dict],
    outreach: list[dict],
    run_date: str,
) -> str:
    day_label = run_date.split(" ")[0]
    lines = [f"Morning. Here's the rundown for {day_label}.", ""]

    if submitted:
        lines.append(f"Applied to {len(submitted)} for you:")
        for a in submitted:
            lines.append(f"  {a.get('company','?')} - {a.get('title','?')}")
        lines.append("")
    else:
        lines.append("Nothing auto-submitted today.")
        lines.append("")

    if materials_ready:
        lines.append(f"{len(materials_ready)} waiting on you to submit manually:")
        for a in materials_ready[:5]:
            lines.append(f"  {a.get('company','?')} - {a.get('title','?')}")
        if len(materials_ready) > 5:
            lines.append(f"  ...and {len(materials_ready) - 5} more")
        lines.append("")

    if discoveries:
        lines.append(f"Found {len(discoveries)} new opening(s):")
        for o in discoveries[:5]:
            lines.append(f"  {o.get('company','?')} - {o.get('title','?')}")
        if len(discoveries) > 5:
            lines.append(f"  ...and {len(discoveries) - 5} more")
        lines.append("")

    if outreach:
        lines.append(f"{len(outreach)} outreach messages are ready whenever you want to send them.")
        lines.append("Aim for 5-8 a day so LinkedIn doesn't flag it.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Building report for {run_date}...")

    applications = load_json(APPLICATIONS_FILE, [])
    state = load_json(SCANNER_STATE, {})
    outreach = load_pending_outreach()

    submitted, materials_ready = todays_applications(applications)
    discoveries = new_discoveries(state)

    # Build and write HTML email
    html = build_html_report(submitted, materials_ready, discoveries, outreach, run_date)
    report_path = PROJECT_DIR / "email_report.html"
    report_path.write_text(html)
    print(f"  HTML report written to {report_path.name}")
    print(f"  Submitted: {len(submitted)} | Ready: {len(materials_ready)} | "
          f"Discovered: {len(discoveries)} | Outreach: {len(outreach)}")

    # Send Telegram if credentials are set
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if token and chat_id:
        msg = build_telegram_message(submitted, materials_ready, discoveries, outreach, run_date)
        ok = send_telegram(token, chat_id, msg)
        print(f"  Telegram: {'sent' if ok else 'failed'}")
    else:
        print("  Telegram: skipped (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set)")


if __name__ == "__main__":
    main()
