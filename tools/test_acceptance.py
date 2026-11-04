#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/acceptance.py (Chapter 33), run by CTest as tools.acceptance.

A synthetic OUT directory of the release checks, built from snippets of real evidence, gives every
verdict: PASS when the evidence meets the target, FAIL when it does not, MISSING when the file is
absent or unreadable (never a pass), STALE when a part ran on another commit or on a tree with
changes. The repository criterion is not evaluated here (it runs the document checks).
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import acceptance  # noqa: E402

COMMIT = "cfb708fb44b22b8e9648f2ad211600c96ae55490"
OTHER = "1572784aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SPEC = json.loads(acceptance.SPEC.read_text())
CRITERIA = {c["id"]: c for c in SPEC["criteria"]}

PIPELINE = ("# 2026-11-04T03:17:32Z commit cfb708f hardened bm_pipeline\n"
            "BM_Pipeline/4096/64/real_time_mean    227 ms   7.20 ms   5 items_per_second=36.9978M/s\n"
            "BM_Pipeline/4096/64/real_time_median  224 ms   7.24 ms   5 items_per_second={}M/s\n")
WRITER = "".join(f"writer fsync=close ...: 200003584 coincidences, 3201.6 MB in 16.654 s "
                 f"(close 0.976 s): {r} M/s, 192 MB/s; files 3\n" for r in ("12.01", "15.50", "{}"))
SOAK = ("soak: 1e+06 singles/s for {} min, 181 samples every 10 s\n"
        "singles in: 1800030235 (1000017/s); losses 0; fault None; complete True\n"
        "end-to-end latency over each interval: p99 max {} ms, max 12.91 ms\n"
        "result: {}\n")
REPORT = "## 2. Results\n\n34 test cases: {} passed, {} failed, 0 skipped.\n"
CHECKS = "".join(f"## part {n}\npass  something\nall release checks passed (part {n})\n"
                 for n in (1, 2, 3, 4))


def e2e_result(commit="cfb708f", same=True, radius=80.25):
    def acq(name, image):
        checks = [{"name": "link: delivered or lost", "ok": True},
                  {"name": "reference: the server wrote the reference's records", "ok": same}]
        a = {"name": name, "checks": checks}
        if image:
            checks.append({"name": "image: the cylinder's radius at half its level",
                           "ok": abs(radius - 80) <= 2})
            a["image"] = {"radius_at_half_mm": radius, "center_over_periphery": 1.04}
        return a
    return json.dumps({"format": "MiniDAQ end-to-end result", "commit": commit,
                       "acquisitions": [acq("qc", False), acq("phantom", True)]})


class Evidence:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = pathlib.Path(self._tmp.name)
        for name, part in (("commit.txt", 1), ("commit-part-2.txt", 2), ("commit-part-3.txt", 3),
                           ("commit-part-4.txt", 4)):
            self.write(name, f"commit {COMMIT}\n")
        self.write("perf-pipeline.txt", PIPELINE.format("37.4753"))
        self.write("perf-writer.txt", WRITER.format("15.77"))
        self.write("soak.txt", SOAK.format("30.0", "4.42", "PASS"))
        self.write("system-test-report.md", REPORT.format(34, 0))
        self.write("release-checks.txt", CHECKS)
        (self.out / "e2e").mkdir()
        self.write("e2e/e2e.json", e2e_result())

    def write(self, name, text):
        (self.out / name).write_text(text)

    def verdict(self, cid, candidate=COMMIT):
        return acceptance.evaluate(CRITERIA[cid], self.out, candidate)[0]

    def close(self):
        self._tmp.cleanup()


