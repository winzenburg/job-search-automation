#!/usr/bin/env python3
"""
Career Targeting Strategy v3 — application gates and resume versioning.

Core mandate: Director-level product experience leadership for complex B2B —
the customer-facing product, the design org, and the operating model that
ships work. AI-enabled delivery is the multiplier, not the title.

Level architecture (search time):
  60% Director (Product Design / Product Experience / UX / Experience Strategy / Product Ops)
  30% Senior Director / Head of Product Experience|Design|Experience Strategy
  10% VP Product Experience / VP Design (selective)

IC and pure UX/UI roles are out of scope by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Level bands + resume versions
# ---------------------------------------------------------------------------

LEVEL_DIRECTOR = "director"  # 60%
LEVEL_HEAD = "head_senior_director"  # 30%
LEVEL_VP = "vp_selective"  # 10%

RESUME_PRODUCT_EXPERIENCE = "product_experience_leader"
RESUME_PRODUCT_OPS = "product_experience_ops"
RESUME_AI_ENTERPRISE = "ai_enterprise_workflow"

LEVEL_BANDS = (LEVEL_DIRECTOR, LEVEL_HEAD, LEVEL_VP)
RESUME_VERSIONS = (
    RESUME_PRODUCT_EXPERIENCE,
    RESUME_PRODUCT_OPS,
    RESUME_AI_ENTERPRISE,
)

MIN_BASE_SALARY = 225_000
STAGE1_APPLY_THRESHOLD = 7


@dataclass(frozen=True)
class RoleTarget:
    level: str
    resume_version: str
    headline: str
    altitude: str
    search_share: str
    instructions: str


# ---------------------------------------------------------------------------
# Title matching
# ---------------------------------------------------------------------------

_EXCLUDE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bpeople\b",
        r"\btalent\b",
        r"\brecruiter\b",
        r"\bhuman resources\b",
        r"\bcompensation\b",
        r"\bmerchandising\b",
        r"\bmechanical\b",
        r"\bdata engineer\b",
        r"\bsoftware engineer\b",
        r"\bstaff data\b",
        r"\bfront-?end engineer\b",
        r"\bback-?end\b",
        r"\bfull.?stack engineer\b",
        r"\bengineering manager\b",
        r"\b\btax\b",
        r"\bmotion designer\b",
        r"\bgraphic design\b",
        r"\bhead of graphic\b",
        r"\bcgi\b",
        r"\bcustomer success\b",
        r"\baccount executive\b",
        r"\brisk strategist\b",
        r"\bprogram manager\b",
        r"\bproject manager\b",
        r"\bbrand designer\b",
        r"\bbrand & creative\b",
        r"\bbrand and creative\b",
        r"\bart director\b",
        r"\bhead of marketing\b",
        r"\bcourse director\b",
        r"\binstructor\b",
        r"\bproduct manager\b",
        r"\bstaff product manager\b",
        r"\bsales\b",
        r"\bcpo\b",
        r"\bchief product officer\b",
        r"\bchief design officer\b",
        # Pure IC / production design — not the default search
        r"\bstaff product designer\b",
        r"\bsenior product designer\b",
        r"\bsenior staff product designer\b",
        r"\bstaff designer\b",
        r"\bux/?ui designer\b",
        r"\bui/?ux designer\b",
        r"\bproduct designer\b",
        r"\bux designer\b",
        r"\bui designer\b",
        r"\bvisual designer\b",
        r"\bbrand design\b",
        r"\bstaff brand\b",
        r"\bdesign engineer\b",
        r"\bweb experience manager\b",
        r"\bdigital web experience\b",
        r"\bai production\b",
        r"\(visual\)",
        r"\binnovation lab\b",
        r"\binnovation specialist\b",
    )
)

# Director band (60%)
_DIRECTOR_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bdirector of product design\b",
        r"\bdirector[,/ ]+product design\b",
        r"\bdirector of product experience\b",
        r"\bdirector[,/ ]+product experience\b",
        r"\bdirector of ux\b",
        r"\bdirector[,/ ]+ux\b",
        r"\bdirector of user experience\b",
        r"\bdirector of experience strategy\b",
        r"\bdirector[,/ ]+experience strategy\b",
        r"\bdirector of product operations\b",
        r"\bdirector[,/ ]+product operations\b",
        r"\bdirector of design\b",
        r"\bdirector[,/ ]+design\b",
        r"\bdesign director\b",
        r"\bux director\b",
        r"\bproduct design director\b",
        r"\bexperience director\b",
    )
)

# Head / Senior Director band (30%)
_HEAD_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bsenior director.{0,40}(product design|product experience|ux|experience|design)\b",
        r"\bhead of product experience\b",
        r"\bhead of product design\b",
        r"\bhead of experience strategy\b",
        r"\bhead of ux\b",
        r"\bhead of user experience\b",
        r"\bhead of design\b",
        r"\bhead of experience\b",
    )
)

# VP band (10%) — still in-scope; generator marks as selective
_VP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bvp[,/ ].{0,40}(product experience|product design|experience|design|ux)\b",
        r"\bvice president.{0,40}(product experience|product design|experience|design|ux)\b",
    )
)

# Principal with enterprise authority — exception only when description is B2B-heavy
_PRINCIPAL_EXCEPTION = re.compile(
    r"\b(principal (product )?designer|principal ux|principal user experience)\b",
    re.IGNORECASE,
)

_OPS_SIGNAL = re.compile(
    r"\b(product operations|operating model|design ops|design operations|"
    r"product strategy.?ops|delivery model|ways of working)\b",
    re.IGNORECASE,
)
_AI_SIGNAL = re.compile(
    r"\b(ai|artificial intelligence|automation|agentic|intelligent workflow|"
    r"machine learning|genai|llm)\b",
    re.IGNORECASE,
)
_ENTERPRISE_SIGNAL = re.compile(
    r"\b(enterprise|b2b|platform|workflow|infrastructure|regulated|"
    r"multi-?stakeholder|telecom|cyber|defense|fintech|saas)\b",
    re.IGNORECASE,
)

_FOUNDER_ALWAYS_BAN = (
    "foundpath",
    "camp luxe",
    "cultivate",
    "until the company takes off",
    "my startups",
)
# Allowed only on the AI-enterprise resume version, as range — never as identity
_VENTURE_NAMES = ("casimir", "winzinvest", "kinlet")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _level_for_title(title: str) -> str | None:
    t = _normalize(title)
    if not t:
        return None
    if any(p.search(t) for p in _EXCLUDE_PATTERNS):
        # Principal exception can still fire below
        if not _PRINCIPAL_EXCEPTION.search(t):
            return None
    if any(p.search(t) for p in _VP_PATTERNS):
        return LEVEL_VP
    if any(p.search(t) for p in _HEAD_PATTERNS):
        return LEVEL_HEAD
    if any(p.search(t) for p in _DIRECTOR_PATTERNS):
        return LEVEL_DIRECTOR
    if _PRINCIPAL_EXCEPTION.search(t):
        return LEVEL_DIRECTOR  # provisional; description must prove enterprise
    return None


def resume_version_for(title: str, description: str = "") -> str:
    """Pick which top-third of the resume to emphasize."""
    blob = f"{title}\n{description}"
    if _OPS_SIGNAL.search(blob) and not re.search(
        r"\b(product design|product experience|ux director|head of design)\b",
        title,
        re.IGNORECASE,
    ):
        return RESUME_PRODUCT_OPS
    if _AI_SIGNAL.search(blob) and re.search(
        r"\b(fintech|defense|public sector|regulated|government|capital|"
        r"trading|healthcare|health)\b",
        blob,
        re.IGNORECASE,
    ):
        return RESUME_AI_ENTERPRISE
    return RESUME_PRODUCT_EXPERIENCE


def is_in_scope_title(title: str, description: str = "") -> bool:
    level = _level_for_title(title)
    if level is None:
        return False
    # Principal IC exception: require enterprise/B2B signal in the posting
    if _PRINCIPAL_EXCEPTION.search(_normalize(title)) and not any(
        p.search(_normalize(title)) for p in _DIRECTOR_PATTERNS + _HEAD_PATTERNS + _VP_PATTERNS
    ):
        return bool(_ENTERPRISE_SIGNAL.search(f"{title}\n{description}"))
    return True


def should_apply(title: str, description: str = "") -> bool:
    """Hard gate: in-scope title band + Stage 1 score, when description exists."""
    if not is_in_scope_title(title, description):
        return False
    if description and stage1_score(title, description) < STAGE1_APPLY_THRESHOLD:
        return False
    return True


def classify_role(title: str, description: str = "") -> RoleTarget | None:
    if not is_in_scope_title(title, description):
        return None
    level = _level_for_title(title)
    if level is None:
        return None
    version = resume_version_for(title, description)
    share = {
        LEVEL_DIRECTOR: "60% core funnel",
        LEVEL_HEAD: "30% when scope matches Comcast Business decision rights",
        LEVEL_VP: "10% selective — warm intro or unusually strong mandate only",
    }[level]
    altitude = {
        LEVEL_DIRECTOR: "Director — product experience + operating-model authority",
        LEVEL_HEAD: "Senior Director / Head — portfolio and executive exposure",
        LEVEL_VP: "VP — selective executive mandate at growth / mid-market B2B",
    }[level]
    headline = {
        LEVEL_DIRECTOR: "Director of Product Experience",
        LEVEL_HEAD: "Head of Product Experience",
        LEVEL_VP: "VP, Product Experience",
    }[level]
    version_instructions = {
        RESUME_PRODUCT_EXPERIENCE: (
            "Resume version: Product Experience Leader. Lead with CVS/Aetna task "
            "completion, Comcast Business scope + maturity program, and Pitney Bowes. "
            "Message: you make difficult enterprise products more usable and build "
            "the org that sustains it."
        ),
        RESUME_PRODUCT_OPS: (
            "Resume version: Product Experience + Operations. Lead with Pitney Bowes, "
            "AI cycle compression, and a Comcast cross-functional decision example. "
            "Message: you improve how product teams decide and deliver, not only UI."
        ),
        RESUME_AI_ENTERPRISE: (
            "Resume version: AI-Enabled Enterprise Workflow. Lead with AI cycle "
            "compression, CVS/Aetna, and at most one line of Casimir or Winzinvest as "
            "range — never as the reason you are applying. Message: you turn AI into "
            "usable, governed workflows for consequential users."
        ),
    }[version]

    return RoleTarget(
        level=level,
        resume_version=version,
        headline=headline,
        altitude=altitude,
        search_share=share,
        instructions=(
            f"Write as a product-experience leader applying for THIS title ({share}). "
            f"Altitude: {altitude}. {version_instructions} "
            "Keep the formal Comcast Business title (Senior UX Lead) and make the "
            "scope line + first bullets prove Director-level ownership. Do not inflate "
            "the title. Do not open with founder identity. Do not raise ventures first. "
            "Mandate: lead product experience for a complex B2B business — the "
            "customer-facing product, the design organization, and the operating model "
            "that ships work. Differentiation: make complex B2B products more usable "
            "while improving the system that produces them."
        ),
    )


# ---------------------------------------------------------------------------
# Stage 1 posting screen (0–10, apply at 7+)
# ---------------------------------------------------------------------------

def stage1_score(title: str, description: str = "", salary: int = 0) -> int:
    """
    Approximate Stage 1 screen from CAREER_TARGETING_STRATEGY_V3.md.
    Returns 0–10. Hard constraint failures return 0.
    """
    blob = f"{title}\n{description}".lower()
    title_l = (title or "").lower()

    # Hard stops
    if not is_in_scope_title(title, description):
        return 0
    if salary and 0 < salary < MIN_BASE_SALARY:
        return 0
    if re.search(r"\b(on-?site only|must relocate|5 days in office)\b", blob):
        if not re.search(r"\b(remote|hybrid|denver|colorado|boulder)\b", blob):
            return 0

    # B2B complexity (0–2)
    if re.search(
        r"\b(enterprise|platform|workflow|infrastructure|regulated|"
        r"multi-?stakeholder|b2b)\b",
        blob,
    ):
        b2b = 2
    elif re.search(r"\b(saas|business|commercial)\b", blob):
        b2b = 1
    elif re.search(r"\b(consumer|agency|dribbble|mobile game)\b", blob):
        b2b = 0
    else:
        b2b = 1

    # Scope (0–2)
    if re.search(
        r"\b(portfolio|cross-functional|transformation|organization|"
        r"operating model|org-level|multi-?product)\b",
        blob,
    ):
        scope = 2
    elif re.search(r"\b(team|manager|lead|product area|squad)\b", blob):
        scope = 1
    else:
        scope = 0

    # Strategic proximity (0–2)
    if re.search(
        r"\b(product strategy|roadmap|business outcome|executive|"
        r"c-level|vp of product|priorit)\b",
        blob,
    ):
        strategy = 2
    elif re.search(r"\b(partner|collaborat|stakeholder)\b", blob):
        strategy = 1
    else:
        strategy = 0

    # AI / automation (0–2)
    if re.search(
        r"\b(ai|automation|intelligent workflow|operating effectiveness|"
        r"agentic|genai)\b",
        blob,
    ):
        # Prefer real brief language over vague innovation
        if re.search(r"\b(innovation lab|cutting-edge|disrupt)\b", blob) and not re.search(
            r"\b(workflow|operating|delivery|adoption)\b", blob
        ):
            ai = 1
        else:
            ai = 2
    elif re.search(r"\b(innovat|digital transform)\b", blob):
        ai = 1
    else:
        ai = 0  # AI absent is OK — multiplier, not required title

    # Practical fit (0–2): level band known + remote/denver-friendly when stated
    practical = 2
    if re.search(r"\b(relocation required|must be in sf|bay area only)\b", blob):
        practical = 0
    elif salary and salary >= MIN_BASE_SALARY:
        practical = 2
    elif re.search(r"\b(remote|denver|colorado|hybrid)\b", blob):
        practical = 2
    else:
        practical = 1

    # VP lane is selective — require stronger B2B + scope signal
    level = _level_for_title(title)
    score = b2b + scope + strategy + ai + practical
    if level == LEVEL_VP and (b2b < 2 or scope < 2):
        return min(score, STAGE1_APPLY_THRESHOLD - 1)

    # Pure design-system-only leadership without product/operating mandate
    if re.search(r"\bdesign systems?\b", title_l) and not re.search(
        r"\b(director|head|vp|product experience|product design|operations)\b",
        title_l,
    ):
        return min(score, STAGE1_APPLY_THRESHOLD - 1)

    return min(score, 10)


def founder_leak_terms(text: str, resume_version: str = RESUME_PRODUCT_EXPERIENCE) -> list[str]:
    """Banned identity language. Venture names allowed only on AI-enterprise version."""
    lower = (text or "").lower()
    leaks = [term for term in _FOUNDER_ALWAYS_BAN if term in lower]
    # "founder" as identity — allow "founded the design systems function" style
    if re.search(r"\b(as a founder|i'?m a founder|founder of|co-founder)\b", lower):
        leaks.append("founder identity")
    if resume_version != RESUME_AI_ENTERPRISE:
        for name in _VENTURE_NAMES:
            if name in lower:
                leaks.append(name)
    return leaks


def targeting_prompt_block(title: str, description: str = "") -> str:
    target = classify_role(title, description)
    if target is None:
        return "This posting is out of scope for Career Targeting Strategy v3. Do not generate materials."

    allow_ventures = target.resume_version == RESUME_AI_ENTERPRISE
    venture_rule = (
        "You may include at most ONE short line on Casimir or Winzinvest as range "
        "(regulated AI / governed automation). Do not lead with it. Do not say you "
        "are applying because a company you founded needs runway."
        if allow_ventures
        else "Do not mention Casimir, Winzinvest, Kinlet, Foundpath, or Camp Luxe. "
        "Ventures are answered only when asked in conversation — never raised first."
    )

    return f"""ROLE TARGETING — Career Strategy v3 (mandatory):
