#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/post_release.py (roadmap 2.0.0, Theme D)."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import post_release as pr  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def tree(base, version="1.1.0", py="1.1.0", changelog="# Changelog\n\n## [1.1.0] - 2026-11-10\n"):
    (base / "VERSION").write_text(version + "\n")
    for rel, line in (("analysis/pyproject.toml", f'[project]\nname = "a"\nversion = "{py}"\n'),
                      ("analysis/src/minidaq_analysis/__init__.py", f'"""x"""\n__version__ = "{py}"\n'),
                      ("recon/python/pyproject.toml", f'[project]\nversion = "{py}"\n')):
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text(line)
    (base / "CHANGELOG.md").write_text(changelog)
    rel = base / "docs/regulatory/releases"
    rel.mkdir(parents=True, exist_ok=True)
    for v in ("1.0.0", "1.1.0", "0.10.0"):
        (rel / f"{v}.md").write_text("record\n")
    (rel / "README.md").write_text("not a record\n")


class PostRelease(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)
        tree(self.root)

    def tearDown(self):
        self.dir.cleanup()

    def test_python_spelling(self):
        self.assertEqual(pr.python_version("1.2.0-dev"), "1.2.0.dev0")
        self.assertEqual(pr.python_version("2.0.0"), "2.0.0")
        for bad in ("1.2", "v1.2.0", "1.2.0-rc1", ""):
            with self.assertRaises(ValueError):
                pr.python_version(bad)

    def test_after_a_release_the_next_patch_dev_everywhere(self):
        self.assertEqual(pr.main(["x", str(self.root)]), 0)
        self.assertEqual((self.root / "VERSION").read_text(), "1.1.1-dev\n")
        self.assertEqual(pr.disagreements(self.root, "1.1.1-dev"), [])
        self.assertIn("## [Unreleased]\n\n## [1.1.0]", (self.root / "CHANGELOG.md").read_text())
        self.assertEqual(pr.main(["x", str(self.root), "--check"]), 0)

    def test_versions_compare_as_numbers(self):
        self.assertEqual(pr.next_dev(["0.9.0", "0.10.0"]), "0.10.1-dev")

    def test_a_new_minor_version_asks_for_a_soup_review(self):
        notes = pr.set_version(self.root, "1.2.0-dev")
        self.assertTrue(any("soup-list.md" in n for n in notes))
        self.assertFalse(any("soup-list.md" in n for n in pr.set_version(self.root, "1.2.0")))

    def test_check_finds_a_package_left_behind(self):
        tree(self.root, version="1.1.1-dev", py="1.1.0")
        self.assertEqual(pr.main(["x", str(self.root), "--check"]), 1)
        self.assertEqual(len(pr.disagreements(self.root, "1.1.1-dev")), 3)

    def test_a_bad_version_writes_nothing(self):
        self.assertEqual(pr.main(["x", str(self.root), "1.2"]), 1)
        self.assertEqual((self.root / "VERSION").read_text(), "1.1.0\n")

    def test_a_place_without_a_version_line_writes_nothing(self):
        # Review of 1.2.0: VERSION used to be written before the packages were read.
        (self.root / "recon/python/pyproject.toml").write_text("[project]\n")
        self.assertEqual(pr.main(["x", str(self.root), "1.2.0-dev"]), 1)
        self.assertEqual((self.root / "VERSION").read_text(), "1.1.0\n")
        self.assertIn('"1.1.0"', (self.root / "analysis/pyproject.toml").read_text())

    def test_an_existing_unreleased_section_is_kept(self):
        text = "# C\n\n## [Unreleased]\n\n- x\n\n## [1.1.0]\n"
        self.assertEqual(pr.with_unreleased(text), text)

    def test_the_repository_agrees_with_itself(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertEqual(pr.disagreements(ROOT, version), [])


if __name__ == "__main__":
    unittest.main()
