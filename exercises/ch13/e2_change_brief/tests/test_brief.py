# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 13.2: the structure and the content a reviewer checks
first. Whether the reasoning is right is for a person to judge; compare with the
solution's NOTES.md."""
import re
import unittest

import brief_files

SECTIONS = [
    "Change",
    "Software items affected",
    "Software safety class",
    "Risk",
    "Verification",
    "EU",
    "US",
    "Switzerland",
    "Documents to update",
    "Decision",
]

# Words a section must contain (case-insensitive), as evidence that the question was asked.
MUST_MENTION = {
    "Software items affected": ["SOUP"],
    "Risk": ["ISO 14971", "hazard"],
    "Verification": ["regression", "latency"],
    "EU": ["notified body", "technical documentation"],
    "US": ["510(k)", "Deciding When to Submit a 510(k) for a Software Change"],
    "Switzerland": ["CE"],
    "Documents to update": ["SOUP list", "release notes"],
}

# Claims a reviewer sends back at once.
FORBIDDEN = [
    r"no regulatory impact",
    r"only the operating system",
    r"no need to (re)?test",
]


def sections(text):
    out, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m:
            current = m.group(1)
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


class Brief(unittest.TestCase):
    def setUp(self):
        self.text = brief_files.BRIEF.read_text()
        self.sections = sections(self.text)

    def test_every_section_in_order_and_filled(self):
        self.assertEqual([s for s in self.sections if s in SECTIONS], SECTIONS)
        for s in SECTIONS:
            self.assertGreater(len(self.sections[s].split()), 5, f"section {s!r} is empty")

    def test_fits_on_one_page(self):
        words = len(re.findall(r"\w+", self.text))
        self.assertLessEqual(words, 700, f"{words} words; one page is about 600")

    def test_the_questions_were_asked(self):
        for s, words in MUST_MENTION.items():
            body = self.sections.get(s, "").lower()
            for w in words:
                self.assertIn(w.lower(), body, f"section {s!r} should mention {w!r}")

    def test_no_claim_a_reviewer_rejects(self):
        for pattern in FORBIDDEN:
            self.assertIsNone(re.search(pattern, self.text, re.I), f"remove the claim {pattern!r}")

    def test_the_decision_names_an_owner_and_a_next_step(self):
        d = self.sections["Decision"]
        self.assertRegex(d, r"(?i)\b(regulatory affairs|quality|change control board|ccb)\b")


if __name__ == "__main__":
    unittest.main()
