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
        if a.get("status", "").upper() in ("MATERIALS_READY", "PENDING", "FAILED", "")
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
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       font-size: 15px; color: #1a1a1a; max-width: 640px; margin: 0 auto; padding: 24px; }
h1  { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
h2  { font-size: 16px; font-weight: 600; margin: 24px 0 10px; border-bottom: 1px solid #e5e7eb;
      padding-bottom: 6px; }
.meta { font-size: 13px; color: #6b7280; margin-bottom: 24px; }
.card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 10px; }
.card a { color: #2563eb; text-decoration: none; font-weight: 600; }
.card .sub { font-size: 13px; color: #6b7280; margin-top: 4px; }
.badge { display: inline-block; font-size: 12px; font-weight: 600; border-radius: 4px;
         padding: 2px 8px; margin-right: 6px; }
.badge-green  { background: #dcfce7; color: #166534; }
.badge-yellow { background: #fef9c3; color: #854d0e; }
.badge-gray   { background: #f3f4f6; color: #374151; }
.badge-red    { background: #fee2e2; color: #991b1b; }
.msg { font-family: monospace; font-size: 13px; white-space: pre-wrap;
       background: #f3f4f6; border-radius: 6px; padding: 12px; margin-top: 8px;
       color: #374151; border: 1px solid #e5e7eb; }
.empty { font-size: 14px; color: #9ca3af; font-style: italic; }
"""


def _badge(text: str, color: str) -> str:
    return f'<span class="badge badge-{color}">{text}</span>'


def build_html_report(
    submitted: list[dict],
    materials_ready: list[dict],
    discoveries: list[dict],
    outreach: list[dict],
    run_date: str,
) -> str:
    submitted_count = len(submitted)
    total_apps = submitted_count + len(materials_ready)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{_STYLE}</style></head>
<body>
<h1>Antigravity Daily Report</h1>
<p class="meta">{run_date} &mdash;
  {submitted_count} submitted today &bull;
  {len(materials_ready)} pending &bull;
  {len(discoveries)} new discoveries &bull;
  {len(outreach)} outreach messages ready to send
</p>
"""

    # Submitted today
    html += '<h2>Submitted Today</h2>'
    if submitted:
        for a in submitted:
            status_badge = _badge("Submitted", "green")
            platform = a.get("source", "")
            html += f"""<div class="card">
  {status_badge}{_badge(platform, "gray")}
  <a href="{a.get('url','#')}">{a.get('company','?')} &mdash; {a.get('title','?')}</a>
  <div class="sub">Submitted {a.get('submitted_at','')[:16].replace('T', ' ')} UTC</div>
</div>"""
    else:
        html += '<p class="empty">Nothing submitted today. Add LINKEDIN_PASSWORD and other secrets to enable auto-submit.</p>'

    # Materials ready (not yet submitted)
    html += '<h2>Materials Ready (Need Manual Submit)</h2>'
    if materials_ready:
        for a in materials_ready[:10]:
            status = a.get("status", "").upper()
            color = "red" if status == "FAILED" else "yellow"
            label = "Failed" if status == "FAILED" else "Ready"
            html += f"""<div class="card">
  {_badge(label, color)}{_badge(a.get('source',''), 'gray')}
  <a href="{a.get('url','#')}">{a.get('company','?')} &mdash; {a.get('title','?')}</a>
  <div class="sub">Generated {a.get('applied_at','')[:10]}</div>
</div>"""
        if len(materials_ready) > 10:
            html += f'<p class="empty">...and {len(materials_ready) - 10} more. See APPLICATIONS.md for the full list.</p>'
    else:
        html += '<p class="empty">Nothing pending.</p>'

    # New discoveries
    html += f'<h2>New Jobs Discovered ({len(discoveries)})</h2>'
    if discoveries:
        for o in discoveries[:15]:
            html += f"""<div class="card">
  {_badge(o.get('source',''), 'gray')}
  <a href="{o.get('url','#')}">{o.get('company','?')} &mdash; {o.get('title','?')}</a>
  <div class="sub">{o.get('location','Remote')}</div>
</div>"""
        if len(discoveries) > 15:
            html += f'<p class="empty">...and {len(discoveries) - 15} more.</p>'
    else:
        html += '<p class="empty">No new jobs found today.</p>'

    # Outreach queue
    html += f'<h2>LinkedIn Outreach Queue ({len(outreach)} messages)</h2>'
    if outreach:
        html += '<p style="font-size:13px;color:#6b7280;margin-bottom:12px;">Send 5-8 per day. Copy each message directly into LinkedIn.</p>'
        for m in outreach[:8]:
            name = m.get("contact_name", "")
            company = m.get("company_name", "")
            title = m.get("contact_title", "")
            msg_text = m.get("message", "").strip()
            html += f"""<div class="card">
  <strong>{name}</strong> &mdash; {title} at {company}
  <div class="msg">{msg_text}</div>
</div>"""
        if len(outreach) > 8:
            html += f'<p class="empty">...showing 8 of {len(outreach)}. See LINKEDIN_OUTREACH.md for all messages.</p>'
    else:
        html += '<p class="empty">No pending outreach messages.</p>'

    html += """
<hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb;">
<p style="font-size:12px;color:#9ca3af;">
  Antigravity Job Search Automation &bull;
  <a href="https://github.com/winzenburg/job-search-automation">View repo</a>
</p>
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
    lines = [
        f"<b>Antigravity Daily Report</b>",
        f"<i>{run_date}</i>",
        "",
    ]

    # Submitted
    if submitted:
        lines.append(f"<b>Submitted today ({len(submitted)})</b>")
        for a in submitted:
            lines.append(f"  - <a href=\"{a.get('url','#')}\">{a.get('company','?')}</a> - {a.get('title','?')}")
        lines.append("")
    else:
        lines.append("No applications submitted today.")
        lines.append("")

    # Ready
    if materials_ready:
        lines.append(f"<b>Materials ready, needs submit ({len(materials_ready)})</b>")
        for a in materials_ready[:5]:
            lines.append(f"  - {a.get('company','?')} - {a.get('title','?')}")
        if len(materials_ready) > 5:
            lines.append(f"  ...and {len(materials_ready) - 5} more")
        lines.append("")

    # Discoveries
    if discoveries:
        lines.append(f"<b>New jobs found ({len(discoveries)})</b>")
        for o in discoveries[:5]:
            lines.append(f"  - <a href=\"{o.get('url','#')}\">{o.get('company','?')}</a> - {o.get('title','?')}")
        if len(discoveries) > 5:
            lines.append(f"  ...and {len(discoveries) - 5} more")
        lines.append("")

    # Outreach reminder
    if outreach:
        lines.append(f"<b>Outreach queue: {len(outreach)} messages ready to send</b>")
        lines.append("Send 5-8 per day on LinkedIn. Check LINKEDIN_OUTREACH.md.")

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
