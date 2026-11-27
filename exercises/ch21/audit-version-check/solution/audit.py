# SPDX-License-Identifier: MIT
"""Exercise 21.6 (A): tests of the agent's version rules, one per commit in the life of a
release and per kind of text a VERSION file can hold."""
import unittest

RELEASED = ["0.2.0", "0.3.0"]


class Audit(unittest.TestCase):
    subject = None  # set by tests/test_audit.py

    def ok(self, version, subject, released=RELEASED):
        self.assertEqual(self.subject.problems(version, subject, released), [], (version, subject))

    def refused(self, version, subject, released=RELEASED):
        self.assertTrue(self.subject.problems(version, subject, released), (version, subject))

    def test_a_dev_version_after_the_newest_release_is_right(self):
        self.ok("0.4.0-dev", "Add the sorter")

    def test_a_dev_version_not_after_the_newest_release_is_refused(self):
        self.refused("0.3.0-dev", "Add the sorter")
        self.refused("0.2.5-dev", "Add the sorter")

    def test_the_release_version_in_its_release_commit_is_right(self):
        self.ok("0.4.0", "Release 0.4.0")
        self.ok("0.3.0", "Release 0.3.0")  # the record is written in the release commit

    def test_the_release_version_in_the_commit_that_lists_its_tag_is_right(self):
        self.ok("0.3.0", "Tag book-v0.3.0 on the release commit")

    def test_a_release_version_in_any_later_commit_is_refused(self):
        # The crash report of such a build names the release: an investigator reads the
        # release's code, not the code that crashed (Chapter 21).
        self.refused("0.3.0", "Chapter 16: the QMS")
        self.refused("0.3.0", "Tag book-v0.2.0 on the release commit")

    def test_a_release_version_in_another_release_commit_is_refused(self):
        self.refused("0.3.0", "Release 0.4.0")

    def test_text_that_is_not_a_version_is_refused(self):
        for text in ("", "0.4", "0.4.0-rc1", "v0.4.0", "0.4.0 ", " 0.4.0", "0.4.0-dev\n",
                     "0.4.0\n", "0.4.0\n0.5.0"):
            with self.subTest(text=text):
                self.refused(text, "Release 0.4.0")
