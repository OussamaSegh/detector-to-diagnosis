# SPDX-License-Identifier: MIT
"""Acceptance tests for Exercise 21.5. Run: python3 -m unittest discover -s tests
with the starter or solution directory on PYTHONPATH (CTest does this). Needs git."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import bisect_tool as bt

GOOD = "def answer():\n    return 42\n"
BAD = "def answer():\n    return 41\n"
BROKEN = "def answer(:\n    return 42\n"  # does not import


def make_repo(root, n=40, bad_at=25, broken=()):
    """n commits; from commit bad_at on, answer() is wrong; the commits in `broken` do not import.
    Returns the SHA-1 of every commit, the first at index 0."""
    def git(*args):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

    root.mkdir(parents=True)
    git("init", "-q")
    shas = []
    for i in range(n):
        text = BROKEN if i in broken else (BAD if i >= bad_at else GOOD)
        (root / "app.py").write_text(text)
        (root / "notes.txt").write_text(f"commit {i}\n")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", f"commit {i}")
        shas.append(subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                                   capture_output=True, text=True).stdout.strip())
    return shas


@unittest.skipUnless(shutil.which("git"), "git not installed")
class Bisect(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_a_clean_history(self):
        shas = make_repo(self.tmp / "r", bad_at=25)
        self.assertEqual(bt.first_bad(self.tmp / "r", shas[0], shas[-1]), [shas[25]])

    def test_a_commit_that_does_not_build_is_skipped_not_blamed(self):
        # Commits 18 to 21 do not import, and bisect tests one of them first. Calling them bad
        # blames commit 18.
        shas = make_repo(self.tmp / "r", bad_at=25, broken={18, 19, 20, 21})
        self.assertEqual(bt.first_bad(self.tmp / "r", shas[0], shas[-1]), [shas[25]])

    def test_broken_commits_next_to_the_defect_leave_candidates(self):
        # Commits 23 and 24 do not import, 25 is the first bad one: bisect cannot tell whether
        # 23, 24 or 25 broke it, and must say so instead of guessing.
        shas = make_repo(self.tmp / "r", bad_at=25, broken={23, 24})
        self.assertEqual(sorted(bt.first_bad(self.tmp / "r", shas[0], shas[-1])), sorted(shas[23:26]))

    def test_the_check_says_skip_for_a_commit_that_does_not_build(self):
        d = self.tmp / "w"
        d.mkdir()
        (d / "app.py").write_text(BROKEN)
        self.assertEqual(bt.check(d), 125)
        (d / "app.py").write_text(BAD)
        self.assertEqual(bt.check(d), 1)
        (d / "app.py").write_text(GOOD)
        self.assertEqual(bt.check(d), 0)

    def test_the_repository_is_left_as_it_was(self):
        shas = make_repo(self.tmp / "r", bad_at=5, n=12)
        bt.first_bad(self.tmp / "r", shas[0], shas[-1])
        head = subprocess.run(["git", "-C", str(self.tmp / "r"), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip()
        self.assertEqual(head, shas[-1], "bisect reset afterwards")


if __name__ == "__main__":
    unittest.main()
