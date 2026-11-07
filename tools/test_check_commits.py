#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/check_commits.py (Chapter 36), run by CTest as tools.commits.

The trailer parser is checked against git's own (`git interpret-trailers --parse`) on messages
chosen at the edges of git's rule; the rules on commits written as dictionaries; the whole check
on small repositories made for the test, with a policy, an SRS, a change request and a history.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_commits  # noqa: E402

# Built at run time, so that this file does not itself add an address the pre-commit hook refuses.
PERSONAL = "someone" + "@" + "mail.example.net"
POLICY = json.loads((pathlib.Path(__file__).resolve().parent / "commit_policy.json").read_text())

MESSAGES = {
    "trailers only": "Fix the sorter\n\nBody.\n\nReview: items 1 to 6.\nSigned-off-by: A <a@x>\n",
    "review in the body": "Fix\n\nBody.\n\nReview: items 1 to 6.\n\nCo-Authored-By: B <b@x>\n",
    "subject only": "Fix: the sorter\n",
    "subject and a trailer paragraph": "Fix\n\nReview: ok\n",
    "a sentence in the block": "Fix\n\nBody.\n\nReview: ok\nThis line is prose.\n",
    "git generated, 25 percent": "Fix\n\nBody.\n\nprose one\nprose two\nprose three\n"
                                 "Signed-off-by: A <a@x>\n",
    "git generated, below 25 percent": "Fix\n\nBody.\n\none\ntwo\nthree\nfour\n"
                                       "Signed-off-by: A <a@x>\n",
    "continuation": "Fix\n\nBody.\n\nReview: items 1\n  to 6\nTested-by: C <c@x>\n",
    "trailing blank lines": "Fix\n\nBody.\n\nReview: ok\n\n\n",
    "a URL is not a key": "Fix\n\nhttps://example.org/x\n",
    "no space after the colon": "Fix\n\nBody.\n\nReview:ok\n",
}


def git_trailers(message):
    out = subprocess.run(["git", "interpret-trailers", "--parse"], input=message,
                         capture_output=True, text=True, check=True).stdout
    return [tuple(x.strip() for x in line.split(":", 1)) for line in out.splitlines()]


def commit(message="Fix the sorter\n\nBody.\n\nReview: items 1 to 6.\n", parents=("a",),
           author=("t", "t@example.invalid"), files=(), controlled=()):
    return {"sha": "1234567890abcdef", "parents": list(parents), "author": author,
            "committer": author, "message": message, "files": list(files),
            "controlled": list(controlled)}


KNOWN = {"names": {"CR-0001", "MDQ-PR-007"}, "commits": {"abcdef1"}}


class Trailers(unittest.TestCase):
    def test_agrees_with_git_at_the_edges_of_its_rule(self):
        # REQ: SRS-GIT-001
        # Git changed its rule: 2.43 took the scheme of a URL for a key, 2.56 does not. The check
        # follows the newer git; on an older one the URL case is checked without the oracle.
        old_git = bool(git_trailers(MESSAGES["a URL is not a key"]))
        for name, message in MESSAGES.items():
            with self.subTest(name):
                if old_git and name == "a URL is not a key":
                    self.assertEqual(check_commits.trailers(message), [])
                    continue
                self.assertEqual(check_commits.trailers(message), git_trailers(message))

    def test_a_review_line_above_a_blank_line_is_not_a_trailer(self):
        # REQ: SRS-GIT-001
        self.assertEqual(check_commits.trailers(MESSAGES["review in the body"]),
                         [("Co-Authored-By", "B <b@x>")])
        self.assertEqual(check_commits.trailers(MESSAGES["continuation"])[0],
                         ("Review", "items 1 to 6"))


