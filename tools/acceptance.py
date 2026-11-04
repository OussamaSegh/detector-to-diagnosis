#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Evaluate the MiniDAQ 1.0 acceptance specification (Chapter 33) against the evidence of one run
of the release checks.

    tools/acceptance.py OUT [--spec docs/regulatory/verification/acceptance.json] [--commit SHA]

OUT is the directory tools/release_checks.sh wrote. Every criterion of the specification gets one
verdict:

- PASS: its evidence exists, is of the candidate commit, and meets the target;
- FAIL: its evidence exists and is of the candidate commit, and does not meet the target;
- MISSING: its evidence does not exist or cannot be read. Missing evidence is never a pass;
- STALE: its evidence exists but was produced on another commit, or on a working tree with
  changes, so it says nothing about the candidate.

The candidate commit is --commit, else the commit of part 1 (OUT/commit.txt). Prints the report as
Markdown and exits 0 only if every criterion passes, 1 otherwise, 2 on wrong usage.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/regulatory/verification/acceptance.json"
SCALE = {"": 1.0, "k": 1e3, "M": 1e6, "G": 1e9}


SHORTEST = 7  # a commit prefix shorter than this names nothing (Exercise 33.2)


class Missing(Exception):
    """The evidence is not there or cannot be read."""


def same_commit(a, b):
    """True when a and b name the same commit: one is a prefix of the other, both long enough."""
    return min(len(a), len(b)) >= SHORTEST and (a.startswith(b) or b.startswith(a))


# [snippet:rules]
def pipeline_median(text, c):
    m = re.search(r"real_time_median.*items_per_second=([\d.]+)([kMG]?)/s", text)
    if not m:
        raise Missing("no median in the benchmark output")
    v = float(m.group(1)) * SCALE[m.group(2)]
    return v >= c["limit"], f"median {v / 1e6:.1f} M singles/s"


def writer_slowest(text, c):
    rates = [float(x) * 1e6 for x in re.findall(r": ([\d.]+) M/s,", text)]
    if len(rates) < 3:
        raise Missing(f"{len(rates)} writer runs, 3 expected")
    return min(rates) >= c["limit"], f"slowest {min(rates) / 1e6:.2f} M coincidences/s of {len(rates)}"


def soak(text, c):
    head = re.search(r"soak: ([\d.e+]+) singles/s for ([\d.]+) min", text)
    result = re.search(r"^result: (PASS|FAIL.*)$", text, re.M)
    if not head or not result:
        raise Missing("not a soak summary")
    rate, minutes = float(head.group(1)), float(head.group(2))
    ok = result.group(1) == "PASS" and minutes >= c["limit"] and rate >= 1e6
    return ok, f"{rate:g} singles/s for {minutes:g} min, {result.group(1)}"


def soak_latency(text, c):
    m = re.search(r"p99 max ([\d.]+) ms", text)
    if not m:
        raise Missing("no latency in the soak summary")
    v = float(m.group(1))
    return v <= c["limit"], f"p99 at most {v:g} ms"


def e2e_checks(text):
    result = json.loads(text)
    if result.get("format") != "MiniDAQ end-to-end result":
        raise Missing("not an end-to-end result")
    return result


def e2e_chain(text, c):
    result = e2e_checks(text)
    checks = [ch for a in result["acquisitions"] for ch in a["checks"]
              if not ch["name"].startswith("image:")]
    failed = [ch["name"] for ch in checks if not ch["ok"]]
    same = sum(ch["name"] == "reference: the server wrote the reference's records" and ch["ok"]
               for ch in checks)
    ok = not failed and same == len(result["acquisitions"]) == 2
    return ok, (f"{len(checks) - len(failed)} of {len(checks)} checks pass, records equal to the "
                f"reference in {same} of {len(result['acquisitions'])} acquisitions"
                + (f"; failed: {', '.join(failed)}" if failed else ""))


def e2e_image(text, c):
    result = e2e_checks(text)
    checks = [ch for a in result["acquisitions"] for ch in a["checks"]
              if ch["name"].startswith("image:")]
    if not checks:
        raise Missing("the end-to-end run made no image (--no-image)")
    image = next(a["image"] for a in result["acquisitions"] if "image" in a)
    return all(ch["ok"] for ch in checks), (f"radius {image['radius_at_half_mm']} mm, center over "
                                            f"periphery {image['center_over_periphery']}")


def system_tests(text, c):
    m = re.search(r"(\d+) test cases: (\d+) passed, (\d+) failed, (\d+) skipped", text)
    if not m:
        raise Missing("no result line in the system test report")
    total, passed, failed, skipped = map(int, m.groups())
    return total > 0 and passed == total, m.group(0)


