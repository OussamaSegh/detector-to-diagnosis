# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 37.2, on a repository made for each test."""
import pathlib
import tempfile
import unittest

from context import problems, references

FILES = ["tools/survey.py", "tools/dicom/encode.py", "docs/releases/0.8.0.md",
         "exercises/ch35/e1_decimal_string/README.md", "minidaq/src/core/crc32.cpp"]
CMAKE = "add_test(NAME tools.dicom COMMAND python3 tools/test_dicom.py)\n"


class Context(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        for f in FILES:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            (self.root / f).write_text("x\n")
        (self.root / "minidaq" / "CMakeLists.txt").write_text(CMAKE)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, text):
        return problems(text, self.root)

    def test_existing_paths_pass(self):
        text = ("Run `tools/survey.py`, read `tools/dicom/` and `minidaq/src/core/crc32.cpp:12`.\n"
                "See `docs/releases/0.8.0.md`.\n")
        self.assertEqual(self.check(text), [])

    def test_missing_paths_are_reported_with_their_line(self):
        text = "Fine: `tools/survey.py`.\nGone: `tools/old_survey.py` and `docs/plans/`.\n"
        self.assertEqual(self.check(text), [(2, "tools/old_survey.py does not exist"),
                                            (2, "docs/plans does not exist")])

    def test_urls_and_other_words_are_not_references(self):
        text = ("Read `https://github.com/tools/x`, use `a/b`, run `git log --oneline`, and "
                "write `Review: items 1/6`.\n")
        self.assertEqual(references(text, {"tools", "docs", "minidaq"}), [])
        self.assertEqual(self.check(text), [])

    def test_placeholders_are_patterns(self):
        text = ("Each exercise is `exercises/chNN/<exercise>/` and each record "
                "`docs/releases/X.Y.Z.md`.\n")
        self.assertEqual(self.check(text), [])
        missing = "Notes in `docs/notes/X.Y.Z.md` and `tools/chNN/*.py`.\n"
        self.assertEqual(self.check(missing), [(1, "nothing matches docs/notes/X.Y.Z.md"),
                                               (1, "nothing matches tools/chNN/*.py")])

    def test_fenced_blocks_and_tests_are_checked(self):
        text = ("Build:\n\n```\npython3 tools/survey.py .\npython3 tools/gone.py .\n"
                "ctest --preset debug -R tools.dicom\nctest --preset debug -R tools.gone\n```\n"
                "And `ctest -R tools.dicom` again.\n")
        self.assertEqual(self.check(text), [(5, "tools/gone.py does not exist"),
                                            (7, "no test named tools.gone")])


if __name__ == "__main__":
    unittest.main()
