# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 6.3. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this)."""
import pathlib
import tempfile
import unittest

import adr_lint
import adr_location

GOOD = """# 0002. Use a ring buffer between stages

Date: 2026-11-02
Status: Accepted

## Context

Stages run on separate threads.

## Options

1. A mutex queue.
2. An SPSC ring of batches.

## Decision

Option 2.

## Consequences

### Positive

- Fast.

### Negative

- Fixed capacity.
"""


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def write(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p


class LintFile(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.tmp.cleanup()

    def problems(self, text, name="0002-use-a-ring.md"):
        return adr_lint.lint_file(self.f.write(name, text))

    def assertProblem(self, problems, *words):
        joined = " | ".join(problems).lower()
        for w in words:
            self.assertIn(w.lower(), joined, f"expected a problem mentioning '{w}', got: {problems}")

    def test_a_good_record_has_no_problems(self):
        self.assertEqual(self.problems(GOOD), [])

    def test_options_as_subsections_also_count(self):
        text = GOOD.replace("1. A mutex queue.\n2. An SPSC ring of batches.",
                            "### Mutex queue\n\nSlow.\n\n### SPSC ring\n\nFast.")
        self.assertEqual(self.problems(text), [])

    def test_file_name(self):
        self.assertProblem(self.problems(GOOD, "2-ring.md"), "file name")
        self.assertProblem(self.problems(GOOD, "0002_Use_A_Ring.md"), "file name")

    def test_title_line_and_number(self):
        self.assertProblem(self.problems(GOOD.replace("# 0002. ", "# ")), "first line")
        self.assertProblem(self.problems(GOOD.replace("# 0002.", "# 0003.")), "0003", "0002")

    def test_date(self):
        self.assertProblem(self.problems(GOOD.replace("Date: 2026-11-02\n", "")), "date")
        self.assertProblem(self.problems(GOOD.replace("2026-11-02", "2026-13-02")), "date")

    def test_status(self):
        self.assertProblem(self.problems(GOOD.replace("Status: Accepted\n", "")), "status")
        self.assertProblem(self.problems(GOOD.replace("Accepted", "Done")), "status")
        for ok in ("Proposed", "Rejected", "Deprecated", "Superseded by 0007"):
            self.assertEqual(self.problems(GOOD.replace("Accepted", ok)), [], ok)

    def test_required_sections(self):
        for h in ("Context", "Options", "Decision", "Consequences"):
            text = GOOD.replace(f"## {h}\n", f"## Something else\n")
            self.assertProblem(self.problems(text), h)

    def test_empty_section(self):
        self.assertProblem(self.problems(GOOD.replace("Option 2.\n", "")), "decision", "empty")

    def test_section_order(self):
        text = GOOD.replace("## Decision\n\nOption 2.\n\n", "")
        text = text.replace("## Context\n", "## Decision\n\nOption 2.\n\n## Context\n")
        self.assertProblem(self.problems(text), "order")

    def test_at_least_two_options(self):
        self.assertProblem(self.problems(GOOD.replace("2. An SPSC ring of batches.\n", "")), "two options")

    def test_positive_and_negative_consequences(self):
        self.assertProblem(self.problems(GOOD.replace("### Negative\n\n- Fixed capacity.\n", "")), "negative")
        self.assertProblem(self.problems(GOOD.replace("- Fast.\n", "")), "positive", "empty")


class LintDir(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.tmp.cleanup()

    def good(self, n, slug="x", status="Accepted"):
        text = GOOD.replace("# 0002.", f"# {n:04d}.").replace("Accepted", status)
        self.f.write(f"{n:04d}-{slug}.md", text)

    def test_clean_directory(self):
        self.good(1)
        self.good(2)
        self.f.write("README.md", "# Index\n")
        result = adr_lint.lint_dir(self.f.dir)
        self.assertEqual(set(result), {"0001-x.md", "0002-x.md"}, "README is not an ADR")
        self.assertTrue(all(not p for p in result.values()), result)

    def test_gaps_and_duplicates(self):
        self.good(1)
        self.good(3)
        self.assertIn("(directory)", adr_lint.lint_dir(self.f.dir))
        self.good(3, slug="y")
        problems = " ".join(adr_lint.lint_dir(self.f.dir).get("(directory)", []))
        self.assertIn("duplicate", problems.lower())

    def test_superseded_by_must_exist(self):
        self.good(1, status="Superseded by 0002")
        self.assertTrue(any("0002" in p for p in adr_lint.lint_dir(self.f.dir)["0001-x.md"]))
        self.good(2)
        self.assertEqual(adr_lint.lint_dir(self.f.dir)["0001-x.md"], [])


class YourRecords(unittest.TestCase):
    """The three ADRs the exercise asks for: queue, file format, control protocol."""

    def setUp(self):
        self.result = adr_lint.lint_dir(adr_location.ADR_DIR)
        self.titles = {}
        for name in self.result:
            if name != "(directory)":
                first = (pathlib.Path(adr_location.ADR_DIR) / name).read_text(encoding="utf-8").splitlines()[0]
                self.titles[name] = first.lower()

    def test_they_pass_the_linter(self):
        bad = {k: v for k, v in self.result.items() if v}
        self.assertEqual(bad, {})

    def test_the_three_topics_are_covered(self):
        topics = {"queue": ("queue", "channel", "spsc", "ring"),
                  "file format": ("file format", "list-mode", "listmode"),
                  "control protocol": ("protocol", "control api")}
        for topic, words in topics.items():
            self.assertTrue(any(any(w in t for w in words) for t in self.titles.values()),
                            f"no ADR title about the {topic}: {sorted(self.titles.values())}")


if __name__ == "__main__":
    unittest.main()
