#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A survey of a codebase for someone who has just taken it over (Chapter 34).

    tools/survey.py ROOT [--since "180 days ago"] [--top 10] [--json FILE]

Puts side by side, for every software item of docs/architecture/software-items.json, what the
documents say about it (safety class, hazards, requirements and how many of them a test names,
problem reports) and what the history says (files, code lines, commits and changed lines since
--since). Then the file hotspots: the files changed most often, weighted by their size, where
defects and misunderstandings concentrate (A. Tornhill, "Your Code as a Crime Scene"). And two
checks of the item map itself: product files that no item claims, and files that two items claim
(the longest prefix owns a file, as tools/check_items.py rules; two of the same length are an
ambiguity), and prefixes that claim no file at all.

The survey decides nothing. It is a list of where to read first and which questions to ask.
Prints Markdown; exits 1 if a product file has no owner or an ambiguous one, 0 otherwise.
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import trace_matrix  # noqa: E402

ITEMS = "docs/architecture/software-items.json"
REPORTS = "docs/regulatory/problem-reports.json"
PRODUCT = ("minidaq/src/", "minidaq/include/", "minidaq/apps/")
SOURCE = {".cpp", ".hpp", ".h", ".cc", ".py"}
CLASS_ORDER = {"C": 0, "B": 1, "A": 2, None: 3}


# [snippet:owners]
def owners(path, items):
    """The ids of the items that claim a file, the owner first. An item claims every path that
    starts with one of its path prefixes (a directory ending in '/', or a file stem such as
    .../coincidence_sorter); when several do, the longest prefix owns the file, the rule of
    tools/check_items.py. Two items with prefixes of the same length are an ambiguity."""
    claims = sorted(((len(p), it["id"]) for it in items for p in it["paths"]
                     if path.startswith(p)), reverse=True)
    return list(dict.fromkeys(i for _, i in claims))


def ambiguous(path, items):
    """True when two items claim the file with prefixes of the same, longest length."""
    claims = [(len(p), it["id"]) for it in items for p in it["paths"] if path.startswith(p)]
    if not claims:
        return False
    longest = max(n for n, _ in claims)
    return len({i for n, i in claims if n == longest}) > 1
# [/snippet:owners]


def code_lines(text):
    """Lines that are neither blank nor only a comment: a rough size, the same for every file."""
    return sum(1 for line in text.splitlines()
               if line.strip() and not line.strip().startswith(("//", "#", "*", "/*")))


# [snippet:churn]
RENAME = re.compile(r"^(.*)\{(.*) => (.*)\}(.*)$")


def renamed_to(path):
    """The new path of a numstat entry: 'a/{b => c}/d' is a/c/d and 'a => b' is b."""
    m = RENAME.match(path)
    if m:
        return (m.group(1) + m.group(3) + m.group(4)).replace("//", "/")
    return path.split(" => ")[-1]


def churn(numstat):
    """{path: (commits, lines added and deleted)} from `git log --numstat --format=@%H`. A binary
    file ('-' counts) counts its commits and no lines; a renamed file counts under its new name."""
    commits, lines = collections.Counter(), collections.Counter()
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        path = renamed_to(path)
        commits[path] += 1
        if added != "-":
            lines[path] += int(added) + int(deleted)
    return {p: (commits[p], lines[p]) for p in commits}
# [/snippet:churn]


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


