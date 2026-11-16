#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Trends of MiniDAQ's problem reports, release by release (Chapter 40).

A problem report says how it was found; git says which commit recorded it, and so which release
first contained the record, and how many commits each release took. This tool puts each report
in the development window of the first release whose tag contains the commit that added it (or
"unreleased"), and gives per window:
the commits, the reports, the reports per 100 commits with a u-chart's upper control limit, how
the reports were found, the root causes' categories, and the reports whose defect reached a
release ("affects", from MDQ-PR-065 on). It is the data analysis that the maintenance plan asks
for at every minor release (docs/regulatory/maintenance-plan.md, section 6).

Usage: pr_trends.py ROOT. Writes the report to standard output.
"""
import json
import math
import pathlib
import re
import subprocess
import sys

REPORTS = pathlib.Path("docs/regulatory/problem-reports.json")
CHANGELOG = pathlib.Path("CHANGELOG.md")
RELEASE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})", re.M)

# [snippet:found-by]
# How a problem was found, from the report's "found" text: the first rule that matches wins, so
# a review held for a release counts as the release's checks, not as a review.
FOUND_BY = (
    ("release checks", re.compile(r"release checks|coverage review|SOUP review for release|"
                                  r"threat model review|review of the controlled documents|"
                                  r"CAPA-0001 check of release", re.I)),
    ("review or audit", re.compile(r"\breview\b|\baudit\b", re.I)),
    ("CI", re.compile(r"\bCI\b|GitHub|fuzz-smoke", re.I)),
    ("tests", re.compile(r"test|ctest|fuzz_|gate self-test", re.I)),
    ("measurement", re.compile(r"measurement|end-to-end run|recordings", re.I)),
)
OTHER = "development"
# [/snippet:found-by]


def found_by(text):
    """The way a report was found, one of FOUND_BY's names or OTHER."""
    return next((name for name, rule in FOUND_BY if rule.search(text)), OTHER)


def releases(changelog_text):
    """[(version, date)], oldest first."""
    out = [(v, d) for v, d in RELEASE.findall(changelog_text)]
    return sorted(out, key=lambda r: (r[1], tuple(int(x) for x in r[0].split("."))))


def recorded_in(root, released):
    """{report id: the first release whose tag contains the commit that added the report}, or
    "unreleased"; from the history of the reports file. Dates cannot do this: several releases
    were made on one day, and a report found by the release checks of 1.3.0 was recorded before
    the release on the day that 1.2.0 was also released."""
    log = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--format=%H", "--",
                          str(REPORTS)], capture_output=True, text=True, check=True).stdout.split()
    added, seen = {}, set()
    for commit in log:
        show = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{REPORTS}"],
                              capture_output=True, text=True, check=False)
        if show.returncode != 0:
            continue
        for rid in re.findall(r'"id": "(MDQ-PR-\d{3})"', show.stdout):
            if rid not in seen:
                seen.add(rid)
                added[rid] = commit
    tags = {}
    for v, _ in released:
        out = subprocess.run(["git", "-C", str(root), "rev-list", f"book-v{v}"],
                             capture_output=True, text=True, check=False).stdout
        tags[v] = set(out.split())
    return {rid: next((v for v, _ in released if c in tags[v]), "unreleased")
            for rid, c in added.items()}


def commits(root, released):
    """{version: commits since the previous release's tag}, "unreleased" up to HEAD; None for a
    window whose tags are missing (a shallow clone)."""
    out = {}
    previous = None
    for v in [r[0] for r in released] + ["unreleased"]:
        end = "HEAD" if v == "unreleased" else f"book-v{v}"
        span = end if previous is None else f"{previous}..{end}"
        run = subprocess.run(["git", "-C", str(root), "rev-list", "--count", span],
                             capture_output=True, text=True, check=False)
        out[v] = int(run.stdout) if run.returncode == 0 else None
        previous = end
    return out


