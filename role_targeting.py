#!/usr/bin/env python3
"""
Role-first targeting for job applications.

Hiring managers for Product Design / Design Ops / Design Leadership roles
should see an employed designer who can do *this job* — not a founder
running parallel companies. This module:

1. Decides whether a posting is in-scope (title must be a design/UX role).
2. Classifies the posting into a role family so resume + cover letter
   match the altitude of the job (IC vs. manager vs. design ops).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Role families
# ---------------------------------------------------------------------------

PRODUCT_DESIGN_IC = "product_design_ic"
DESIGN_LEADERSHIP = "design_leadership"
DESIGN_OPS_SYSTEMS = "design_ops_systems"

ROLE_FAMILIES = (PRODUCT_DESIGN_IC, DESIGN_LEADERSHIP, DESIGN_OPS_SYSTEMS)


@dataclass(frozen=True)
class RoleTarget:
    family: str
    headline: str
    altitude: str
    instructions: str


FAMILY_TARGETS: dict[str, RoleTarget] = {
    PRODUCT_DESIGN_IC: RoleTarget(
        family=PRODUCT_DESIGN_IC,
        headline="Product Designer",
        altitude="individual contributor",
        instructions=(
            "Write as a hands-on product designer applying for THIS title. "
            "Lead with shipped product work, research, IA, interaction design, "
            "and design-system contribution. Mentoring is a supporting point "
            "only if the posting asks for it. Do not pitch org design, P&L, "
            "or executive transformation. Keep employed titles accurate, but "
            "choose bullets that prove you will do the work of this role."
        ),
    ),
    DESIGN_LEADERSHIP: RoleTarget(
        family=DESIGN_LEADERSHIP,
        headline="Design Leader",
        altitude="manager / director",
        instructions=(
            "Write as a design leader applying for THIS title. Lead with team "
            "direction, product partnership, quality, and how you help a design "
            "org ship. Stay inside the scope of the posting — do not inflate "
            "to VP/C-level or company-building. Proof should come from "
            "employed roles (CVS Health, Life Time, Pitney Bowes, Buildout)."
        ),
    ),
    DESIGN_OPS_SYSTEMS: RoleTarget(
        family=DESIGN_OPS_SYSTEMS,
        headline="Design Systems / Design Operations",
        altitude="systems / operations",
        instructions=(
            "Write as a design systems or design operations specialist for "
            "THIS title. Lead with pattern libraries, governance, handoff, "
            "multi-team consistency, and workflow design. Employed roles at "
            "Pitney Bowes, CVS Health, and Life Time are the primary proof."
        ),
    ),
}


# Titles we will apply to. Require a design/UX signal in the TITLE, not the
# description — description-only matching is how "Staff Data Engineer" and
# "Head of People" slipped through.
_INCLUDE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bproduct designer\b",
        r"\bux designer\b",
        r"\bui designer\b",
        r"\bux/?ui\b",
        r"\bui/?ux\b",
        r"\buser experience\b",
        r"\bdesign systems?\b",
        r"\bdesign ops\b",
        r"\bdesign operations\b",
        r"\bhead of design\b",
        r"\bhead of product design\b",
        r"\bdirector of (?:product )?design\b",
        r"\bdirector[,/ ]+product design\b",
        r"\bdirector[,/ ]+design\b",
        r"\bvp[,/ ].{0,40}product design\b",
        r"\bvp[,/ ].{0,40}\bdesign\b",
        r"\bvice president.{0,40}design\b",
        r"\bdesign director\b",
        r"\bdesign manager\b",
        r"\bux manager\b",
        r"\bproduct design manager\b",
        r"\bmanager.{0,20}product design\b",
        r"\bmanager.{0,20}\bux\b",
        r"\bdesign lead\b",
        r"\bux lead\b",
        r"\bproduct design lead\b",
        r"\bcreative technologist\b",
        r"\bdesign technologist\b",
        r"\bprincipal designer\b",
        r"\bstaff designer\b",
        r"\bstaff product designer\b",
        r"\bsenior product designer\b",
        r"\bsenior ux\b",
        r"\bsenior staff product designer\b",
        r"\bprincipal product designer\b",
        r"\bdesign engineer\b",
        r"\bproduct design\b",
    )
)

# Even with a design keyword, these are the wrong job.
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
        r"\bhead of people\b",
        r"\bcourse director\b",
        r"\binstructor\b",
        r"\bprofessor\b",
        r"\bproduct manager\b",
        r"\bstaff product manager\b",
        r"\bsales\b",
        r"\bidentity.{0,20}access\b",
        r"\bonboarding and compliance\b",
        r"\bperformance and talent\b",
        r"\bintake.{0,20}portfolio\b",
        r"\bweb experience manager\b",
        r"\bdigital web experience\b",
        r"\bai production\b",
        r"\bvisual\)",
        r"\(visual\)",
        r"\bbrand design\b",
        r"\bstaff brand\b",
        r"\bhead of people\b",
    )
)

_FOUNDER_LEAK_WORDS = (
    "founder",
    "co-founder",
    "cofounder",
    "founding",
    "i founded",
    "my startup",
    "my company",
    "my companies",
    "winzinvest",
    "casimir",
    "foundpath",
    "kinlet",
    "camp luxe",
    "cultivate",
    "principal investigator",
    "sbir",
    "raising capital",
    "fundraising",
)

_LEADERSHIP_TITLE = re.compile(
    r"\b(director|vp|vice president|head of|chief|cdo)\b",
    re.IGNORECASE,
)
_OPS_TITLE = re.compile(
    r"\b(design ops|design operations|design systems?)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def is_in_scope_title(title: str) -> bool:
    """True when the job TITLE is a product design / UX / design-ops role."""
    t = _normalize(title)
    if not t:
        return False
    if any(p.search(t) for p in _EXCLUDE_PATTERNS):
        return False
    return any(p.search(t) for p in _INCLUDE_PATTERNS)


def should_apply(title: str, description: str = "") -> bool:
    """
    Gate for scanner + apply pipeline.

    Description is accepted for API compatibility but is not used to include
    a role. Off-target jobs often mention "design" in the body.
    """
    del description
    return is_in_scope_title(title)


def classify_role(title: str) -> RoleTarget | None:
    """Return the role family for an in-scope title, or None if we should skip."""
    if not is_in_scope_title(title):
        return None
    t = _normalize(title)
    if _OPS_TITLE.search(t) and not _LEADERSHIP_TITLE.search(t):
        return FAMILY_TARGETS[DESIGN_OPS_SYSTEMS]
    if _LEADERSHIP_TITLE.search(t) or re.search(
        r"\b(design manager|ux manager|product design manager|manager.{0,20}product design)\b",
        t,
        re.IGNORECASE,
    ):
        return FAMILY_TARGETS[DESIGN_LEADERSHIP]
    return FAMILY_TARGETS[PRODUCT_DESIGN_IC]


def founder_leak_terms(text: str) -> list[str]:
    """Return banned founder terms found in generated application copy."""
    lower = (text or "").lower()
    return [term for term in _FOUNDER_LEAK_WORDS if term in lower]


def targeting_prompt_block(title: str) -> str:
    """Prompt fragment injected into resume/cover-letter generation."""
    target = classify_role(title)
    if target is None:
        return (
            "This posting is out of scope. Do not generate application materials."
        )
    banned = ", ".join(f'"{w}"' for w in _FOUNDER_LEAK_WORDS)
    return f"""ROLE TARGETING (mandatory):
- Job title: {title}
- Role family: {target.family}
- Application altitude: {target.altitude}
- Headline to match: {target.headline} — adapt to the exact job title, not a higher one
- {target.instructions}

DO NOT use these words or names anywhere in the resume or cover letter:
{banned}

DO NOT:
- Describe the candidate as a founder, owner, or someone building their own companies
- Imply they will leave when a side project takes off
- Overshoot the role (do not write as a VP/CDO when the job is IC or Director)
- Lead with independent/consulting work if employed roles prove the requirement

DO:
- Open as someone applying to THIS job
- Prove fit with employed experience (CVS Health/Aetna, Life Time, Pitney Bowes, Buildout, DOI, Level 3, AOL/MapQuest, Aspenware)
- Keep independent consulting (2023–present) to 2–3 bullets that map to the posting, titled as consulting — never as founding
- Match seniority: IC letters sound like a designer; leadership letters sound like a design manager/director
"""