class Rules(unittest.TestCase):
    def test_identity_wants_no_reply_addresses(self):
        # REQ: SRS-GIT-002
        self.assertEqual(check_commits.identity(commit(), POLICY), [])
        noreply = ("u", "123+u@users.noreply.github.com")
        self.assertEqual(check_commits.identity(commit(author=noreply), POLICY), [])
        bad = check_commits.identity(commit(author=("u", PERSONAL)), POLICY)
        self.assertEqual(len(bad), 2)  # author and committer
        self.assertNotIn("mail.example.net", " ".join(bad))  # the report does not repeat it

    def test_subject_and_layout(self):
        # REQ: SRS-GIT-003
        self.assertEqual(check_commits.subject(commit(), POLICY), [])
        self.assertEqual(check_commits.layout(commit(), POLICY), [])
        long_subject = "x" * 73 + "\n\nBody.\n"
        self.assertIn("73 characters", check_commits.subject(commit(long_subject), POLICY)[0])
        self.assertTrue(check_commits.subject(commit("Fix the sorter.\n"), POLICY))
        for s in ("fixup! Fix the sorter", "squash! x", "WIP sorter", "amend! x"):
            self.assertTrue(check_commits.subject(commit(s + "\n"), POLICY), s)
        self.assertTrue(check_commits.layout(commit("Fix\nBody at once.\n"), POLICY))
        body = "Fix\n\n" + "y" * 73 + "\n    " + "z" * 90 + "\nhttps://example.org/" + "u" * 80
        body += "\n\nReview: " + "r" * 90 + "\n"
        self.assertEqual(check_commits.layout(commit(body), POLICY),
                         ["line 3 has 73 characters (at most 72)"])

    def test_review_must_be_a_trailer_git_parses(self):
        # REQ: SRS-GIT-004
        self.assertEqual(check_commits.review(commit(), POLICY), [])
        self.assertIn("not in the trailer block",
                      check_commits.review(commit(MESSAGES["review in the body"]), POLICY)[0])
        self.assertIn("no 'Review:'", check_commits.review(commit("Fix\n\nBody.\n"), POLICY)[0])
        self.assertEqual(check_commits.review(commit("Merge x\n", parents=("a", "b")), POLICY), [])

    def test_a_controlled_change_names_a_request_or_a_request_names_it(self):
        # REQ: SRS-GIT-005
        changed = commit(controlled=["SRS-SRT-001"])
        self.assertIn("names no change request",
                      check_commits.reference(changed, POLICY, KNOWN)[0])
        named = commit("Fix (CR-0001)\n\nReview: ok\n", controlled=["SRS-SRT-001"])
        self.assertEqual(check_commits.reference(named, POLICY, KNOWN), [])
        report = commit("Fix (MDQ-PR-007)\n\nReview: ok\n", controlled=["SRS-SRT-001"])
        self.assertEqual(check_commits.reference(report, POLICY, KNOWN), [])
        unknown = commit("Fix (CR-0099)\n\nReview: ok\n", controlled=["SRS-SRT-001"])
        self.assertIn("CR-0099", check_commits.reference(unknown, POLICY, KNOWN)[0])
        listed = dict(changed, sha="abcdef1234")
        self.assertEqual(check_commits.reference(listed, POLICY, KNOWN), [])
        self.assertEqual(check_commits.reference(commit(), POLICY, KNOWN), [])

    def test_merges(self):
        # REQ: SRS-GIT-003
        self.assertEqual(check_commits.merge(commit("Merge PR 1\n", parents="ab"), POLICY), [])
        self.assertTrue(check_commits.merge(commit("Sorter\n", parents="ab"), POLICY))
        self.assertTrue(check_commits.merge(commit("Merge x\n", parents="abc"), POLICY))


SRS = """| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-SRT-001 | The sorter shall pair singles. | sorter | T |

| ID | Method | Evidence |
|---|---|---|
| SRS-SRT-001 | T | Test A. |
"""

GOOD = "Sorter: {}\n\nBody.\n\nReview: change control checklist, items 1 to 6.\n"


class Repository:
    def __init__(self, email="t@example.invalid"):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL=email,
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL=email,
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q", "-b", "main")
        self.write("docs/regulatory/srs.md", SRS)
        self.write("docs/regulatory/changes/CR-0001-sorter.md", "| Commits | none yet |\n")
        self.write("docs/regulatory/problem-reports.json", "[]")
        self.policy = dict(POLICY, since=None)
        self.commit(GOOD.format("start"))
        self.since = self.head()

    def git(self, *args, env=None):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              env=env or self.env, capture_output=True, text=True).stdout

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, message, env=None):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message, env=env)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def run(self, *args):
        policy = dict(self.policy, since=self.since)
        path = pathlib.Path(self._tmp.name) / "policy.json"
        path.write_text(json.dumps(policy))
        return subprocess.run([sys.executable, check_commits.__file__, str(self.root), *args,
                               "--policy", str(path)], capture_output=True, text=True)

    def close(self):
        self._tmp.cleanup()