# [snippet:survey]
def survey(root, since, top=10):
    items = json.loads((root / ITEMS).read_text())["items"]
    tracked = git(root, "ls-files").splitlines()
    files = [f for f in tracked if f.startswith(PRODUCT) and pathlib.Path(f).suffix in SOURCE]
    dead = [(it["id"], p) for it in items for p in it["paths"]
            if not any(f.startswith(p) for f in tracked)]
    history = churn(git(root, "log", f"--since={since}", "--numstat", "--format=@%H", "--",
                        *PRODUCT))
    reqs, _, _ = trace_matrix.parse_srs((root / trace_matrix.SRS).read_text())
    tested = {rid for rid, _, _ in trace_matrix.scan(root)}
    reports = json.loads((root / REPORTS).read_text())["reports"]

    per_item = {it["id"]: {"item": it["id"], "class": it.get("class"),
                           "hazards": it.get("hazards", []), "files": 0, "code_lines": 0,
                           "commits": 0, "changed_lines": 0, "requirements": 0, "by_test": 0,
                           "tested": 0,
                           "reports": 0, "open_reports": 0} for it in items}
    unowned, overlaps, hotspots = [], [], []
    for f in files:
        size = code_lines((root / f).read_text(errors="replace"))
        commits, changed = history.get(f, (0, 0))
        who = owners(f, items)
        if not who:
            unowned.append(f)
        elif len(who) > 1:
            overlaps.append((f, who, ambiguous(f, items)))
        for i in who[:1]:
            row = per_item[i]
            row["files"] += 1
            row["code_lines"] += size
            row["commits"] += commits
            row["changed_lines"] += changed
        hotspots.append({"file": f, "item": who[0] if who else None, "commits": commits,
                         "code_lines": size, "score": commits * size})
    for rid, (_, item, methods) in reqs.items():
        if item in per_item:
            per_item[item]["requirements"] += 1
            if "T" in methods:
                per_item[item]["by_test"] += 1
                per_item[item]["tested"] += rid in tested
    for r in reports:
        if r.get("item") in per_item:
            per_item[r["item"]]["reports"] += 1
            per_item[r["item"]]["open_reports"] += r.get("status") != "closed"
    rows = sorted(per_item.values(), key=lambda r: (CLASS_ORDER.get(r["class"], 3),
                                                    -r["open_reports"], -r["commits"], r["item"]))
    hotspots = sorted((h for h in hotspots if h["score"] > 0),
                      key=lambda h: (-h["score"], h["file"]))
    return {"since": since, "items": rows, "hotspots": hotspots[:top], "unowned": unowned,
            "overlaps": overlaps, "dead_prefixes": dead, "files": len(files)}
# [/snippet:survey]


def markdown(s):
    out = [f"# Codebase survey (history since {s['since']})", "",
           f"{s['files']} product source files.", "",
           "## Software items", "",
           "| Item | Class | Hazards | Files | Code lines | Commits | Changed lines | Requirements "
           "(by test, tagged) | Problem reports (open) |",
           "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in s["items"]:
        out.append(f"| {r['item']} | {r['class'] or '-'} | {', '.join(r['hazards']) or '-'} | "
                   f"{r['files']} | {r['code_lines']:,} | {r['commits']} | "
                   f"{r['changed_lines']:,} | {r['requirements']} ({r['by_test']}, "
                   f"{r['tested']}) | {r['reports']} ({r['open_reports']}) |")
    out += ["", "## Hotspots: commits times code lines", "",
            "| File | Item | Commits | Code lines | Score |", "|---|---|---:|---:|---:|"]
    for h in s["hotspots"]:
        out.append(f"| `{h['file']}` | {h['item'] or '(none)'} | {h['commits']} | "
                   f"{h['code_lines']:,} | {h['score']:,} |")
    out += ["", "## The item map", ""]
    out.append("Files no item claims: "
               + (", ".join(f"`{f}`" for f in s["unowned"]) or "none") + ".")
    out.append("Files two items claim (the first, by the longest prefix, owns them): "
               + (", ".join(f"`{f}` ({', '.join(w)}{', AMBIGUOUS' if amb else ''})"
                            for f, w, amb in s["overlaps"]) or "none") + ".")
    out.append("Prefixes that claim no file: "
               + (", ".join(f"{i} `{p}`" for i, p in s["dead_prefixes"]) or "none") + ".")
    untested = [r["item"] for r in s["items"] if r["by_test"] > r["tested"]]
    out.append("Items with a requirement to be tested that no test names: "
               + (", ".join(untested) or "none") + ".")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=pathlib.Path)
    ap.add_argument("--since", default="180 days ago", help="git's --since (default: 180 days ago)")
    ap.add_argument("--top", type=int, default=10, help="hotspots to list (default 10)")
    ap.add_argument("--json", type=pathlib.Path, help="also write the survey as JSON")
    args = ap.parse_args(argv)
    s = survey(args.root.resolve(), args.since, args.top)
    print(markdown(s), end="")
    if args.json:
        args.json.write_text(json.dumps(s, indent=1) + "\n")
    return 1 if s["unowned"] or any(amb for _, _, amb in s["overlaps"]) else 0


if __name__ == "__main__":
    sys.exit(main())
