#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of tools/soak_ab.py (CR-0038): the comparison of two releases' soaks, judged on the
soaks recorded for MDQ-PR-064 and MDQ-PR-096, the pooled memory trend, and the blocks' order
and resume with a stand-in for tools/soak.py."""
import contextlib
import csv
import fractions
import io
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import acceptance  # noqa: E402
import soak_ab  # noqa: E402

RECORDED = ROOT / "measurements"
ACC04 = {"limit": 10.0, "share": 0.99}


def exact_p(k1, n1, k2, n2):
    """Fisher's one-sided p by enumerating every table with the same margins, in fractions."""
    good, total = k1 + k2, n1 + n2
    tables = {k: fractions.Fraction(math.comb(good, k) * math.comb(total - good, n1 - k))
              for k in range(max(0, n1 - (total - good)), min(good, n1) + 1)}
    return float(sum(v for k, v in tables.items() if k >= k1) / sum(tables.values()))


def split(samples, out, side, blocks):
    """Writes a recorded 100-minute soak as BLOCKS blocks of OUT/side-N, as tools/soak.py writes
    a block: its samples from t = 0 and a summary."""
    with open(samples, newline="") as f:
        rows = list(csv.DictReader(f))
    size = len(rows) // blocks
    for i in range(blocks):
        part = rows[i * size:(i + 1) * size]
        t0 = float(part[0]["t_s"])
        d = out / f"{side}-{i + 1}"
        d.mkdir(parents=True)
        with (d / "samples.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(part[0]))
            w.writeheader()
            w.writerows(dict(r, t_s=f"{float(r['t_s']) - t0:.1f}") for r in part)
        minutes = len(part) * 10 / 60
        (d / "summary.txt").write_text(f"soak: 1e+06 singles/s for {minutes:.1f} min\nresult: PASS\n")
    return rows


def slow(rows, limit=10.0):
    return sum(float(r["p99_ms"]) > limit for r in rows)


class Fisher(unittest.TestCase):
    def test_the_one_sided_p_is_that_of_the_enumerated_tables(self):

        # REQ: SRS-PERF-022
        for case in [(8, 600, 6, 600), (11, 600, 6, 600), (19, 1200, 6, 600), (0, 600, 0, 600),
                     (20, 600, 3, 600), (3, 600, 20, 600), (2, 600, 0, 600)]:
            self.assertAlmostEqual(soak_ab.fisher_greater(*case), exact_p(*case), places=12, msg=case)

    def test_a_clearly_worse_candidate_fails_and_a_better_one_passes(self):

        # REQ: SRS-PERF-022
        ok, text = soak_ab.compare((3, 600), (20, 600))
        self.assertFalse(ok, text)
        self.assertIn("result: FAIL", text)
        ok, text = soak_ab.compare((20, 600), (3, 600))
        self.assertTrue(ok, text)

    def test_the_power_is_stated_and_grows_with_the_effect(self):
        weak = soak_ab.power(600, 600, 0.01, ratio=2.0)
        strong = soak_ab.power(600, 600, 0.01, ratio=4.0)
        self.assertTrue(0.05 < weak < strong <= 1.0, (weak, strong))
        _, text = soak_ab.compare((6, 600), (8, 600))
        self.assertRegex(text, r"power: \d+% to find a candidate with twice")


class Recorded(unittest.TestCase):
    """The comparison on the soaks of 2026-11-24 (MDQ-PR-096): the candidate of 2.2.0, 8 and 11
    slow intervals of 600, against book-v2.1.0's programs on the same machine, 6 of 600. ACC-04
    fails, as at the release; ACC-10 finds the candidate no worse."""

    def judged(self, head, base):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            head_rows = split(head, out, "head", 5)
            base_rows = split(base, out, "base", 5)
            with contextlib.redirect_stdout(io.StringIO()):
                code = soak_ab.merge(out, 5)
            summary = (out / "head/summary.txt").read_text()
            return code, summary, (out / "compare.txt").read_text(), head_rows, base_rows

    def test_the_rerun_of_2_2_0_fails_acc_04_but_not_acc_10(self):

        # REQ: SRS-PERF-022
        code, summary, compare, head, base = self.judged(
            RECORDED / "mdq-pr-096/rerun/samples.csv", RECORDED / "mdq-pr-096/control-2.1.0/samples.csv")
        self.assertEqual((slow(head), slow(base)), (11, 6))
        ok, found = acceptance.soak_latency(summary, ACC04)
        self.assertFalse(ok, found)
        self.assertIn("result: PASS", compare)
        self.assertIn("candidate 11 of", compare)
        self.assertIn("previous release 6 of", compare)
        ok, found = acceptance.soak(summary, {"limit": 100})
        self.assertTrue(ok, found)

    def test_a_quiet_soak_against_a_busy_one_passes_both(self):

        # REQ: SRS-PERF-022
        code, summary, compare, head, base = self.judged(
            RECORDED / "mdq-pr-064/soak-100min/samples.csv", RECORDED / "mdq-pr-096/first/samples.csv")
        self.assertEqual(slow(head), 0)
        self.assertTrue(acceptance.soak_latency(summary, ACC04)[0])
        self.assertIn("result: PASS", compare)
        self.assertEqual(code, 0)

    def test_the_busy_soak_as_candidate_against_the_quiet_one_fails_acc_10(self):

        # REQ: SRS-PERF-022
        code, summary, compare, head, base = self.judged(
            RECORDED / "mdq-pr-096/rerun/samples.csv", RECORDED / "mdq-pr-064/soak-100min/samples.csv")
        self.assertEqual((slow(head), slow(base)), (11, 0))
        self.assertIn("result: FAIL", compare)
        self.assertEqual(code, 1)


class Memory(unittest.TestCase):
    def test_the_slope_is_pooled_within_blocks_whatever_their_levels(self):

        # REQ: SRS-SYS-003
        xs = [i / 60 for i in range(30)]
        blocks = [(xs, [100 + 2 * x for x in xs]), (xs, [300 + 2 * x for x in xs]),
                  (xs, [50 + 2 * x + (0.01 if i % 2 else -0.01) for i, x in enumerate(xs)])]
        b, se, n = soak_ab.pooled_slope(blocks)
        self.assertAlmostEqual(b, 2.0, places=2)
        self.assertEqual(n, 90)
        self.assertLess(se, 0.01)

    def test_a_blocks_own_memory_verdict_is_left_to_the_pooled_trend(self):
        text = "result: FAIL: memory grows 3.000 MiB/h, more than 1.0 MiB/h; 12 singles lost\n"
        self.assertEqual(soak_ab.block_problems(text), ["12 singles lost"])
        self.assertEqual(soak_ab.block_problems("result: PASS\n"), [])
        self.assertEqual(soak_ab.block_problems("nothing\n"), ["the block has no result"])

    def test_a_leak_in_every_block_fails_the_side(self):

        # REQ: SRS-SYS-003
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            split(RECORDED / "mdq-pr-064/soak-100min/samples.csv", out, "head", 5)
            for i in range(1, 6):
                f = out / f"head-{i}/samples.csv"
                rows = list(csv.DictReader(f.open(newline="")))
                for r in rows:  # 30 MiB per hour on top of the recorded memory
                    r["rss_kib"] = str(int(float(r["rss_kib"]) + 30 * 1024 * float(r["t_s"]) / 3600))
                with f.open("w", newline="") as g:
                    w = csv.DictWriter(g, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
            ok, _, _, text = soak_ab.side_summary(out, "head", 5)
            self.assertFalse(ok)
            self.assertIn("memory grows", text)


class Blocks(unittest.TestCase):
    def test_the_sides_alternate_as_the_benchmarks_do(self):
        self.assertEqual(soak_ab.order(3), [("base", 1), ("head", 1), ("head", 2), ("base", 2),
                                            ("base", 3), ("head", 3)])

    def test_a_stopped_run_continues_at_the_block_it_was_in(self):

        # REQ: SRS-PERF-022
        with tempfile.TemporaryDirectory() as d:
            work = pathlib.Path(d)
            out, ran = work / "out", work / "ran.txt"
            recorded = RECORDED / "mdq-pr-064/soak-100min"
            split(recorded / "samples.csv", out, "base", 2)
            split(recorded / "samples.csv", out, "head", 2)
            (out / "head-2/summary.txt").unlink()  # stopped in this block
            (out / "base-2/summary.txt").unlink()  # not reached
            fake = work / "soak.py"
            fake.write_text(
                "import pathlib, shutil, sys\n"
                f"open({str(ran)!r}, 'a').write(pathlib.Path(sys.argv[2]).name + '\\n')\n"
                "d = pathlib.Path(sys.argv[2]); d.mkdir(parents=True, exist_ok=True)\n"
                f"src = pathlib.Path({str(out)!r}) / 'head-1'\n"
                "shutil.copy(src / 'samples.csv', d / 'samples.csv')\n"
                "shutil.copy(src / 'summary.txt', d / 'summary.txt')\n")
            code = subprocess.run(
                [sys.executable, "-c",
                 "import sys, pathlib; sys.path.insert(0, sys.argv[1]); import soak_ab; "
                 "soak_ab.SOAK = pathlib.Path(sys.argv[2]); "
                 "sys.exit(soak_ab.main(sys.argv[3:]))",
                 str(HERE), str(fake), "A", "B", str(out), "--blocks", "2", "--block-minutes", "1"],
                capture_output=True, text=True)
            self.assertEqual(ran.read_text(), "head-2\nbase-2\n", code.stdout + code.stderr)
            self.assertTrue((out / "compare.txt").is_file())

    def test_a_block_names_no_absolute_path_of_the_machine(self):

        # REQ: SRS-PERF-022
        # MDQ-PR-103: the release checks give the previous release's programs by an absolute path
        # under OUT; the summary is committed to a public repository.
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "summary.txt"
            apps = pathlib.Path(d) / "soak-ab/base-src/build/release/minidaq/apps"
            f.write_text(f"machine: vm, 4 CPUs; programs {apps}\nresult: PASS\n")
            soak_ab.private(f, apps, "base")
            self.assertNotIn(d, f.read_text())
            self.assertIn("programs the previous release's build", f.read_text())
            f.write_text("machine: vm, 4 CPUs; programs build/release/minidaq/apps\n")
            soak_ab.private(f, pathlib.Path("build/release/minidaq/apps"), "head")
            self.assertIn("programs build/release/minidaq/apps", f.read_text())


if __name__ == "__main__":
    unittest.main()
