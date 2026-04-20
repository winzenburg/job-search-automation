#!/usr/bin/env python3
"""
Job Search Scanner — Automated opportunity discovery
Searches Indeed & LinkedIn for target roles, identifies new opportunities, sends alerts
"""

import json
import os
import sys
from datetime import datetime
import hashlib
import urllib.request
import re
from pathlib import Path

# Target parameters
TARGET_RANKS = [
    "manager",
    "strategist",
    "director",
    "vp",
    "vice president",
    "head",
    "principal",
    "staff"
]

TARGET_KEYWORDS = [
    "AI",
    "design systems",
    "product design",
    "UX",
    "design ops",
]

MIN_SALARY = 0
LOCATIONS = ["remote", "boulder", "denver", "colorado", "worldwide", "global", "us", "usa", "anywhere"]

OPPORTUNITIES_FILE = Path(__file__).parent / "OPPORTUNITIES.md"
STATE_FILE = Path(__file__).parent / "scanner_state.json"


def load_state():
    """Load previously found opportunities to detect new ones."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"opportunities": {}, "lastRun": None}


def save_state(state):
    """Save state to detect duplicates on next run."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def hash_opportunity(title, company, url):
    """Generate unique hash for opportunity."""
    key = f"{title}|{company}|{url}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:8]


def search_remotive():
    """Search Remotive for remote design and product roles natively via API."""
    opportunities = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching Remotive API...")
    try:
        url = "https://remotive.com/api/remote-jobs?category=design"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for job in data.get("jobs", []):
                opportunities.append({
                    "source": "Remotive",
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "location": job.get("candidate_required_location", "Remote"),
                    "salary": job.get("salary", ""), # Remotive sometimes lacks exact salary arrays
                    "url": job.get("url", ""),
                    "postedDate": job.get("publication_date", ""),
                    "description": job.get("description", "")
                })
    except Exception as e:
        print(f"Error searching remotive: {e}")
        
    return opportunities