def release_checks(text, c):
    """The last section of each part (a part run again appends a new one), or one whole run."""
    sections = {}
    for block in re.split(r"^## part ", text, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        sections[name.strip()] = body
    parts = {"all"} if "all" in sections else {"1", "2", "3", "4"}
    passed = sorted(p for p in parts if p in sections and re.search(
        rf"^all release checks passed \(part {p}\)$", sections[p], re.M))
    failed = [f for p in parts if p in sections for f in re.findall(r"^FAIL  (.*)$", sections[p], re.M)]
    ok = set(passed) == parts and not failed
    return ok, (f"parts passed: {', '.join(passed) or 'none'} of {', '.join(sorted(parts))}"
                + (f"; failed: {', '.join(failed)}" if failed else ""))


def repository(root, c):
    bad = []
    for cmd in c["commands"]:
        p = subprocess.run([sys.executable, str(root / cmd[0]), *[str(root) if a == "." else a
                                                                  for a in cmd[1:]]],
                           capture_output=True, text=True)
        if p.returncode != 0:
            bad.append(pathlib.Path(cmd[0]).name)
    return not bad, ("all pass" if not bad else "failed: " + ", ".join(bad))


RULES = {f.__name__: f for f in (pipeline_median, writer_slowest, soak, soak_latency, e2e_chain,
                                 e2e_image, system_tests, release_checks)}
# [/snippet:rules]


def commit_of_part(out, part):
    """The full commit a part of the release checks ran on, or None if the tree had changes."""
    f = out / ("commit.txt" if part <= 1 else f"commit-part-{part}.txt")
    if not f.exists():
        raise Missing(f"{f.name} is missing")
    lines = f.read_text().splitlines()
    if not lines or not lines[0].startswith("commit "):
        raise Missing(f"{f.name} names no commit")
    return lines[0].split()[1] if len(lines) == 1 else None


# [snippet:verdict]
def evaluate(c, out, candidate, root=ROOT):
    """(verdict, what was found) of one criterion."""
    try:
        if c["rule"] == "repository":
            made_on = commit_of_part(out, 1)
            if made_on is None or not same_commit(made_on, candidate):
                return "STALE", f"the release checks ran on {made_on or 'a changed tree'}"
            head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()
            if not same_commit(head, candidate):
                return "STALE", f"the repository is at {head[:12]}, not at the candidate"
            ok, found = repository(root, c)
            return ("PASS" if ok else "FAIL"), found
        path = out / c["evidence"]
        if not path.is_file():
            return "MISSING", f"{c['evidence']} does not exist"
        text = path.read_text(errors="replace")
        if c["part"]:
            made_on = commit_of_part(out, c["part"])
            if c["evidence"].endswith(".json") and c["rule"].startswith("e2e"):
                made_on = e2e_checks(text)["commit"]
                made_on = None if made_on.endswith("-dirty") else made_on
            if made_on is None or not same_commit(made_on, candidate):
                return "STALE", f"made on {made_on or 'a tree with changes'}"
        ok, found = RULES[c["rule"]](text, c)
        return ("PASS" if ok else "FAIL"), found
    except Missing as e:
        return "MISSING", str(e)
    except (ValueError, KeyError, StopIteration) as e:  # evidence that cannot be read is missing
        return "MISSING", f"cannot read {c['evidence']}: {type(e).__name__} {e}"
# [/snippet:verdict]


def report(spec, rows, candidate, out):
    accepted = all(v == "PASS" for _, v, _ in rows)
    lines = [f"# {spec['title']}, version {spec['version']}: "
             f"{'ACCEPTED' if accepted else 'NOT ACCEPTED'}", "",
             f"Candidate commit `{candidate[:12]}`; evidence from `{out}`.", "",
             "| Criterion | Requirements | Target | Found | Verdict |", "|---|---|---|---|---|"]
    for c, verdict, found in rows:
        reqs = ", ".join(c["requirements"]) or "(process)"
        lines.append(f"| {c['id']}: {c['what']} | {reqs} | {c['target']} | {found} | {verdict} |")
    counts = {v: sum(r[1] == v for r in rows) for v in ("PASS", "FAIL", "MISSING", "STALE")}
    lines += ["", ", ".join(f"{n} {v.lower()}" for v, n in counts.items()) + "."]
    return accepted, "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--spec", type=pathlib.Path, default=SPEC)
    ap.add_argument("--commit", help="the candidate commit (default: that of part 1)")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if not args.out.is_dir():
        print(f"{args.out} is not a directory", file=sys.stderr)
        return 2
    spec = json.loads(args.spec.read_text())
    candidate = args.commit
    if candidate is not None and len(candidate) < SHORTEST:
        print(f"--commit {candidate}: give at least {SHORTEST} characters of the commit",
              file=sys.stderr)
        return 2
    if candidate is None:
        try:
            candidate = commit_of_part(args.out, 1)
        except Missing as e:
            print(f"no candidate commit: {e}; give --commit", file=sys.stderr)
            return 2
        if candidate is None:
            print("part 1 ran on a tree with changes; give --commit", file=sys.stderr)
            return 2
    rows = [(c, *evaluate(c, args.out, candidate, args.root)) for c in spec["criteria"]]
    accepted, text = report(spec, rows, candidate, args.out)
    print(text, end="")
    return 0 if accepted else 1


if __name__ == "__main__":
    sys.exit(main())
