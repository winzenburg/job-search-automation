#!/usr/bin/env python3
"""Role-targeting gates — in-scope design jobs vs. the spray of off-target titles."""

import unittest

from role_targeting import (
    DESIGN_LEADERSHIP,
    DESIGN_OPS_SYSTEMS,
    PRODUCT_DESIGN_IC,
    classify_role,
    founder_leak_terms,
    should_apply,
)


APPLY = [
    "Director, Product Design",
    "Director of Product Design",
    "Director of Product Design, AI & Agentic Workflows",
    "Head of Product Design",
    "Head of Product Design - Remote (US/CANADA)",
    "VP, Product Design, Growth and Revenue - CNN",
    "Vice President, Product Design & Research",
    "Vice President - Product Design",
    "Principal Product Designer",
    "Principal Product Designer, Storytelling",
    "Senior Staff Product Designer, Risk",
    "Staff UI/UX Product Designer (USA/EMEA - Remote)",
    "Senior Staff Product Designer, Finance",
    "Design Director, Product Design",
    "Manager - Product Design",
    "Design Manager",
    "UX Manager",
    "Principal Design Engineer, Storytelling",
    "Design Systems Lead",
    "Senior Design Systems Manager",
    "Design Operations Lead",
    "Staff Product Designer",
    "Product Designer - Platform Experience",
    "Creative Technologist",
]

SKIP = [
    "Product Manager, ML Foundations and GenAI",
    "Product Manager, Sail Core",
    "Staff Product Manager, Link Consumer Product",
    "Staff Product Manager, Dashboard",
    "Senior Manager, Motion Designer (EU)",
    "Director, Brand & Creative",
    "Staff Data Engineer",
    "Staff Software Engineer, Developer Productivity",
    "Sales Excellence Manager, Global Sales Vendors",
    "Program Manager, Performance and Talent Planning",
    "Risk Strategist, Onboarding and Compliance",
    "Operations Program Manager, Tax",
    "Head of Graphic Design (m/w/d)",
    "Head of People",
    "Merchandising Operations Manager",
    "Lead Sales Compensation Design Manager",
    "Staff Mechanical Product Development Engineer- Integrated Predictive Analysis",
    "Director of Customer Success",
    "Head of Marketing & Communications",
    "Art Director - CGI",
    "Staff Brand Designer",
    "Brand Design Manager - Remote",
    "Design Manager (Visual)",
    "Course Director: UX, UI, and AI",
    "Engineering Manager, Developer Productivity AI",
    "Staff Front-End Engineer - Design Systems",
    "Digital Web Experience Manager",
    "Associate Director, Digital Experience & AI Production",
    "PRODUCT MANAGER III (Remote)",
]


class ShouldApplyTests(unittest.TestCase):
    def test_apply_titles(self) -> None:
        for title in APPLY:
            with self.subTest(title=title):
                self.assertTrue(should_apply(title), f"should apply: {title}")

    def test_skip_titles(self) -> None:
        for title in SKIP:
            with self.subTest(title=title):
                self.assertFalse(should_apply(title), f"should skip: {title}")

    def test_description_cannot_rescue_off_target_title(self) -> None:
        self.assertFalse(
            should_apply(
                "Staff Data Engineer",
                "We care deeply about design systems, UX, and AI product design.",
            )
        )


class ClassifyRoleTests(unittest.TestCase):
    def test_ic(self) -> None:
        target = classify_role("Senior Staff Product Designer, Risk")
        assert target is not None
        self.assertEqual(target.family, PRODUCT_DESIGN_IC)

    def test_leadership(self) -> None:
        target = classify_role("Director, Product Design")
        assert target is not None
        self.assertEqual(target.family, DESIGN_LEADERSHIP)

    def test_ops(self) -> None:
        target = classify_role("Design Systems Lead")
        assert target is not None
        self.assertEqual(target.family, DESIGN_OPS_SYSTEMS)

    def test_out_of_scope_is_none(self) -> None:
        self.assertIsNone(classify_role("Head of People"))


class FounderLeakTests(unittest.TestCase):
    def test_detects_founder_framing(self) -> None:
        leaks = founder_leak_terms(
            "As founder of Winzinvest and Casimir Systems I am seeking a Director role."
        )
        self.assertIn("founder", leaks)
        self.assertIn("winzinvest", leaks)
        self.assertIn("casimir", leaks)

    def test_clean_letter_has_no_leaks(self) -> None:
        text = (
            "I am applying for the Principal Product Designer role. "
            "At CVS Health I led the experience for core digital workflows."
        )
        self.assertEqual(founder_leak_terms(text), [])


if __name__ == "__main__":
    unittest.main()