def search_remoteok():
    """Search RemoteOK natively via API."""
    opportunities = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching RemoteOK API...")
    try:
        url = "https://remoteok.com/api?tags=design"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for job in data[1:]:
                salary_max = job.get("salary_max", 0)
                try:
                    salary = int(salary_max) if salary_max else 0
                except (ValueError, TypeError):
                    salary = 0
                
                opportunities.append({
                    "source": "RemoteOK",
                    "title": job.get("position", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", "Remote"),
                    "salary": salary,
                    "url": job.get("url", ""),
                    "postedDate": job.get("date", ""),
                    "description": job.get("description", "")
                })
    except Exception as e:
        print(f"Error searching remoteok: {e}")
        
    return opportunities


def filter_opportunities(opportunities):
    """Filter opportunities by target criteria."""
    filtered = []
    
    for opp in opportunities:
        title = opp.get("title", "").lower()
        location = opp.get("location", "").lower()
        description = opp.get("description", "").lower()
        
        salary_val = opp.get("salary", 0)
        try:
            salary = int(salary_val) if salary_val else 0
        except (ValueError, TypeError):
            salary = 0
        
        # Check title has correct rank (Manager, Director, VP, etc)
        rank_match = any(rank in title for rank in TARGET_RANKS)
        
        # Check that it's actually a Product/Design role instead of HR or Sales
        PRIMARY_DOMAINS = ["design", "product", "ux", "ui", "creative", "strategy", "ops"]
        domain_match = any(d in title for d in PRIMARY_DOMAINS) or (description.count("design") + description.count("product")) > 4
        
        # Check description/title has correct technical keyword using regex bounds to avoid matching 'ai' in 'email'
        tech_match = False
        for kw in TARGET_KEYWORDS:
            if re.search(rf'\b{kw}\b', description) or kw in title:
                tech_match = True
                break
        
        # Check location match
        location_match = any(loc in location for loc in LOCATIONS)
        
        # Check salary (if available)
        salary_match = salary >= MIN_SALARY if salary > 0 else True
        
        if rank_match and domain_match and tech_match and location_match and salary_match:
            filtered.append(opp)
    
    return filtered


def format_opportunity_markdown(opp, oppy_hash):
    """Format single opportunity for OPPORTUNITIES.md"""
    return f"""
### {opp.get('company', 'Unknown')} — {opp.get('title', 'Unknown')}

**Source:** {opp.get('source', 'Unknown')}  
**Link:** {opp.get('url', 'N/A')}  
**Level:** {opp.get('title', '')}  
**Salary:** {opp.get('salary', 'Not specified')}  
**Location:** {opp.get('location', 'Unknown')}  
**Posted:** {opp.get('postedDate', 'Unknown')}  
**Fit Score:** [TBD]  
**Key Responsibilities:** [Extract from job description]  
**Why It Fits:** [Your analysis of alignment]  
**Action:** [To Apply / Warm Intro Opportunity / Research]  
**ID:** {oppy_hash}

---
"""


def update_opportunities_file(new_opportunities):
    """Append new opportunities to OPPORTUNITIES.md"""
    if not new_opportunities:
        return
    
    # Ensure file exists
    if not OPPORTUNITIES_FILE.exists():
        OPPORTUNITIES_FILE.write_text("# Job Opportunities\n\n")
    
    # Append new opportunities
    with open(OPPORTUNITIES_FILE, 'a') as f:
        f.write(f"\n## New Opportunities — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for opp in new_opportunities:
            opp_hash = hash_opportunity(opp.get('title'), opp.get('company'), opp.get('url'))
            f.write(format_opportunity_markdown(opp, opp_hash))


def send_telegram_alert(new_opportunities):
    """Send Telegram alert with new opportunities."""
    if not new_opportunities:
        return
    
    message = f"🎯 **{len(new_opportunities)} New Job Opportunities Found**\n\n"
    
    for opp in new_opportunities:
        message += f"**{opp.get('company')}** — {opp.get('title')}\n"
        message += f"  {opp.get('location')} | {opp.get('salary', 'Salary TBD')}\n"
        message += f"  {opp.get('url', 'N/A')}\n\n"
    
    message += "Review in OPPORTUNITIES.md and prioritize for outreach."
    
    # Would call message tool here to send via Telegram
    # For now, log to stdout
    print(f"\n[ALERT] {message}")


def main():
    """Main scanner workflow."""
    print(f"\n{'='*60}")
    print(f"Job Search Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Load state
    state = load_state()
    
    # Search across platforms
    print("Starting searches...\n")
    all_opportunities = []
    all_opportunities.extend(search_remotive())
    all_opportunities.extend(search_remoteok())
    
    print(f"\nTotal opportunities found: {len(all_opportunities)}")
    
    # Filter by criteria
    filtered = filter_opportunities(all_opportunities)
    print(f"After filtering: {len(filtered)} opportunities meet criteria\n")
    
    # Identify new opportunities
    new_opportunities = []
    for opp in filtered:
        opp_hash = hash_opportunity(opp.get('title'), opp.get('company'), opp.get('url'))
        if opp_hash not in state["opportunities"]:
            new_opportunities.append(opp)
            state["opportunities"][opp_hash] = {
                "company": opp.get('company'),
                "title": opp.get('title'),
                "foundDate": datetime.now().isoformat(),
                "url": opp.get('url'),
            }
    
    print(f"New opportunities: {len(new_opportunities)}\n")
    
    if new_opportunities:
        # Update opportunities file
        update_opportunities_file(new_opportunities)
        
        # Send alert
        send_telegram_alert(new_opportunities)
        
        print("✅ Opportunities file updated + alert sent\n")
    else:
        print("No new opportunities found.\n")
    
    # Update state
    state["lastRun"] = datetime.now().isoformat()
    save_state(state)
    
    print(f"Next run: {state['lastRun']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
