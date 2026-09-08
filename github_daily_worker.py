#!/usr/bin/env python3
"""
GitHub Actions Daily Worker
Runs the scanner, pipes in-scope design roles through the role-targeted pipeline.
"""

import antigravity_pipeline
import job_search_scanner
from datetime import datetime
from role_targeting import should_apply


def build_email_report(discovered_jobs, processed_jobs, skipped_jobs):
    html = f"""
    <html>
    <head><style>body {{ font-family: -apple-system, system-ui; }}</style></head>
    <body>
        <h2>Job search daily sweep</h2>
        <p>Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Applications are role-targeted (employment-led, no founder framing). See ROLE_TARGETING.md.</p>
        <hr>
        <h3>Discovered ({len(discovered_jobs)})</h3>
        <ul>
    """
    for job in discovered_jobs:
        html += (
            f"<li><a href='{job.get('url', '#')}'>"
            f"{job.get('company', 'Unknown')} - {job.get('title', 'Role')}</a></li>"
        )

    html += f"</ul><hr><h3>Customized ({len(processed_jobs)})</h3>"
    for pj in processed_jobs:
        html += (
            f"<div><b>{pj['company']}</b> — {pj.get('title', '')}<br>"
            f"Resume: {pj['resume']}<br>Cover Letter: {pj['cl']}</div><br>"
        )

    html += f"<hr><h3>Skipped as out of scope ({len(skipped_jobs)})</h3><ul>"
    for job in skipped_jobs:
        html += f"<li>{job.get('company', 'Unknown')} — {job.get('title', '')}</li>"
    html += "</ul></body></html>"

    with open("email_report.html", "w") as f:
        f.write(html)


def main():
    print("[*] Running job scanner...")
    job_search_scanner.main()

    state = job_search_scanner.load_state()
    recent_opps = list(state.get("opportunities", {}).values())
    print(f"[*] Found {len(recent_opps)} opportunities in state.")

    processed_jobs = []
    skipped_jobs = []

    for opp in recent_opps[:8]:
        company = opp.get("company", "Unknown")
        title = opp.get("title", "")
        url = opp.get("url", "https://example.com")

        if not should_apply(title, opp.get("description", "")):
            print(f"[SKIP] {company} — {title}")
            skipped_jobs.append(opp)
            continue

        if len(processed_jobs) >= 3:
            break

        try:
            print(f"[*] Customizing for {company} — {title}...")
            result = antigravity_pipeline.run_pipeline(company, url, title)
            if not result:
                skipped_jobs.append(opp)
                continue
            resume_path, cl_path = result
            processed_jobs.append(
                {
                    "company": company,
                    "title": title,
                    "resume": resume_path,
                    "cl": cl_path,
                }
            )
        except Exception as e:
            print(f"[!] Failed to process {company}: {e}")

    build_email_report(recent_opps, processed_jobs, skipped_jobs)
    print("\n[+] Daily sweep worker completed.")


if __name__ == "__main__":
    main()
