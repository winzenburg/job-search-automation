#!/usr/bin/env python3
"""
Outreach Generator
Creates personalized outreach messages for each contact.

Uses:
- Company research briefs
- LinkedIn message templates
- Contact information

Output: data/outreach/pending/[contact_id].json
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Project paths
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
RESEARCH_DIR = DATA_DIR / "research"
OUTREACH_DIR = DATA_DIR / "outreach"
PENDING_DIR = OUTREACH_DIR / "pending"
TEMPLATES_DIR = PROJECT_DIR / "templates"

# Create directories
PENDING_DIR.mkdir(parents=True, exist_ok=True)

CONTACTS_FILE = DATA_DIR / "contacts.json"
LINKEDIN_TEMPLATE = TEMPLATES_DIR / "linkedin_cold.txt"


def load_contacts() -> List[Dict]:
    """Load contacts from JSON."""
    with open(CONTACTS_FILE) as f:
        return json.load(f)


def load_research(company_slug: str) -> Dict:
    """Load research brief for a company."""
    research_file = RESEARCH_DIR / f"{company_slug}.json"
    if research_file.exists():
        with open(research_file) as f:
            return json.load(f)
    return {}


def load_template(template_name: str = "linkedin_cold") -> str:
    """Load message template."""
    template_file = TEMPLATES_DIR / f"{template_name}.txt"
    with open(template_file) as f:
        return f.read()


def generate_personalization_hook(company: Dict, brief: Dict) -> str:
    """
    Generate a specific, timely hook for the message.
    Uses company research to find something recent/specific to mention.
    """
    hooks = brief.get('personalization_hooks', [])
    
    if hooks:
        # Use first hook from research
        return hooks[0]
    
    # Fallback to generic but still specific
    ai_keywords = company.get('ai_keywords', [])
    if ai_keywords:
        return f"integrating AI into your product ({', '.join(ai_keywords[:2])})"
    
    return "growing your design team and capabilities"


def generate_opportunity_angle(brief: Dict) -> str:
    """
    Create a specific value proposition for this company.
    Based on research, what can Ryan uniquely offer?
    """
    angles = brief.get('opportunity_angles', [])
    
    if angles:
        angle = angles[0]
        return angle if angle.endswith((".", "!", "?")) else angle + "."
    
    # Fallback
    return "I've built frameworks that help design teams adopt AI systematically—not just adding tools, but transforming how they work."


def _first_name(full_name: str) -> str:
    """Return just the first name, handling edge cases like 'CJ' or parenthetical nicknames."""
    name = full_name.strip()
    if name.startswith("[Research Needed]"):
        return "there"
    # Handle "Christina (CJ) Jones" -> "CJ"
    paren = __import__("re").search(r"\((\w+)\)", name)
    if paren:
        return paren.group(1)
    return name.split()[0]


# Rotating message templates -- varied tone, structure, and CTA so no two
# messages feel like they came from the same mail merge.
_TEMPLATES = [
    # 0 -- observation-led, conversational
    """\
Subject: Design ops question

Hi {first_name},

{company_name} is {personalization_hook} -- that's a real design challenge at scale.

I've spent 15 years building design operations for teams in healthcare, fintech, and telecom. The last couple years I've been focused on something most design leaders don't have bandwidth to tackle on their own: getting AI into how teams actually work, not just which tools they use.

{opportunity_angle}

Worth a quick call if you ever want to compare notes?

Ryan
winzenburg.com
""",
    # 1 -- direct, shorter
    """\
Subject: Quick question about design ops at {company_name}

Hi {first_name},

Saw that {company_name} is {personalization_hook}. Curious how you're thinking about design ops infrastructure as that scales.

Background: 15 years in design operations, and recently I've gone deep on AI integration -- the workflow side specifically, not just tooling.

{opportunity_angle}

Happy to chat for 15 minutes if it's relevant.

Ryan
winzenburg.com
""",
    # 2 -- lead with the angle
    """\
Subject: {company_name} + design ops

Hi {first_name},

{company_name} is {personalization_hook}.

{opportunity_angle}

I've spent 15 years in design ops across healthcare, fintech, and telecom and lately I've been working specifically on the AI integration side -- how design teams actually absorb it into their day-to-day rather than just piloting tools.

Open to a short conversation if this is on your radar.

Ryan
winzenburg.com
""",
    # 3 -- peer tone
    """\
Subject: AI in design operations

Hi {first_name},

Noticed {company_name} is {personalization_hook}. It's a problem I've been thinking about a lot.

15 years in design ops, mostly in regulated industries where you have to systematize everything. Lately I've shifted focus to AI -- specifically what it takes to get a design team using it in a way that actually sticks.

{opportunity_angle}

If this is something you're working through, I'd love to compare notes.

Ryan
winzenburg.com
""",
    # 4 -- lead with Ryan's background, then hook
    """\
