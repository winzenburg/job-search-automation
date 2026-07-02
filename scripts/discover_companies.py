#!/usr/bin/env python3
"""
Company Discovery Engine
Finds target companies matching job search criteria.

Sources:
- Built In (startup database)
- LinkedIn (company search)
- Manual curated list
- Y Combinator batch lists

Output: data/companies.json
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

# Project paths
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"

# Target criteria
CRITERIA = {
    "min_designers": 15,
    "locations": ["Remote", "Colorado", "Denver", "Boulder", "USA"],
    "ai_keywords": [
        "AI", "artificial intelligence", "machine learning", "LLM",
        "generative AI", "AI-powered", "AI-native"
    ],
    "industries": [
        "SaaS", "Enterprise Software", "Developer Tools",
        "Design Tools", "Productivity", "Collaboration"
    ]
}


def load_companies() -> List[Dict]:
    """Load existing companies from JSON."""
    if COMPANIES_FILE.exists():
        with open(COMPANIES_FILE) as f:
            return json.load(f)
    return []


def save_companies(companies: List[Dict]):
    """Save companies to JSON."""
    with open(COMPANIES_FILE, 'w') as f:
        json.dump(companies, f, indent=2)
    print(f"✅ Saved {len(companies)} companies to {COMPANIES_FILE}")


def add_company(companies: List[Dict], company: Dict) -> List[Dict]:
    """Add company if not duplicate."""
    # Check for duplicates by name or URL
    existing_names = {c.get('name', '').lower() for c in companies}
    existing_urls = {c.get('url', '').lower() for c in companies}
    
    name_lower = company.get('name', '').lower()
    url_lower = company.get('url', '').lower()
    
    if name_lower in existing_names or url_lower in existing_urls:
        print(f"⏭️  Skipping duplicate: {company['name']}")
        return companies
    
    # Add UUID and timestamp
    company['id'] = str(uuid.uuid4())
    company['discovered_at'] = datetime.now().isoformat()
    company['status'] = 'discovered'
    
    companies.append(company)
    print(f"✅ Added: {company['name']}")
    return companies


def discover_built_in() -> List[Dict]:
    """
    Scrape Built In for companies.
    Note: This is a placeholder - actual scraping requires handling JS rendering.
    """
    print("\n🔍 Discovering companies from Built In...")
    
    # Placeholder - would need Playwright for JS-rendered pages
    # For now, return manual seed list
    return []


def discover_yc_companies() -> List[Dict]:
    """
    Find AI-focused companies from Y Combinator batches.
    """
    print("\n🔍 Discovering YC companies...")
    
    # YC company directory (public, no auth needed)
    # Placeholder - would scrape https://www.ycombinator.com/companies
    return []


def seed_manual_companies() -> List[Dict]:
    """
    Manual seed list of high-potential companies.
    These are known AI-forward, design-heavy companies.
    """
    print("\n🌱 Seeding manual company list...")
    
    seed_companies = [
        {
            "name": "Figma",
            "slug": "figma",
            "url": "https://figma.com",
            "linkedin": "https://linkedin.com/company/figma",
            "stage": "Public",
            "funding": "$332M+ (IPO pending)",
            "designer_count_estimate": 150,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["AI design tools", "auto-layout", "FigJam AI"],
            "why_target": "Leading design tool, heavy AI investment, large design team",
            "notes": "Check for Head of Design Ops or AI + Design roles"
        },
        {
            "name": "Notion",
            "slug": "notion",
            "url": "https://notion.so",
            "linkedin": "https://linkedin.com/company/notionhq",
            "stage": "Series C",
            "funding": "$343M",
            "designer_count_estimate": 50,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["Notion AI", "AI writing assistant", "generative AI"],
            "why_target": "AI-first product evolution, design-forward culture",
            "notes": "Recent AI features launch - good timing"
        },
        {
            "name": "Canva",
            "slug": "canva",
            "url": "https://canva.com",
            "linkedin": "https://linkedin.com/company/canva",
            "stage": "Series A (Unicorn)",
            "funding": "$572M",
            "designer_count_estimate": 200,
            "location": "Sydney, Australia (Remote)",
            "ai_keywords": ["Magic Write", "AI image generation", "AI design tools"],
            "why_target": "Massive design team, heavy AI integration, design ops need",
            "notes": "Large scale = need for ops infrastructure"
        },
        {
            "name": "Miro",
            "slug": "miro",
            "url": "https://miro.com",
            "linkedin": "https://linkedin.com/company/miro",
            "stage": "Series C",
            "funding": "$476M",
            "designer_count_estimate": 80,
            "location": "San Francisco, CA / Amsterdam (Remote)",
            "ai_keywords": ["Miro AI", "collaboration AI", "smart widgets"],
            "why_target": "Design collaboration tool, AI features, growing team",
            "notes": "Recently launched AI features - transformation phase"
        },
        {
            "name": "Webflow",
            "slug": "webflow",
            "url": "https://webflow.com",
            "linkedin": "https://linkedin.com/company/webflow-inc",
            "stage": "Series C",
            "funding": "$334M",
            "designer_count_estimate": 60,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["No-code", "visual development", "AI website generation"],
            "why_target": "Design-centric product, no-code + AI convergence",
            "notes": "Strong design culture, ops-mature"
        },
        {
            "name": "Framer",
            "slug": "framer",
            "url": "https://framer.com",
            "linkedin": "https://linkedin.com/company/framer",
            "stage": "Series B",
            "funding": "$50M",
            "designer_count_estimate": 40,
            "location": "Amsterdam (Remote)",
            "ai_keywords": ["AI prototyping", "design-to-code", "Framer AI"],
            "why_target": "Design tool for designers, AI-powered features",
            "notes": "Smaller but fast-growing, good timing"
        },
        {
            "name": "Linear",
            "slug": "linear",
            "url": "https://linear.app",
            "linkedin": "https://linkedin.com/company/linearapp",
            "stage": "Series B",
            "funding": "$52M",
            "designer_count_estimate": 25,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["Product management", "AI issue triage", "workflow automation"],
            "why_target": "Design-forward product tool, growing fast",
            "notes": "Exceptional design culture, could create role"
        },
        {
            "name": "Pitch",
            "slug": "pitch",
            "url": "https://pitch.com",
            "linkedin": "https://linkedin.com/company/pitch",
            "stage": "Series B",
            "funding": "$85M",
            "designer_count_estimate": 30,
            "location": "Berlin (Remote)",
            "ai_keywords": ["Presentation AI", "design suggestions", "AI templates"],
            "why_target": "Design-heavy product, AI features launching",
            "notes": "Strong design leadership, European remote-friendly"
        },
        {
            "name": "Airtable",
            "slug": "airtable",
            "url": "https://airtable.com",
            "linkedin": "https://linkedin.com/company/airtable",
            "stage": "Series F",
            "funding": "$1.36B",
            "designer_count_estimate": 70,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["AI-powered apps", "Airtable AI", "workflow automation"],
            "why_target": "Large design team, AI transformation underway",
            "notes": "Enterprise scale = design ops need"
        },
        {
            "name": "Superhuman",
            "slug": "superhuman",
            "url": "https://superhuman.com",
            "linkedin": "https://linkedin.com/company/superhuman",
            "stage": "Post-acquisition (rebranded from Grammarly)",
            "funding": "$108M (original)",
            "designer_count_estimate": 80,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["AI email", "AI writing", "productivity AI", "Coda integration"],
            "why_target": "Rebranded Grammarly — now 920-person AI productivity platform integrating three design orgs",
            "notes": "Collin Whitehead is VP of Design (Oct 2025). Jonas Downey leads Superhuman Mail design."
        },
        # --- Tier 2: AI-Native ---
        {
            "name": "OpenAI",
            "slug": "openai",
            "url": "https://openai.com",
            "linkedin": "https://linkedin.com/company/openai",
            "stage": "Private ($300B valuation)",
            "funding": "$195.9B total",
            "designer_count_estimate": 80,
            "location": "San Francisco, CA (Hybrid)",
            "ai_keywords": ["ChatGPT", "GPT-4o", "Sora", "AI agents", "OpenAI API"],
            "why_target": "Most influential AI company, rapidly building product design org",
            "notes": "Ian Silber is Head of Product Design. Actively opening design roles."
        },
        {
            "name": "Anthropic",
            "slug": "anthropic",
            "url": "https://anthropic.com",
            "linkedin": "https://linkedin.com/company/anthropic",
            "stage": "Private ($61B valuation)",
            "funding": "$12B+ total",
            "designer_count_estimate": 40,
            "location": "San Francisco, CA (Hybrid)",
            "ai_keywords": ["Claude", "Claude Code", "Claude Cowork", "Claude Design", "AI safety"],
            "why_target": "Top AI safety company, design is top-level product nav item",
            "notes": "Joel Lewenstein is Head of Design. Meaghan Choi leads Claude Code."
        },
        {
            "name": "Perplexity",
            "slug": "perplexity",
            "url": "https://perplexity.ai",
            "linkedin": "https://linkedin.com/company/perplexity-ai",
            "stage": "Private ($14B valuation)",
            "funding": "$1.7B total",
            "designer_count_estimate": 20,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["AI search", "answer engine", "Comet browser", "AI-native UX"],
            "why_target": "Fast-growing AI search, design-in-code team, VP of Design Henry Modisett",
            "notes": "Sebastian Speier just promoted to Head of Design (May 2026)."
        },
        {
            "name": "Runway",
            "slug": "runway",
            "url": "https://runwayml.com",
            "linkedin": "https://linkedin.com/company/runwayml",
            "stage": "Private ($4.5B valuation)",
            "funding": "$861.5M total",
            "designer_count_estimate": 20,
            "location": "New York, NY (Remote)",
            "ai_keywords": ["Gen-3 Alpha", "AI video generation", "AI creative tools", "world models"],
            "why_target": "Frontier AI creative company, artist-first culture",
            "notes": "Jamie Umpherson is CCO (Feb 2026). Alejandro Matamala co-founder + former CDO."
        },
        # --- Tier 3: Colorado Priority ---
        {
            "name": "Gusto",
            "slug": "gusto",
            "url": "https://gusto.com",
            "linkedin": "https://linkedin.com/company/gustohq",
            "stage": "Private ($9.5B valuation)",
            "funding": "$746M total",
            "designer_count_estimate": 60,
            "location": "Denver, CO + San Francisco (Remote-friendly)",
            "ai_keywords": ["Gusto AI", "HR automation", "payroll AI", "AI-native HR"],
            "why_target": "Colorado Tier-1 priority, CDO Amy Thibodeau, Denver office 226 people",
            "notes": "Amy Thibodeau is CDO. Alaine MacKenzie is VP of Product Design for AI & Core."
        },
        {
            "name": "Databricks",
            "slug": "databricks",
            "url": "https://databricks.com",
            "linkedin": "https://linkedin.com/company/databricks",
            "stage": "Private ($62B valuation)",
            "funding": "$27.3B total",
            "designer_count_estimate": 100,
            "location": "San Francisco, CA / Denver, CO (Remote)",
            "ai_keywords": ["Mosaic AI", "MLflow", "Delta Lake", "AI platform"],
            "why_target": "Colorado Tier-1, fastest-growing enterprise AI platform, $2.6B revenue",
            "notes": "Ryan Donahue is VP Product Design (since Jan 2020)."
        },
        # --- Tier 4: Fintech/SaaS ---
        {
            "name": "Stripe",
            "slug": "stripe",
            "url": "https://stripe.com",
            "linkedin": "https://linkedin.com/company/stripe",
            "stage": "Private ($91.5B valuation)",
            "funding": "$9.4B total",
            "designer_count_estimate": 200,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["Stripe AI", "payment intelligence", "AI fraud detection"],
            "why_target": "Legendary design culture, 200+ designers, Katie Dill Head of Design",
            "notes": "Yuliya Gorlovetsky is Head of Product Design. Actively hiring."
        },
        {
            "name": "Brex",
            "slug": "brex",
            "url": "https://brex.com",
            "linkedin": "https://linkedin.com/company/brexhq",
            "stage": "Private ($12.3B valuation)",
            "funding": "$2.0B total",
            "designer_count_estimate": 50,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["spend management AI", "expense automation", "AI finance"],
            "why_target": "CDO Matt Bango (ex-Palantir), actively hiring design leaders",
            "notes": "Matt Bango is CDO (since Sep 2024)."
        },
        {
            "name": "Ramp",
            "slug": "ramp",
            "url": "https://ramp.com",
            "linkedin": "https://linkedin.com/company/ramp",
            "stage": "Private ($13.6B valuation)",
            "funding": "$3.0B total",
            "designer_count_estimate": 30,
            "location": "New York, NY (Remote)",
            "ai_keywords": ["spend automation", "AI finance", "Claude Code", "AI-native"],
            "why_target": "Most AI-installed company, VP Design redesigning org structure for AI era",
            "notes": "Diego Zaks is VP Design (Apr 2023). Highest AI-ops alignment company."
        },
        # --- Tier 5: Consumer/Prosumer ---
        {
            "name": "Duolingo",
            "slug": "duolingo",
            "url": "https://duolingo.com",
            "linkedin": "https://linkedin.com/company/duolingo",
            "stage": "Public (DUOL)",
            "funding": "$183M pre-IPO",
            "designer_count_estimate": 130,
            "location": "Pittsburgh, PA / New York, NY (Remote)",
            "ai_keywords": ["Duolingo Max", "AI language learning", "Lily AI tutor"],
            "why_target": "Design is 2nd largest division, first CDO hired, scaling to 130 designers",
            "notes": "Ryan Sims is first CDO (April 2024). Mig Reyes is VP Product Experience."
        },
        {
            "name": "Loom (Atlassian)",
            "slug": "loom",
            "url": "https://loom.com",
            "linkedin": "https://linkedin.com/company/loom",
            "stage": "Acquired by Atlassian (2023, $975M)",
            "funding": "$203M pre-acquisition",
            "designer_count_estimate": 40,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["Loom AI", "async video AI", "Atlassian Rovo", "AI video summaries"],
            "why_target": "Atlassian AI portfolio, strong async + AI design culture",
            "notes": "Stu Smith is Head of Design for Loom Core (Sep 2025). Christina Nguyen White is VP Design."
        },
        {
            "name": "Asana",
            "slug": "asana",
            "url": "https://asana.com",
            "linkedin": "https://linkedin.com/company/asana",
            "stage": "Public (ASAN)",
            "funding": "$12.4B market cap",
            "designer_count_estimate": 80,
            "location": "San Francisco, CA (Remote)",
            "ai_keywords": ["Asana AI", "Studio AI agents", "AI workflows", "enterprise AI"],
            "why_target": "Enterprise work management, VP Design since Jun 2023, building AI Studio",
            "notes": "Manesh John is VP of Design (Jun 2023). Hiring design directors."
        },
    ]

    return seed_companies


def main():
    """Run discovery process."""
    print("=" * 60)
    print("COMPANY DISCOVERY ENGINE")
    print("=" * 60)
    
    # Load existing companies
    companies = load_companies()
    print(f"\n📊 Currently tracking: {len(companies)} companies")
    
    # Discover from sources
    discovered = []
    
    # Manual seed (immediate)
    manual = seed_manual_companies()
    discovered.extend(manual)
    
    # Built In (requires scraping)
    # built_in = discover_built_in()
    # discovered.extend(built_in)
    
    # YC companies (requires scraping)
    # yc = discover_yc_companies()
    # discovered.extend(yc)
    
    # Add new companies
    for company in discovered:
        companies = add_company(companies, company)
    
    # Save updated list
    save_companies(companies)
    
    print("\n" + "=" * 60)
    print(f"✅ Discovery complete: {len(companies)} total companies")
    print("=" * 60)


if __name__ == "__main__":
    main()
