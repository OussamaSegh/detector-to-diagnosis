#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The soak of two releases' programs, interleaved on one machine (CR-0038, MDQ-PR-096).

A soak of the candidate alone cannot tell a slow spell of the machine from a slower program: on
2026-11-24 book-v2.1.0's programs had twice as many slow intervals as at their own release
(`measurements/mdq-pr-096/`). Here the previous release (A) and the candidate (B) soak in
blocks, in the order A B, B A, A B, ... as tools/perf_ab.sh runs the benchmarks, so a slow spell
of the host falls on both. Each block is one run of tools/soak.py; a block that has its
summary is kept, so a run stopped by a time limit continues at the block it was in.

    tools/soak_ab.py BASE_APPS HEAD_APPS OUT [--blocks 5] [--block-minutes 20] [--rate 1e6]
    tools/soak_ab.py --merge OUT [--blocks 5]       (judge the blocks already in OUT)

Writes OUT/{base,head}-N/ (each block's samples.csv and summary.txt), OUT/head/summary.txt and
OUT/base/summary.txt (each side's blocks as one soak, in tools/soak.py's format, which
tools/acceptance.py reads for ACC-03 and ACC-04), and OUT/compare.txt (ACC-10). Two verdicts,
kept apart:

- ACC-04, absolute: the candidate's share of slow intervals against SRS-PERF-022's 1%.
- ACC-10, relative: whether the candidate has more slow intervals than the previous release on
  the same machine, by Fisher's exact test, one-sided, alpha 0.05. Passing it does not meet
  SRS-PERF-022; it says whether a failure of ACC-04 is in the code or in the machine.

The memory trend of a side is the slope pooled within its blocks (each block its own
intercept), after each block's warm-up: a server restarted every block still shows a leak.
Exit status 0 if the candidate's soak and the comparison both pass, 1 if not, 2 on wrong usage.
"""
import argparse
import csv
import math
import pathlib
import re
import shutil
import subprocess
import sys

SOAK = pathlib.Path(__file__).resolve().parent / "soak.py"
SIDES = ("base", "head")


def order(blocks):
    """The (side, block) pairs in the order they run: A B, B A, A B, ..."""
    out = []
    for i in range(1, blocks + 1):
        pair = SIDES if i % 2 else SIDES[::-1]
        out += [(side, i) for side in pair]
    return out


# [snippet:fisher]
def hypergeom(k, total, good, drawn):
    return math.comb(good, k) * math.comb(total - good, drawn - k) / math.comb(total, drawn)


def fisher_greater(k1, n1, k2, n2):
    """One-sided p of Fisher's exact test that the first rate (k1 of n1) is higher than the
    second (k2 of n2): the chance, with the margins fixed, of k1 or more in the first row."""
    total, good = n1 + n2, k1 + k2
    return min(1.0, sum(hypergeom(k, total, good, n1) for k in range(k1, min(good, n1) + 1)))
# [/snippet:fisher]


def binom(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def power(n1, n2, rate, ratio=2.0, alpha=0.05):
    """The chance that the test finds a candidate whose rate is `ratio` times the previous
    release's `rate`: the sum over the outcomes the test rejects. Outcomes past 12 standard
    deviations are left out; they weigh less than 1e-12."""
    p1, p2 = min(1.0, rate * ratio), rate

    def span(n, p):
        sd = math.sqrt(n * p * (1 - p))
        return range(max(0, int(n * p - 12 * sd) - 1), min(n, int(n * p + 12 * sd) + 2) + 1)

    # For a given count of the previous release, p falls as the candidate's count rises: the
    # test rejects every count from the first one it rejects.
    rejected = 0.0
    for b in span(n2, p2):
        first = next((a for a in span(n1, p1) if fisher_greater(a, n1, b, n2) < alpha), None)
        if first is not None:
            rejected += binom(b, n2, p2) * sum(binom(a, n1, p1) for a in span(n1, p1) if a >= first)
    return rejected


def read_rows(path):
    with open(path, newline="") as f:
        return [{k: (v if k in ("state", "fault", "runq_wait_thread") else float(v))
                 for k, v in r.items()} for r in csv.DictReader(f)]


def pooled_slope(blocks):
    """The least-squares slope common to several series, each with its own intercept, and its
    standard error: (slope, standard error, samples). blocks is a list of (xs, ys)."""
    sxx = sxy = 0.0
    n = 0
    for xs, ys in blocks:
        if len(xs) < 2:
            continue
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx += sum((x - mx) ** 2 for x in xs)
        sxy += sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        n += len(xs)
    used = [(xs, ys) for xs, ys in blocks if len(xs) >= 2]
    if sxx == 0 or n - len(used) - 1 < 1:
        return None
    b = sxy / sxx
    residual = 0.0
    for xs, ys in used:
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        residual += sum((y - my - b * (x - mx)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(residual / (n - len(used) - 1) / sxx)
    return b, se, n


def block_problems(summary):
    """The problems a block's own summary names, except its memory trend, which is judged over
    the side's blocks together."""
    m = next((m for line in summary.splitlines()
              if (m := re.fullmatch(r"result: (PASS|FAIL: (.*))", line))), None)
    if not m:
        return ["the block has no result"]
    if m.group(1) == "PASS":
        return []
    return [p for p in m.group(2).split("; ") if not p.startswith("memory grows")]


def side_summary(out, side, blocks, limit=10.0, interval=10.0, warmup=10.0, max_growth=1.0):
    """(passed, slow, intervals, text): one side's blocks as one soak, in tools/soak.py's format."""
    rows, problems, trend, rate, minutes = [], [], [], None, 0.0
    for i in range(1, blocks + 1):
        d = out / f"{side}-{i}"
        summary = (d / "summary.txt").read_text()
        head = re.search(r"^soak: ([\d.e+]+) singles/s for ([\d.]+) min", summary, re.M)
        if not head:
            raise ValueError(f"{d.name}/summary.txt is not a soak summary")
        rate = float(head.group(1)) if rate is None else min(rate, float(head.group(1)))
        minutes += float(head.group(2))
        problems += [f"block {i}: {p}" for p in block_problems(summary)]
        block = read_rows(d / "samples.csv")
        rows += [dict(r, block=i) for r in block]
        after = [r for r in block if r["t_s"] >= warmup * 60]
        trend.append(([r["t_s"] / 3600 for r in after], [r["rss_kib"] / 1024 for r in after]))
    pooled = pooled_slope(trend)
    if pooled is None:
        growth = "not measured: the blocks were shorter than the warm-up"
    else:
        b, se, n = pooled
        growth = (f"{b:+.3f} MiB/h (standard error {se:.3f}) pooled within {blocks} blocks, "
                  f"{n} samples after {warmup:g} min of each")
        if b - 2 * se > max_growth:
            problems.append(f"memory grows {b:.3f} MiB/h, more than {max_growth} MiB/h")
    intervals = [r for r in rows if r["t_s"] >= interval]
    above = [r for r in intervals if r["p99_ms"] > limit]
    steal = [r["steal_pct"] for r in intervals] or [0.0]
    lines = [
        f"soak: {rate:g} singles/s for {minutes:.1f} min, {len(rows)} samples every {interval:g} s, "
        f"in {blocks} blocks interleaved with the other side's (CR-0038)",
        f"resident memory: max {max(r['rss_kib'] for r in rows) / 1024:.1f} MiB; trend {growth}",
        f"end-to-end latency over each interval: p99 max {max(r['p99_ms'] for r in rows):.2f} ms, "
        f"max {max(r['max_ms'] for r in rows):.2f} ms",
        f"intervals with p99 above {limit:g} ms: {len(above)} of {len(intervals)}"
        + (" (" + ", ".join(f"block {r['block']} at {r['t_s']:g} s" for r in above) + ")"
           if above else ""),
        f"steal time over each interval: max {max(steal):.2f}%, mean {sum(steal) / len(steal):.2f}%",
        "result: " + ("PASS" if not problems else "FAIL: " + "; ".join(problems)),
    ]
    return not problems, len(above), len(intervals), "\n".join(lines) + "\n"


def compare(base, head, alpha=0.05):
    """(passed, text) of ACC-10: base and head are (slow, intervals)."""
    (k2, n2), (k1, n1) = base, head
    p = fisher_greater(k1, n1, k2, n2)
    rate = max(k2, 1) / n2
    pw = power(n1, n2, rate)
    worse = p < alpha
    lines = [
        f"intervals with p99 above the limit: candidate {k1} of {n1} ({100.0 * k1 / n1:.2f}%), "
        f"previous release {k2} of {n2} ({100.0 * k2 / n2:.2f}%)",
        f"Fisher's exact test, one-sided (the candidate worse): p = {p:.4f}, alpha {alpha:g}",
        f"power: {100.0 * pw:.0f}% to find a candidate with twice the previous release's rate "
        f"({100.0 * rate:.2f}%)",
        "result: " + ("FAIL: the candidate has more slow intervals than the previous release "
                      "on the same machine" if worse else "PASS"),
    ]
    return not worse, "\n".join(lines) + "\n"


def merge(out, blocks):
    verdicts = {}
    for side in SIDES:
        ok, slow, n, text = side_summary(out, side, blocks)
        (out / side).mkdir(exist_ok=True)
        (out / side / "summary.txt").write_text(text)
        verdicts[side] = (ok, slow, n)
    ok, text = compare(verdicts["base"][1:], verdicts["head"][1:])
    (out / "compare.txt").write_text(text)
    print((out / "head" / "summary.txt").read_text() + text, end="")
    return 0 if ok and verdicts["head"][0] else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dirs", nargs="*", type=pathlib.Path)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--blocks", type=int, default=5)
    ap.add_argument("--block-minutes", type=float, default=20.0)
    ap.add_argument("--rate", type=float, default=1e6)
    args = ap.parse_args(argv)
    if args.merge != (len(args.dirs) == 1) or (not args.merge and len(args.dirs) != 3):
        ap.print_usage(sys.stderr)
        return 2
    out = args.dirs[-1]
    out.mkdir(parents=True, exist_ok=True)
    if not args.merge:
        apps = dict(zip(SIDES, args.dirs[:2]))
        for side, i in order(args.blocks):
            d = out / f"{side}-{i}"
            if (d / "summary.txt").is_file():
                print(f"{d.name}: done before, kept")
                continue
            shutil.rmtree(d, ignore_errors=True)  # a block that stopped runs again in full
            print(f"{d.name}: {args.block_minutes:g} min of {apps[side]}", flush=True)
            subprocess.run([sys.executable, str(SOAK), str(apps[side]), str(d), "--minutes",
                            str(args.block_minutes), "--rate", str(args.rate)],
                           stdout=subprocess.DEVNULL)
            if not (d / "summary.txt").is_file():
                print(f"{d.name}: the soak wrote no summary", file=sys.stderr)
                return 1
    return merge(out, args.blocks)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
