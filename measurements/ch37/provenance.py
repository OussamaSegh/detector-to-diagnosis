#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Chapter 37 measurements: how MiniDAQ was built with an AI assistant, and what found its
defects.

    python3 measurements/ch37/provenance.py OUT_TEXT [ROOT]

Sections:
1. provenance: the commits that name an assistant, what they touched, and the assisted changes of
   product code without a test changed in the same commit (tools/ai_provenance.py);
2. the commit policy's rule assisted over the whole history;
3. the problem reports: what found each defect, from the field "found", and the categories of
   their root causes;
4. the defects found by an independent review of a Part, against those the author's own checks
   found.
Counts only: no address or name.
"""
import collections
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import ai_provenance as ap  # noqa: E402
import check_commits as cc  # noqa: E402

# What found a defect, by the first rule that matches the report's field "found" (lower case).
SOURCES = [
    ("independent review of a Part", ("review of part",)),
    ("internal audit", ("internal audit",)),
    ("fuzzing", ("fuzz_", "fuzzing", "fuzz-smoke")),
    ("release checks and their reviews", ("release checks", "release coverage review",
                                          "review of the controlled documents", "capa-0001 check",
                                          "soup review")),
    ("CI runs", ("github ci", "github actions", "ci run", "the ci runs")),
    ("the author's own tests and runs", ("system test", "local", "run_all.sh", "full ctest", "ctest",
                                         "end-to-end run", "recordings", "coverage report",
                                         "the first", "gate self-test")),
    ("design, development and measurement", ("design", "development", "measurements",
                                             "classification", "soup")),
]


def source(found):
    text = found.lower()
    for name, keys in SOURCES:
        if any(k in text for k in keys):
            return name
    return "other"


def main(out_path, root):
    lines = []
    say = lines.append
    policy = json.loads((root / "tools/commit_policy.json").read_text())
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "--short=7", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    say(f"Chapter 37: provenance of MiniDAQ's history at {head}, commit policy {policy['version']}")
    say("")

    say("1. Provenance (tools/ai_provenance.py)")
    r = ap.report(root, "HEAD", policy)
    own = r["commits"] - r["merges"]
    say(f"commits {r['commits']}, merges {r['merges']}; an assistant is named in {r['assisted']} "
        f"of the {own} that are not merges")
    say(f"assisted commits that change product code: {r['assisted_with_product_code']}, without a "
        f"test changed in the same commit: {len(r['assisted_product_code_without_a_test'])}")
    rows = {x["commit"]: x for x in r["rows"]}
    for sha in r["assisted_product_code_without_a_test"]:
        files = subprocess.run(["git", "-C", str(root), "show", "--format=", "--numstat", sha],
                               capture_output=True, text=True, check=True).stdout.split("\n")
        code = [f for f in files if f and ap.touched({"files": [f.split("\t")[-1]]},
                                                     ap.json.loads((root / ap.ITEMS).read_text())
                                                     ["items"])]
        changed = sum(int(f.split("\t")[0]) + int(f.split("\t")[1]) for f in code
                      if f.split("\t")[0].isdigit())
        say(f"  {sha}: {', '.join(sorted(rows[sha]['items']))}; {changed} product lines changed")
    say(f"assisted commits with a review trailer git parses: "
        f"{r['assisted_with_a_parsed_review_trailer']} (the trailer moved into the block in "
        "Chapter 36)")
    say("")

    say("2. The rule assisted over the whole history")
    known = cc.known_references(root)
    broken = [c["sha"][:7] for c in cc.commits(root, "HEAD") if cc.assisted(c, policy, known)]
    since = [c["sha"][:7] for c in cc.commits(root, f"{policy['since']}..HEAD")
             if cc.assisted(c, policy, known)]
    say(f"commits that break it: {len(broken)} in the whole history, {len(since)} since the "
        "policy began")
    say("")

    say("3. Problem reports")
    reports = json.loads((root / "docs/regulatory/problem-reports.json").read_text())["reports"]
    found = collections.Counter(source(x["found"]) for x in reports)
    say(f"{len(reports)} reports; found by:")
    for name, _ in SOURCES + [("other", ())]:
        if found[name]:
            say(f"  {name}: {found[name]}")
    cats = collections.Counter((x.get("root_cause") or {}).get("category", "none recorded")
                               for x in reports)
    say("root cause categories: " + ", ".join(f"{k} {v}" for k, v in sorted(cats.items())))
    safety = sum(1 for x in reports if x["evaluation"]["safety_relevant"])
    say(f"evaluated as safety relevant: {safety}")
    say("")

    say("4. Independent reviews")
    log = subprocess.run(["git", "-C", str(root), "log", "--merges", "--reverse", "--format=%h %s"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    reviews = [x.split()[0] for x in log if "review" in x.lower()]
    say(f"merges of an independent review's branch: {len(reviews)}")
    for m in reviews:
        n = subprocess.run(["git", "-C", str(root), "rev-list", "--count", f"{m}^1..{m}^2"],
                           capture_output=True, text=True, check=True).stdout.strip()
        files = subprocess.run(["git", "-C", str(root), "diff", "--name-only", f"{m}^1", m],
                               capture_output=True, text=True, check=True).stdout.split()
        book = sum(f.startswith("book/") for f in files)
        say(f"  {m}: {n} commit(s) on the branch, {len(files)} files changed by the merge, "
            f"{book} of them in the book, {len(files) - book} elsewhere")
    by_review = [x["id"] for x in reports if source(x["found"]) == "independent review of a Part"]
    say(f"problem reports opened from them: {len(by_review)} ({', '.join(by_review)})")

    pathlib.Path(out_path).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "provenance.txt",
         pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent.parent)