class Verdicts(unittest.TestCase):
    def setUp(self):
        self.ev = Evidence()

    def tearDown(self):
        self.ev.close()

    def test_evidence_that_meets_every_target_passes(self):
        for cid in CRITERIA:
            if CRITERIA[cid]["rule"] != "repository":
                with self.subTest(cid):
                    self.assertEqual(self.ev.verdict(cid), "PASS")

    def test_evidence_below_its_target_fails(self):
        self.ev.write("perf-pipeline.txt", PIPELINE.format("19.9"))
        self.assertEqual(self.ev.verdict("ACC-01"), "FAIL")
        self.ev.write("perf-writer.txt", WRITER.format("2.99"))
        self.assertEqual(self.ev.verdict("ACC-02"), "FAIL")
        self.ev.write("soak.txt", SOAK.format("29.5", "10.01", "PASS"))
        self.assertEqual(self.ev.verdict("ACC-03"), "FAIL", "a soak shorter than 30 minutes")
        self.assertEqual(self.ev.verdict("ACC-04"), "FAIL")
        self.ev.write("system-test-report.md", REPORT.format(33, 1))
        self.assertEqual(self.ev.verdict("ACC-07"), "FAIL")
        self.ev.write("e2e/e2e.json", e2e_result(same=False, radius=83.0))
        self.assertEqual(self.ev.verdict("ACC-05"), "FAIL")
        self.assertEqual(self.ev.verdict("ACC-06"), "FAIL")
        self.ev.write("release-checks.txt", CHECKS.replace("all release checks passed (part 4)", ""))
        self.assertEqual(self.ev.verdict("ACC-08"), "FAIL", "a part that did not end")

    def test_a_part_run_again_counts_by_its_last_section(self):
        failed_first = "## part 3\nFAIL  soak, 30 minutes at 1 M singles/s\n1 release checks failed (part 3)\n"
        self.ev.write("release-checks.txt", CHECKS.replace("## part 3", failed_first + "## part 3"))
        self.assertEqual(self.ev.verdict("ACC-08"), "PASS")
        self.ev.write("release-checks.txt", CHECKS + failed_first)
        self.assertEqual(self.ev.verdict("ACC-08"), "FAIL")
        self.ev.write("release-checks.txt", "## part all\npass  x\nall release checks passed (part all)\n")
        self.assertEqual(self.ev.verdict("ACC-08"), "PASS", "one run of all four parts")

    def test_a_soak_that_failed_fails_whatever_its_length(self):
        self.ev.write("soak.txt", SOAK.format("30.0", "4.42", "FAIL: 3 singles lost"))
        self.assertEqual(self.ev.verdict("ACC-03"), "FAIL")

    def test_missing_or_unreadable_evidence_is_never_a_pass(self):
        (self.ev.out / "perf-pipeline.txt").unlink()
        self.assertEqual(self.ev.verdict("ACC-01"), "MISSING")
        self.ev.write("perf-writer.txt", WRITER.format("15.0").splitlines()[0] + "\n")
        self.assertEqual(self.ev.verdict("ACC-02"), "MISSING", "one run of three")
        self.ev.write("soak.txt", "the soak was not run\n")
        self.assertEqual(self.ev.verdict("ACC-03"), "MISSING")
        self.ev.write("e2e/e2e.json", "{not json")
        self.assertEqual(self.ev.verdict("ACC-05"), "MISSING")
        self.ev.write("e2e/e2e.json", json.dumps({"format": "something else"}))
        self.assertEqual(self.ev.verdict("ACC-06"), "MISSING")
        (self.ev.out / "commit-part-2.txt").unlink()
        self.ev.write("perf-pipeline.txt", PIPELINE.format("37.4"))
        self.assertEqual(self.ev.verdict("ACC-01"), "MISSING", "no commit for part 2")

    def test_evidence_of_another_commit_or_a_changed_tree_is_stale(self):
        self.ev.write("commit-part-3.txt", f"commit {OTHER}\n")
        self.assertEqual(self.ev.verdict("ACC-03"), "STALE")
        self.ev.write("commit-part-2.txt", f"commit {COMMIT}\n M tools/e2e.py\n")
        self.assertEqual(self.ev.verdict("ACC-01"), "STALE")
        self.ev.write("e2e/e2e.json", e2e_result(commit="cfb708f-dirty"))
        self.ev.write("commit-part-3.txt", f"commit {COMMIT}\n")
        self.assertEqual(self.ev.verdict("ACC-05"), "STALE")
        self.ev.write("e2e/e2e.json", e2e_result(commit="1572784"))
        self.assertEqual(self.ev.verdict("ACC-06"), "STALE")
        self.assertEqual(self.ev.verdict("ACC-02", candidate=OTHER), "STALE")

    def test_a_commit_prefix_too_short_to_name_a_commit_matches_nothing(self):
        self.assertEqual(self.ev.verdict("ACC-01", candidate=COMMIT[:7]), "PASS")
        self.assertEqual(self.ev.verdict("ACC-05", candidate=COMMIT[:7]), "PASS")
        self.assertEqual(self.ev.verdict("ACC-01", candidate=COMMIT[:2]), "STALE")
        self.assertEqual(self.ev.verdict("ACC-05", candidate=COMMIT[:2]), "STALE")
        self.ev.write("e2e/e2e.json", e2e_result(commit="cf"))
        self.assertEqual(self.ev.verdict("ACC-05"), "STALE")
        self.assertEqual(acceptance.main([str(self.ev.out), "--commit", "cfb"]), 2)

    def test_the_report_accepts_only_when_every_criterion_passes(self):
        rows = [(c, "PASS", "x") for c in SPEC["criteria"]]
        self.assertTrue(acceptance.report(SPEC, rows, COMMIT, self.ev.out)[0])
        for verdict in ("FAIL", "MISSING", "STALE"):
            rows[-1] = (rows[-1][0], verdict, "x")
            accepted, text = acceptance.report(SPEC, rows, COMMIT, self.ev.out)
            self.assertFalse(accepted, verdict)
            self.assertIn("NOT ACCEPTED", text)

    def test_every_criterion_names_a_known_rule_and_existing_requirements(self):
        srs = (acceptance.ROOT / "docs/regulatory/srs.md").read_text()
        for c in SPEC["criteria"]:
            with self.subTest(c["id"]):
                self.assertIn(c["rule"], {*acceptance.RULES, "repository"})
                for r in c["requirements"]:
                    self.assertIn(f"| {r} |", srs)


if __name__ == "__main__":
    unittest.main()
