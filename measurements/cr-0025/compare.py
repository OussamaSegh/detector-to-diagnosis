#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CR-0025: the criteria of release 1.0.0 applied to the evidence of releases 0.7.0 to 0.9.0.

    python3 measurements/cr-0025/compare.py > measurements/cr-0025/compare.txt

Gate: each release candidate against the previous release, both run interleaved on the reference
machine the same day, the rounds pooled (as tools/perf_ab.sh pools them), judged by
tools/perf_gate.py with its default threshold (5%) and significance level (0.01). Release 0.7.0
has no interleaved run: its gate passed against the recorded baseline. Latency: the share of the
soak's 10 s intervals whose 99th percentile is at or below 10 ms, at least 99% required."""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import perf_gate  # noqa: E402

M = ROOT / "measurements"


def pooled(files):
    merged = {}
    for f in files:
        for name, s in perf_gate.load(str(f)).items():
            merged.setdefault(name, perf_gate.Samples([], s.higher_is_better, s.unit)).values += s.values
    return merged


def gate(title, base, head):
    print(f"== gate: {title}")
    bad = False
    for v in perf_gate.compare(pooled(base), pooled(head)):
        bad |= v.regressed
        print(f"  {v.name:40} speed {v.ratio:6.3f}  p {v.p_value:6.4f}  {'REGRESSION' if v.regressed else 'ok'}")
    print(f"  verdict: {'FAIL' if bad else 'pass'}\n")


r8, r9 = M / "release-0.8.0/perf-interleaved", M / "release-0.9.0/perf-interleaved"
gate("0.8.0 candidate (d262ff0) against 0.7.0, 2026-11-04, 2 rounds of 10",
     [r8 / "0.7.0-1.json", r8 / "0.7.0-2.json"], [r8 / "0.8.0-1.json", r8 / "0.8.0-2.json"])
gate("0.9.0 candidate (c8d0800) against 0.8.0, 2026-11-07, 2 rounds of 10",
     [r9 / "080-1.json", r9 / "080-2.json"], [r9 / "090-1.json", r9 / "090-2.json"])

print("== latency: intervals whose 99th percentile is at or below 10 ms (at least 99% required)")
for title, path in (("0.7.0 release soak", "release-0.7.0/soak/samples.csv"),
                    ("0.8.0 release soak", "release-0.8.0/soak/samples.csv"),
                    ("0.7.0 programs on 0.8.0's day", "release-0.8.0/soak-0.7.0/samples.csv"),
                    ("0.9.0 release soak", "release-0.9.0/soak/samples.csv")):
    rows = [r for r in csv.DictReader(open(M / path)) if float(r["t_s"]) >= 10.0]
    above = [float(r["p99_ms"]) for r in rows if float(r["p99_ms"]) > 10.0]
    within = len(rows) - len(above)
    ok = within >= 0.99 * len(rows)
    print(f"  {title:32} {within} of {len(rows)} ({100 * within / len(rows):.1f}%), highest "
          f"{max(float(r['p99_ms']) for r in rows):.2f} ms: {'pass' if ok else 'FAIL'}"
          f" (every interval: {'pass' if not above else 'FAIL'})")

print("\n== power: release 0.9.0's pooled samples made slower by a factor, against 0.8.0's")
base = pooled([r9 / "080-1.json", r9 / "080-2.json"])
for factor in (0.97, 0.93, 0.90, 0.85):
    head = pooled([r9 / "090-1.json", r9 / "090-2.json"])
    for s in head.values():
        s.values = [x * factor if s.higher_is_better else x / factor for x in s.values]
    flagged = [v.name for v in perf_gate.compare(base, head) if v.regressed]
    print(f"  slower by {100 * (1 - factor):4.1f}%: {len(flagged)} of {len(head)} flagged"
          + (f" ({', '.join(flagged)})" if flagged else ""))
