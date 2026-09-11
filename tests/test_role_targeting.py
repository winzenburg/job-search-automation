#!/usr/bin/env python3
"""Career Targeting Strategy v3 — gates and scoring tests."""

import unittest

from role_targeting import (
    LEVEL_DIRECTOR,
    LEVEL_HEAD,
    LEVEL_VP,
    RESUME_AI_ENTERPRISE,
    RESUME_PRODUCT_EXPERIENCE,
    RESUME_PRODUCT_OPS,
    classify_role,
    founder_leak_terms,
    should_apply,
    stage1_score,
)


DIRECTOR_APPLY = [
    "Director, Product Design",
    "Director of Product Design",
    "Director of Product Experience",
    "Director of UX",
    "Director of Experience Strategy",
    "Director of Product Operations",
    "Director of Design",
    "Design Director, Product Design",
    "Director of Product Design, AI & Agentic Workflows",
]

HEAD_APPLY = [
    "Head of Product Design",
    "Head of Product Experience",
    "Head of Product Design - Remote (US/CANADA)",
    "Senior Director, Product Design",
    "Head of Experience Strategy",
]

VP_APPLY = [
    "VP, Product Design, Growth and Revenue - CNN",
    "Vice President, Product Design & Research",
    "Vice President - Product Design",
]

SKIP = [
    "Senior Staff Product Designer, Risk",
    "Staff UI/UX Product Designer (USA/EMEA - Remote)",
    "Product Manager, ML Foundations and GenAI",
    "Staff Data Engineer",
    "Staff Software Engineer, Developer Productivity",
    "Head of People",
    "Head of Graphic Design (m/w/d)",
    "Brand Design Manager - Remote",
    "Design Manager (Visual)",
    "Course Director: UX, UI, and AI",
    "Engineering Manager, Developer Productivity AI",
    "Staff Front-End Engineer - Design Systems",
    "Senior Manager, Motion Designer (EU)",
    "Art Director - CGI",
    "Digital Web Experience Manager",
    "Merchandising Operations Manager",
    "Lead Sales Compensation Design Manager",
]


ENTERPRISE_DESC = (
    "Enterprise B2B platform for workflow automation across multi-stakeholder "
    "customers. Partner with product leadership on roadmap and operating model. "
    "AI-assisted delivery and cross-functional portfolio ownership. Remote US. "
    "Base compensation $240,000+."
)


class TitleGateTests(unittest.TestCase):
    def test_director_titles_apply(self) -> None:
        for title in DIRECTOR_APPLY:
            with self.subTest(title=title):
                self.assertTrue(
                    should_apply(title, ENTERPRISE_DESC), f"should apply: {title}"
                )

    def test_head_titles_apply(self) -> None:
        for title in HEAD_APPLY:
            with self.subTest(title=title):
                self.assertTrue(should_apply(title, ENTERPRISE_DESC))

    def test_vp_requires_strong_scope(self) -> None:
        weak = "Consumer mobile app. Make screens look great."
        self.assertFalse(should_apply(VP_APPLY[0], weak))
        self.assertTrue(should_apply(VP_APPLY[0], ENTERPRISE_DESC))

    def test_skip_ic_and_off_target(self) -> None:
        for title in SKIP:
            with self.subTest(title=title):
                self.assertFalse(
                    should_apply(title, ENTERPRISE_DESC), f"should skip: {title}"
                )

    def test_principal_exception_needs_enterprise_signal(self) -> None:
        title = "Principal Product Designer"
        self.assertFalse(should_apply(title, "Join our consumer social app"))
        self.assertTrue(
            should_apply(
                title,
                "Enterprise B2B platform, portfolio ownership, product strategy, "
                "cross-functional roadmap, remote, $230k",
            )
        )


class ClassifyTests(unittest.TestCase):
    def test_director_band(self) -> None:
        t = classify_role("Director of Product Experience", ENTERPRISE_DESC)
        assert t is not None
        self.assertEqual(t.level, LEVEL_DIRECTOR)
        self.assertEqual(t.resume_version, RESUME_PRODUCT_EXPERIENCE)

    def test_head_band(self) -> None:
        t = classify_role("Head of Product Design", ENTERPRISE_DESC)
        assert t is not None
        self.assertEqual(t.level, LEVEL_HEAD)

    def test_ops_version(self) -> None:
        t = classify_role(
            "Director of Product Operations",
            "Own the operating model and product operations cadence for an enterprise platform.",
        )
        assert t is not None
        self.assertEqual(t.resume_version, RESUME_PRODUCT_OPS)

    def test_ai_enterprise_version(self) -> None:
        t = classify_role(
            "Director of Product Experience",
            "Fintech and capital-markets workflow software. AI automation for regulated users.",
        )
        assert t is not None
        self.assertEqual(t.resume_version, RESUME_AI_ENTERPRISE)


class Stage1Tests(unittest.TestCase):
    def test_strong_posting_meets_threshold(self) -> None:
        self.assertGreaterEqual(
            stage1_score("Director of Product Design", ENTERPRISE_DESC), 7
        )

    def test_low_salary_hard_stop(self) -> None:
        self.assertEqual(
            stage1_score("Director of Product Design", ENTERPRISE_DESC, salary=180000),
            0,
        )


class LeakTests(unittest.TestCase):
    def test_founder_identity_blocked(self) -> None:
        leaks = founder_leak_terms(
            "As a founder of Winzinvest I am seeking a Director role."
        )
        self.assertTrue(leaks)

    def test_ventures_allowed_only_on_ai_version(self) -> None:
        text = "Range includes Winzinvest rules-based automation."
        self.assertIn("winzinvest", founder_leak_terms(text, RESUME_PRODUCT_EXPERIENCE))
        self.assertEqual(founder_leak_terms(text, RESUME_AI_ENTERPRISE), [])

    def test_clean_director_letter(self) -> None:
        text = (
            "I am applying for Director of Product Experience. "
            "At CVS Health I led experience work during the Aetna merger."
        )
        self.assertEqual(founder_leak_terms(text), [])


if __name__ == "__main__":
    unittest.main()
