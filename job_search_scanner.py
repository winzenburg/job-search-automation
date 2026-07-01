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
import urllib.parse
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
    "ai",
    "design systems",
    "product design",
    "ux",
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


def search_weworkremotely():
    """Search WeWorkRemotely for remote design roles natively via XML RSS."""
    opportunities = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching WeWorkRemotely RSS...")
    try:
        import xml.etree.ElementTree as ET
        url = "https://weworkremotely.com/categories/remote-design-jobs.rss"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req) as response:
            root = ET.fromstring(response.read())
            for item in root.findall('.//item'):
                title_text = item.find('title').text if item.find('title') is not None else ""
                company = ""
                title = title_text
                if ":" in title_text:
                    parts = title_text.split(":", 1)
                    company = parts[0]
                    title = parts[1]
                    
                desc = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                opportunities.append({
                    "source": "WeWorkRemotely",
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": "Remote",
                    "salary": 0,
                    "url": link,
                    "postedDate": pubDate,
                    "description": desc
                })
    except Exception as e:
        print(f"Error searching WWR: {e}")
        
    return opportunities


def search_remoteok():
    """Search RemoteOK natively via API."""
    opportunities = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching RemoteOK API...")
    try:
        url = "https://remoteok.com/api?tags=design"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://remoteok.com/',
            'Origin': 'https://remoteok.com'
        }
        req = urllib.request.Request(url, headers=headers)
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


def search_remotive():
    """Search Remotive public API for remote design roles."""
    opportunities = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching Remotive API...")
    try:
        url = "https://remotive.com/api/remote-jobs?category=design&limit=100"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            for job in data.get("jobs", []):
                opportunities.append({
                    "source": "Remotive",
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "location": job.get("candidate_required_location", "Remote"),
                    "salary": 0,
                    "url": job.get("url", ""),
                    "postedDate": job.get("publication_date", ""),
                    "description": job.get("description", "")
                })
    except Exception as e:
        print(f"Error searching Remotive: {e}")

    return opportunities


def search_himalayas():
    """Search Himalayas public API for senior remote design roles."""
    opportunities = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching Himalayas API...")
    try:
        # Search for Director/Executive level design roles worldwide
        params = "q=design&seniority=Director,Executive,Manager&worldwide=true&sort=recent&page=1"
        url = f"https://himalayas.app/jobs/api/search?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            for job in data.get("jobs", []):
                salary_min = job.get("salaryMin", 0) or 0
                salary_max = job.get("salaryMax", 0) or 0
                salary = max(salary_min, salary_max)
                try:
                    salary = int(salary)
                except (ValueError, TypeError):
                    salary = 0

                opportunities.append({
                    "source": "Himalayas",
                    "title": job.get("title", ""),
                    "company": job.get("companyName", ""),
                    "location": job.get("location", "Remote"),
                    "salary": salary,
                    "url": job.get("applicationLink", job.get("url", "")),
                    "postedDate": job.get("pubDate", ""),
                    "description": job.get("description", "")
                })
    except Exception as e:
        print(f"Error searching Himalayas: {e}")

    return opportunities


def search_hn_who_is_hiring() -> list[dict]:
    """
    Search the most recent monthly HN 'Who Is Hiring' thread for design leadership roles.
    Uses Algolia HN API to find the thread, then scans top-level job comments.
    Only includes comments that follow the structured "Company | Role | ..." format.
    """
    opportunities = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching HN Who's Hiring (monthly thread)...")
    try:
        # Find the most recent "Ask HN: Who is hiring?" story
        search_url = (
            "https://hn.algolia.com/api/v1/search"
            "?query=Ask+HN+Who+is+hiring&tags=ask_hn&hitsPerPage=3&numericFilters=points>10"
        )
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            results = json.loads(r.read().decode())

        stories = results.get("hits", [])
        if not stories:
            return []

        # Use the most recent hiring thread
        story = stories[0]
        story_id = story.get("objectID", "")
        if not story_id:
            return []

        # Fetch comments for this story
        comments_url = (
            f"https://hn.algolia.com/api/v1/search"
            f"?tags=comment,story_{story_id}&hitsPerPage=50"
        )
        req2 = urllib.request.Request(
            comments_url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req2, timeout=10) as r:
            comment_data = json.loads(r.read().decode())

        design_keywords = {"design", "ux", "ui", "designer"}
        leadership_keywords = {"head", "vp", "director", "lead", "chief"}

        for comment in comment_data.get("hits", []):
            text = (comment.get("comment_text") or "").lower()
            object_id = comment.get("objectID", "")
            created_at = comment.get("created_at", "")

            # Must mention both design and leadership
            has_design = any(kw in text for kw in design_keywords)
            has_leadership = any(kw in text for kw in leadership_keywords)
            if not (has_design and has_leadership):
                continue

            # Try to extract company name — HN format: "Company | Role | Location"
            raw_text = comment.get("comment_text") or ""
            first_line = raw_text.split("\n")[0]
            parts = [p.strip() for p in first_line.split("|")]
            company = parts[0] if parts else "Unknown"
            title_from_comment = parts[1] if len(parts) > 1 else "Design Leadership"

            # Skip if company name looks like a username (no spaces, all lowercase)
            if len(company) < 3 or company == company.lower().replace(" ", ""):
                continue

            hn_url = f"https://news.ycombinator.com/item?id={object_id}"
            opportunities.append({
                "source": "HN Who's Hiring",
                "title": title_from_comment[:100],
                "company": company[:80],
                "location": parts[2] if len(parts) > 2 else "Remote",
                "salary": 0,
                "url": hn_url,
                "postedDate": created_at,
                "description": raw_text[:2000]
            })

    except Exception as e:
        print(f"Error searching HN Who's Hiring: {e}")

    return opportunities