# [snippet:u-chart]
def u_chart(counts, exposure):
    """The u-chart of reports per unit of exposure: (u-bar, {window: (u, upper limit)}), with
    the limit u-bar + 3 sqrt(u-bar / n) for a window of exposure n. A window above its limit has
    more reports than its size explains, which is a signal to look for a cause (and the reason
    for a CAPA, or not); one below says nothing, since fewer checks also find fewer problems."""
    windows = [w for w in counts if exposure.get(w)]
    total = sum(exposure[w] for w in windows)
    ubar = sum(counts[w] for w in windows) / total if total else 0.0
    return ubar, {w: (counts[w] / exposure[w], ubar + 3.0 * math.sqrt(ubar / exposure[w]))
                  for w in windows}
# [/snippet:u-chart]


def analyse(reports, released, exposure, window):
    """window: {report id: release} (recorded_in)."""
    order = [v for v, _ in released] + ["unreleased"]
    rows = {v: {"reports": [], "found_by": {}, "category": {}, "escaped": 0} for v in order}
    for r in reports:
        row = rows[window.get(r["id"], "unreleased")]
        row["reports"].append(r["id"])
        how = found_by(r["found"])
        row["found_by"][how] = row["found_by"].get(how, 0) + 1
        cat = (r.get("root_cause") or {}).get("category")
        if cat:
            row["category"][cat] = row["category"].get(cat, 0) + 1
        if r.get("affects"):
            row["escaped"] += 1
    counts = {v: len(rows[v]["reports"]) for v in order}
    ubar, chart = u_chart(counts, exposure)
    return order, rows, ubar, chart


def render(order, rows, ubar, chart, exposure):
    hows = [name for name, _ in FOUND_BY] + [OTHER]
    lines = ["# Problem report trends", "",
             "Generated by `tools/pr_trends.py`. A report counts in the first release whose tag "
             "contains the commit that recorded it.", "",
             f"Mean rate: {100 * ubar:.1f} reports per 100 commits.", "",
             "| Window | Commits | Reports | Per 100 commits | Upper limit | Signal |",
             "|---|---:|---:|---:|---:|---|"]
    for v in order:
        n = len(rows[v]["reports"])
        if v in chart:
            u, ucl = chart[v]
            lines.append(f"| {v} | {exposure[v]} | {n} | {100 * u:.1f} | {100 * ucl:.1f} | "
                         f"{'above' if u > ucl else ''} |")
        else:
            lines.append(f"| {v} | ? | {n} | | | |")
    lines += ["", "How the reports were found:", "",
              "| Window | " + " | ".join(hows) + " |",
              "|---|" + "---:|" * len(hows)]
    for v in order:
        fb = rows[v]["found_by"]
        lines.append(f"| {v} | " + " | ".join(str(fb.get(h, "")) for h in hows) + " |")
    total = {h: sum(rows[v]["found_by"].get(h, 0) for v in order) for h in hows}
    lines.append("| all | " + " | ".join(str(total[h]) for h in hows) + " |")
    cats = sorted({c for v in order for c in rows[v]["category"]})
    lines += ["", "Root cause categories (reports with a root cause analysis, MDQ-PR-019 on):", "",
              "| Window | " + " | ".join(cats) + " |", "|---|" + "---:|" * len(cats)]
    for v in order:
        cc = rows[v]["category"]
        if cc:
            lines.append(f"| {v} | " + " | ".join(str(cc.get(c, "")) for c in cats) + " |")
    lines.append("| all | " + " | ".join(
        str(sum(rows[v]["category"].get(c, 0) for v in order)) for c in cats) + " |")
    escaped = [(v, rows[v]["escaped"]) for v in order if rows[v]["escaped"]]
    lines += ["", "Reports whose defect reached a release (recorded from MDQ-PR-065 on): " +
              (", ".join(f"{n} recorded for {v}" for v, n in escaped) or "none") + "."]
    return "\n".join(lines) + "\n"


def main(argv):
    root = pathlib.Path(argv[1] if len(argv) > 1 else ".").resolve()
    reports = json.loads((root / REPORTS).read_text())["reports"]
    released = releases((root / CHANGELOG).read_text())
    exposure = commits(root, released)
    window = recorded_in(root, released)
    sys.stdout.write(render(*analyse(reports, released, exposure, window), exposure))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