class Range(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def tearDown(self):
        self.repo.close()

    def test_a_good_history_passes_and_starts_after_since(self):
        # REQ: SRS-GIT-006
        self.repo.commit(GOOD.format("pairs"))
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("1 commits, 0 problem(s)", r.stdout)

    def test_a_requirement_changed_without_a_request_fails_its_verification_does_not(self):
        # REQ: SRS-GIT-005
        self.repo.write("docs/regulatory/srs.md", SRS.replace("Test A.", "Test B."))
        self.repo.commit(GOOD.format("evidence"))
        self.assertEqual(self.repo.run().returncode, 0)
        self.repo.write("docs/regulatory/srs.md", SRS.replace("pair singles", "pair hits"))
        sha = self.repo.commit(GOOD.format("pairs hits"))
        r = self.repo.run()
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{sha[:12]} reference: changes SRS-SRT-001", r.stdout)
        self.repo.write("docs/regulatory/changes/CR-0001-sorter.md", f"| Commits | {sha[:7]} |\n")
        self.repo.commit(GOOD.format("CR-0001 implemented"))
        r = self.repo.run()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_an_accepted_exception_names_its_commit_and_its_rule(self):
        # REQ: SRS-GIT-006
        sha = self.repo.commit("Sorter: pairs\n\nBody.\n")
        self.assertEqual(self.repo.run().returncode, 1)
        self.repo.policy["accepted"] = [{"commit": sha[:10], "rule": "layout", "reason": "x"}]
        self.assertEqual(self.repo.run().returncode, 1)  # another rule is still broken
        self.repo.policy["accepted"] = [{"commit": sha[:10], "rule": "review", "reason": "x"}]
        self.assertEqual(self.repo.run().returncode, 0)
        r = self.repo.run("--all-rules")  # the measurement counts it anyway
        self.assertIn("review 1", r.stdout)

    def test_a_merge_made_with_a_personal_address_fails(self):
        # REQ: SRS-GIT-002
        self.repo.git("checkout", "-q", "-b", "topic")
        self.repo.commit(GOOD.format("topic"))
        self.repo.git("checkout", "-q", "main")
        web = dict(self.repo.env, GIT_COMMITTER_EMAIL=PERSONAL, GIT_AUTHOR_EMAIL=PERSONAL)
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge topic", "topic", env=web)
        r = self.repo.run()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.count("identity"), 2)
        self.assertNotIn("someone@", r.stdout)

    def test_a_range_git_cannot_resolve_is_a_usage_error(self):
        # REQ: SRS-GIT-006
        r = self.repo.run("0" * 40 + "..HEAD")
        self.assertEqual(r.returncode, 2)
        self.assertIn("fetch-depth 0", r.stderr)
        shallow = pathlib.Path(self.repo._tmp.name) / "shallow"
        self.repo.commit(GOOD.format("one"))
        self.repo.commit(GOOD.format("two"))
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{self.repo.root}",
                        str(shallow)], check=True, capture_output=True)
        self.repo.root, root = shallow, self.repo.root
        try:
            self.assertEqual(self.repo.run().returncode, 2)
        finally:
            self.repo.root = root


class Hook(unittest.TestCase):
    def test_the_commit_msg_hook_checks_the_message_and_the_identity(self):
        # REQ: SRS-GIT-007
        hook = pathlib.Path(check_commits.__file__).parent / "hooks" / "commit-msg"
        repo = Repository()
        try:
            def run(message, email="t@example.invalid"):
                path = repo.root / ".git" / "COMMIT_EDITMSG"
                path.write_text(message)
                env = dict(repo.env, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_EMAIL=email)
                return subprocess.run([sys.executable, str(hook), str(path)], cwd=repo.root,
                                      env=env, capture_output=True, text=True)
            comments = "\n# Please enter the commit message.\n# On branch main\n"
            self.assertEqual(run(GOOD.format("pairs") + comments).returncode, 0)
            r = run("Sorter: pairs.\nBody.\n")
            self.assertEqual(r.returncode, 1)
            for rule in ("subject:", "layout:", "review:"):
                self.assertIn(rule, r.stderr)
            r = run(GOOD.format("pairs"), email=PERSONAL)
            self.assertEqual(r.returncode, 1)
            self.assertIn("identity:", r.stderr)
        finally:
            repo.close()


class OnThisRepository(unittest.TestCase):
    def test_the_policy_holds_from_since(self):
        # REQ: SRS-GIT-006
        root = pathlib.Path(__file__).resolve().parent.parent
        if not (root / ".git").exists() or subprocess.run(
                ["git", "-C", str(root), "cat-file", "-e", POLICY["since"] + "^{commit}"],
                capture_output=True).returncode != 0:
            self.skipTest("not a whole clone of the repository")
        if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
            self.skipTest("a pull request's checkout is GitHub's merge; CI checks the branch")
        r = subprocess.run([sys.executable, check_commits.__file__, str(root)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