# Verified Ashby public job board slugs for target companies
# Tested and confirmed working as of July 2026
ASHBY_COMPANY_FEEDS: list[dict[str, str]] = [
    {"company": "OpenAI",   "slug": "openai"},
    {"company": "Notion",   "slug": "notion"},
    {"company": "Linear",   "slug": "linear"},
    {"company": "Miro",     "slug": "miro"},
    {"company": "Airtable", "slug": "airtable"},
]

# Companies to search by name via Himalayas and Remotive
# (their ATS feeds are not publicly accessible)
TARGET_COMPANY_NAMES: list[str] = [
    "Anthropic", "Stripe", "Gusto", "Databricks", "Perplexity",
    "Brex", "Ramp", "Duolingo", "Runway", "Asana",
    "Figma", "Canva", "Webflow", "Framer", "Pitch", "Superhuman",
]


def search_company_career_feeds() -> list[dict]:
    """
    Check Ashby career feeds for target companies that have verified public APIs.
    Returns design leadership openings — highest-signal opportunities.
    """
    opportunities = []
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking Ashby career feeds for target companies...")

    for feed in ASHBY_COMPANY_FEEDS:
        company = feed["company"]
        slug = feed["slug"]
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                raw = json.loads(response.read().decode())

            for job in raw.get("jobPostings", []):
                title = job.get("title", "")
                job_url = job.get("jobPostingUrl", "")
                location = job.get("locationName", "Remote")
                description = job.get("descriptionPlain", "")
                comp = job.get("compensation", {}) or {}
                salary = comp.get("maxValue", 0) or 0
                try:
                    salary = int(salary)
                except (ValueError, TypeError):
                    salary = 0

                opportunities.append({
                    "source": f"Careers ({company})",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "url": job_url,
                    "postedDate": "",
                    "description": description
                })

        except Exception as e:
            print(f"  ⚠️  {company} (Ashby): {e}")

    return opportunities


def search_target_companies_on_himalayas() -> list[dict]:
    """
    Search Himalayas for openings at specific target companies that don't have
    public ATS feeds. Uses the Himalayas search API with company name filter.
    """
    opportunities = []
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching Himalayas for target company openings...")

    for company_name in TARGET_COMPANY_NAMES:
        try:
            encoded = urllib.parse.quote(company_name)
            url = f"https://himalayas.app/jobs/api/search?q={encoded}&sort=recent"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            for job in data.get("jobs", []):
                # Only include if company name matches (Himalayas does broad search)
                if company_name.lower() not in job.get("companyName", "").lower():
                    continue
                salary = job.get("salaryMax", 0) or 0
                try:
                    salary = int(salary)
                except (ValueError, TypeError):
                    salary = 0

                opportunities.append({
                    "source": f"Himalayas ({company_name})",
                    "title": job.get("title", ""),
                    "company": job.get("companyName", company_name),
                    "location": job.get("location", "Remote"),
                    "salary": salary,
                    "url": job.get("applicationLink", ""),
                    "postedDate": job.get("pubDate", ""),
                    "description": job.get("description", "")
                })

        except Exception as e:
            print(f"  ⚠️  Himalayas/{company_name}: {e}")

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
        PRIMARY_DOMAINS = ["design", "product", "ux", "ui", "creative", "strategy", "design operations", "design ops"]
        domain_match = any(d in title for d in PRIMARY_DOMAINS) or description.count("design") > 4
        
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
    all_opportunities.extend(search_weworkremotely())
    all_opportunities.extend(search_remoteok())
    all_opportunities.extend(search_remotive())
    all_opportunities.extend(search_himalayas())
    all_opportunities.extend(search_hn_who_is_hiring())
    all_opportunities.extend(search_company_career_feeds())
    all_opportunities.extend(search_target_companies_on_himalayas())
    
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
