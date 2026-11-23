#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/agent_gate.py: the gate rejects every change of its known-bad library for the
reason the change holds, and passes a good change (roadmap 2.2.0, Theme P1).

Each case is a patch against the library's base commit (tools/agent_gate/known-bad/cases.json).
The test checks the base out in a temporary worktree, applies one patch at a time and runs the
gate on the working tree. A case of level "full" (a defect only the tests themselves can catch)
must pass the fast checks; MINIDAQ_GATE_FULL=1 runs it with --full as well, which builds.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import agent_gate as gate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "tools/agent_gate/known-bad"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


class KnownBadLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((LIBRARY / "cases.json").read_text())
        if git(ROOT, "cat-file", "-e", cls.spec["base"] + "^{commit}").returncode != 0:
            raise unittest.SkipTest("the library's base commit is not in this clone (shallow?)")
        cls.tmp = tempfile.mkdtemp(prefix="agent-gate-")
        cls.wt = pathlib.Path(cls.tmp) / "wt"
        r = git(ROOT, "worktree", "add", "--detach", str(cls.wt), cls.spec["base"])
        if r.returncode != 0:
            raise unittest.SkipTest(f"no worktree: {r.stderr.strip()}")
        cls.has_format = shutil.which("clang-format") is not None

    @classmethod
    def tearDownClass(cls):
        git(ROOT, "worktree", "remove", "--force", str(cls.wt))
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def judged(self, case, full=False):
        patch = LIBRARY / f"{case['id']}.patch"
        r = git(self.wt, "apply", str(patch))
        self.assertEqual(r.returncode, 0, f"{patch.name} does not apply: {r.stderr}")
        try:
            _, results, verdict = gate.judge(self.wt, self.spec["base"], full=full,
                                             build=self.wt / "build/debug")
        finally:
            git(self.wt, "checkout", "-q", ".")
            git(self.wt, "clean", "-qfd")
        return {name: result for name, result, _ in results}, verdict

    def test_the_library_has_ten_known_bad_changes_or_more(self):
        bad = [c for c in self.spec["cases"] if c["check"]]
        self.assertGreaterEqual(len(bad), 10)
        for c in bad:
            self.assertTrue(c["source"] and c["defect"], c["id"])

    def test_every_fast_known_bad_change_fails_its_own_check(self):
        for case in self.spec["cases"]:
            if not case["check"] or case["level"] != "fast":
                continue
            with self.subTest(case=case["id"]):
                if case["check"] == "format" and not self.has_format:
                    self.skipTest("clang-format is not installed")
                results, verdict = self.judged(case)
                self.assertEqual(verdict, "FAIL")
                self.assertEqual(results[case["check"]], "FAIL", results)

    def test_a_full_level_change_passes_the_fast_checks_and_only_the_tests_catch_it(self):
        for case in self.spec["cases"]:
            if case["level"] != "full":
                continue
            with self.subTest(case=case["id"]):
                results, verdict = self.judged(case)
                self.assertEqual(verdict, "PASS", results)
                if os.environ.get("MINIDAQ_GATE_FULL") == "1":
                    build = self.wt / "build/debug"
                    subprocess.run(["cmake", "--preset", "debug"], cwd=self.wt, capture_output=True)
                    git(self.wt, "apply", str(LIBRARY / f"{case['id']}.patch"))
                    try:
                        _, full, verdict = gate.judge(self.wt, self.spec["base"], full=True, build=build)
                    finally:
                        git(self.wt, "checkout", "-q", ".")
                    self.assertEqual(dict((n, r) for n, r, _ in full)[case["check"]], "FAIL")

    def test_the_good_change_passes(self):
        for case in self.spec["cases"]:
            if case["check"] is None:
                results, verdict = self.judged(case)
                failed = {n: r for n, r in results.items() if r == "FAIL"}
                self.assertEqual(verdict, "PASS", failed)


class Rules(unittest.TestCase):
    def test_a_compiled_anchored_pattern_used_with_match_is_found(self):
        anchored = {m.group(1) for line in ['SYNTAX = re.compile(r"^[0-9]+$")']
                    if (m := gate.COMPILED_NAME.match(line))}
        self.assertEqual(anchored, {"SYNTAX"})
        self.assertTrue(gate.ANCHORED.search('ok = re.match(r"^[0-9]+$", v)'))
        self.assertFalse(gate.ANCHORED.search('ok = re.fullmatch(r"[0-9]+", v)'))

    def test_a_change_to_a_check_is_for_a_person(self):
        self.assertTrue(gate.check_gate(files=["tools/trace_matrix.py"]))
        self.assertFalse(gate.check_gate(files=["tools/survey.py"]))


if __name__ == "__main__":
    unittest.main()