Subject: Design operations question

Hi {first_name},

I spent 15 years building design ops for large teams in healthcare, fintech, and telecom. The last few years I've been focused on one specific problem: how design organizations actually integrate AI into how they work, not just the tooling decisions.

{company_name} is {personalization_hook}, which is exactly the kind of context where this matters most.

{opportunity_angle}

Worth a quick call?

Ryan
winzenburg.com
""",
    # 5 -- curiosity-led
    """\
Subject: Something I noticed about {company_name}

Hi {first_name},

{company_name} is {personalization_hook} -- I've been following it.

I've spent 15 years building design operations systems, and lately I've been working specifically on the AI integration side: what changes in how a design team operates when AI is actually embedded in the workflow.

{opportunity_angle}

Would love to hear how you're thinking about it if you have 15 minutes.

Ryan
winzenburg.com
""",
]

# Subject line variants for when a template doesn't specify its own
_SUBJECTS = [
    "Design ops question",
    "Quick question about {company_name}",
    "AI in design operations",
    "Design operations at {company_name}",
    "{company_name} + design ops",
    "Something I've been thinking about",
]


def generate_message(contact: Dict, company: Dict, brief: Dict, index: int = 0) -> Dict:
    """
    Generate a personalized outreach message for one contact.
    `index` rotates which template variant is used so messages don't all
    look identical.
    """
    name = contact.get("name", "there")
    first = _first_name(name)

    hook = generate_personalization_hook(company, brief)
    angle = generate_opportunity_angle(brief)
    slug = company.get("slug", company.get("name", "").lower().replace(" ", "-"))

    # Pick template by index, cycling through all variants
    template = _TEMPLATES[index % len(_TEMPLATES)]

    message = template.format(
        first_name=first,
        company_name=company["name"],
        personalization_hook=hook,
        opportunity_angle=angle,
        company_slug=slug,
    )

    outreach = {
        "id": str(uuid.uuid4()),
        "contact_id": contact["id"],
        "company_id": company["id"],
        "contact_name": name,
        "contact_title": contact["title"],
        "company_name": company["name"],
        "channel": "linkedin",
        "message": message,
        "template_used": f"linkedin_cold_v{index % len(_TEMPLATES)}",
        "personalization": {
            "hook": hook,
            "angle": angle,
        },
        "status": "pending_approval",
        "generated_at": datetime.now().isoformat(),
        "utm_params": {
            "utm_source": "linkedin",
            "utm_campaign": "outreach",
            "utm_medium": slug,
        },
    }

    return outreach


def save_outreach(outreach: Dict):
    """Save outreach message to pending queue."""
    filename = f"{outreach['id']}.json"
    filepath = PENDING_DIR / filename
    
    with open(filepath, 'w') as f:
        json.dump(outreach, f, indent=2)
    
    return filepath


def main():
    """Generate outreach for all contacts needing messages."""
    print("=" * 60)
    print("OUTREACH GENERATOR")
    print("=" * 60)
    
    # Load contacts
    contacts = load_contacts()
    print(f"\n📊 Total contacts: {len(contacts)}")
    
    # Filter contacts needing outreach
    needs_outreach = [
        c for c in contacts
        if c.get('status') in ['needs_research', 'researched', None]
    ]
    
    if not needs_outreach:
        print("✅ All contacts already have outreach generated!")
        return
    
    print(f"✉️  Contacts needing outreach: {len(needs_outreach)}")
    
    # Generate outreach for each contact
    generated = 0
    
    for i, contact in enumerate(needs_outreach):
        try:
            # Find company
            company_name = contact.get('company_name', '')
            company_slug = company_name.lower().replace(' ', '-') if company_name else None
            
            if not company_slug:
                print(f"⏭️  Skipping {contact.get('name', 'unknown')}: no company info")
                continue
            
            # Load research
            research = load_research(company_slug)
            if not research:
                print(f"⏭️  Skipping {contact.get('name', 'unknown')}: no research found")
                continue
            
            company = research.get('company', {})
            brief = research.get('brief', {})
            
            # Generate message, rotating through template variants
            outreach = generate_message(contact, company, brief, index=i)
            
            # Save to pending queue
            filepath = save_outreach(outreach)
            
            print(f"✅ Generated: {contact['company_name']} - {contact['title']} (v{i % 6})")
            print(f"   Saved to: {filepath.name}")
            
            generated += 1
            
        except Exception as e:
            print(f"❌ Error generating for {contact.get('name', 'unknown')}: {e}")
    
    print("\n" + "=" * 60)
    print(f"✅ Outreach generation complete!")
    print(f"   Messages generated: {generated}")
    print(f"   Pending approval: {len(list(PENDING_DIR.glob('*.json')))}")
    print("=" * 60)
    print(f"\n📋 Next: Review messages with: python3 scripts/approval_queue.py")


if __name__ == "__main__":
    main()
