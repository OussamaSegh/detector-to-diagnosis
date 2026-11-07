# SPDX-License-Identifier: MIT
"""Acceptance tests of Exercise 36.1, with git itself as the oracle."""
import subprocess
import unittest

from trailers import trailers, value

MESSAGES = [
    "Fix the sorter\n\nBody.\n\nReview: items 1 to 6.\nTested-by: A <a@example.org>\n",
    "Fix\n\nBody.\n\nReview: items 1 to 6.\n\nCo-Authored-By: B <b@example.org>\n",
    "Fix: the sorter\n",
    "Fix: the sorter\nReview: ok\n",
    "Fix\n\nBody.\n\nReview: ok\nThis line is prose.\n",
    "Fix\n\nBody.\n\nReview: items 1\n  to 6\nTested-by: C <c@example.org>\n",
    "Fix\n\nBody.\n\nReview: ok\n\n\n",
    "Fix\n\nhttps://example.org/a\n",
    "Fix\n\nNote: the body says this.\nAnd more prose.\n\nReview: ok\n",
    "Fix\n\n",
]


def git(message):
    out = subprocess.run(["git", "interpret-trailers", "--parse"], input=message,
                         capture_output=True, text=True, check=True).stdout
    return [tuple(x.strip() for x in line.split(":", 1)) for line in out.splitlines()]


URL = "Fix\n\nhttps://example.org/a\n"


class Trailers(unittest.TestCase):
    def test_agrees_with_git(self):
        # Git changed its rule: 2.43 took the scheme of a URL for a key, 2.56 does not. The
        # exercise follows the newer git; on an older one that case is checked by the next test.
        old_git = bool(git(URL))
        for message in MESSAGES:
            if old_git and message == URL:
                continue
            with self.subTest(message=message):
                self.assertEqual(trailers(message), git(message))

    def test_a_url_is_not_a_trailer(self):
        self.assertEqual(trailers(URL), [])

    def test_review_above_a_blank_line_is_not_a_trailer(self):
        self.assertEqual(trailers(MESSAGES[1]), [("Co-Authored-By", "B <b@example.org>")])

    def test_a_continuation_joins_its_value(self):
        self.assertEqual(trailers(MESSAGES[5])[0], ("Review", "items 1 to 6"))


class Value(unittest.TestCase):
    def test_keys_compare_without_case(self):
        message = "Fix\n\nBody.\n\nreview: first\nTested-by: x\nReview: second\n"
        self.assertEqual(value(message, "Review"), ["first", "second"])
        self.assertEqual(value(message, "REVIEW"), ["first", "second"])
        self.assertEqual(value(MESSAGES[1], "Review"), [])


if __name__ == "__main__":
    unittest.main()