- Job title: {title}
- Level band: {target.level} ({target.search_share})
- Resume version: {target.resume_version}
- Application altitude: {target.altitude}
- Suggested headline calibration: {target.headline} — adapt to the exact posted title, never invent a higher one
- {target.instructions}

MANDATE (one narrative):
Lead product experience for a complex B2B business: the customer-facing product,
the design organization behind it, and the operating model that gets work shipped.
Use AI to make both the product and the organization faster and easier to run.
Differentiation: make complex B2B products more usable while improving the system that produces them.

TITLE BRIDGE:
Keep formal title "Senior UX Lead, Comcast Business". Under it, use the scope line
from the master resume. First bullets must prove organizational scale, business
scope, decision rights, executive audience, and outcome evidence. Do not inflate
the Comcast title. Do not claim P&L or budget unless the master resume states it.

{venture_rule}

DO NOT:
- Open as a founder or explain the ventures unprompted
- Write IC craft letters for Director/Head/VP postings
- Use "transformation" as a headline word without numbers behind it
- Invent team size, user counts, or metrics — use [VERIFY] placeholders as-is or omit
- Apply "supported/oversaw" when the master resume says owned/led/shaped

DO:
- Open naming THIS job title
- Put CVS/Aetna and Pitney Bowes outcomes in the summary (Director-scale proof)
- Match the resume version's lead stories
- Close on wanting the mandate (product experience + operating model), not a parking place
"""
