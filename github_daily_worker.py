#!/usr/bin/env python3
"""
GitHub Actions Daily Worker
Runs the scanner, pipes results through Antigravity pipeline, and prepares email payload.
"""

import os
import json
from pathlib import Path
from datetime import datetime
import job_search_scanner
import antigravity_pipeline

def build_email_report(discovered_jobs, processed_jobs):
    html = f"""
    <html>
    <head><style>body {{ font-family: -apple-system, system-ui; }}</style></head>
    <body>
        <h2>Antigravity Daily Sweep Report</h2>
        <p>Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <h3>Discovered ({len(discovered_jobs)})</h3>
    """
    for job in discovered_jobs:
        html += f"<li><a href='{job.get('url', '#')}'>{job.get('company', 'Unknown')} - {job.get('title', 'Role')}</a></li>"
    
    html += "<hr><h3>Successfully Customized Profiles</h3>"
    for pj in processed_jobs:
        html += f"<div><b>{pj['company']}</b>: <br>Resume: {pj['resume']} <br>Cover Letter: {pj['cl']}</div><br>"
        
    html += "</body></html>"
    
    with open("email_report.html", "w") as f:
        f.write(html)

def main():
    print("[*] Running job scanner...")
    
    # Refresh STATE_FILE with dummy state if first run
    job_search_scanner.main()
    
    # Load state to see new opportunities
    state = job_search_scanner.load_state()
    # Find opportunities added today (for simplicity we just take all opportunities in a real CI this would filter by date)
    recent_opps = list(state.get("opportunities", {}).values())
    
    print(f"[*] Found {len(recent_opps)} opportunities.")
    
    processed_jobs = []
    
    # Process up to 3 to save API costs
    for opp in recent_opps[:3]:
        company = opp.get("company", "Unknown")
        url = opp.get("url", "https://example.com")
        
        try:
            print(f"[*] Customizing for {company}...")
            # antigravity_pipeline expects company and job_url, and will write to disk
            resume_path, cl_path = antigravity_pipeline.run_pipeline(company, url)
            processed_jobs.append({
                "company": company,
                "resume": resume_path,
                "cl": cl_path
            })
        except Exception as e:
            print(f"[!] Failed to process {company}: {e}")
            
    build_email_report(recent_opps, processed_jobs)
    print("\n[+] Daily sweep worker completed successfully.")

if __name__ == "__main__":
    main()
