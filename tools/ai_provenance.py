#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Which changes an AI assistant helped make, what they touched, and what checked them
(Chapter 37, ADR 0032).

    ai_provenance.py ROOT [RANGE] [--json]

For every commit of the range (default: the whole history) it reports whether an assistant is
named in its trailers (`Co-Authored-By:`, `Assisted-by:` or `Generated-by:` with a value that
matches one of the policy's `assistants` patterns), the software items and safety classes its
product files belong to, whether it changed a test, and whether its review trailer is one git
parses. The summary counts assisted commits per item and lists the assisted commits that changed
a product item's code without changing a test in the same commit: the commits a reviewer of an
assistant's work should look at first. With --json the report is a JSON document for the release
record.

The commit policy's rule `assisted` (tools/check_commits.py) applies the same test to every new
commit. Exit status 0, or 2 for a usage error.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_commits as cc  # noqa: E402
from survey import owners  # noqa: E402

ITEMS = pathlib.Path("docs/architecture/software-items.json")
KEYS = ("co-authored-by", "assisted-by", "generated-by")
SOURCE = (".cpp", ".hpp", ".h", ".cc", ".sv", ".v", ".py")


# [snippet:assisted]
def assistant_of(message, policy):
    """The first trailer value that names an assistant of the policy, or None."""
    for key, value in cc.trailers(message):
        if key.lower() in KEYS and any(re.search(p, value, re.I) for p in policy["assistants"]):
            return value
    return None


def is_test(path):
    """A file of a test: under a tests directory, or a Python file named test_*.py."""
    parts = path.split("/")
    return "tests" in parts[:-1] or parts[-1].startswith("test_")


def touched(commit, items):
    """{item id: class} for the product code a commit changes (tests and documents left out)."""
    found = {}
    for path in commit["files"]:
        if is_test(path) or not path.endswith(SOURCE):
            continue
        ids = owners(path, items)
        if ids:
            item = next(i for i in items if i["id"] == ids[0])
            if item.get("class"):
                found[item["id"]] = item["class"]
    return found
# [/snippet:assisted]


def report(root, revision_range, policy):
    items = json.loads((pathlib.Path(root) / ITEMS).read_text())["items"]
    rows = []
    for c in cc.commits(root, revision_range):
        product = touched(c, items)
        rows.append({
            "commit": c["sha"][:12],
            "merge": len(c["parents"]) > 1,
            "assistant": assistant_of(c["message"], policy),
            "items": product,
            "tests": any(is_test(f) for f in c["files"]),
            "review": policy["review_trailer"] in dict(cc.trailers(c["message"])),
        })
    own = [r for r in rows if not r["merge"]]
    assisted = [r for r in own if r["assistant"]]
    per_item = {}
    for r in assisted:
        for item in r["items"]:
            per_item[item] = per_item.get(item, 0) + 1
    untested = [r for r in assisted if r["items"] and not r["tests"]]
    return {
        "range": revision_range,
        "commits": len(rows),
        "merges": len(rows) - len(own),
        "assisted": len(assisted),
        "assisted_with_product_code": sum(1 for r in assisted if r["items"]),
        "assisted_product_code_without_a_test": [r["commit"] for r in untested],
        "assisted_with_a_parsed_review_trailer": sum(1 for r in assisted if r["review"]),
        "assisted_per_item": dict(sorted(per_item.items())),
        "rows": rows,
    }


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__.split("\n\n")[1].strip(), file=sys.stderr)
        return 2
    root = pathlib.Path(args[0])
    policy = json.loads((root / cc.POLICY).read_text())
    try:
        r = report(root, args[1] if len(args) > 1 else "HEAD", policy)
    except ValueError as e:
        print(f"ai_provenance: {e}", file=sys.stderr)
        return 2
    if "--json" in argv:
        print(json.dumps(r, indent=2))
        return 0
    print(f"{r['commits']} commits ({r['merges']} merges) in {r['range']}; an assistant is named "
          f"in {r['assisted']}")
    print(f"assisted commits that change product code: {r['assisted_with_product_code']}; "
          f"without a test changed in the same commit: "
          f"{len(r['assisted_product_code_without_a_test'])}")
    for sha in r["assisted_product_code_without_a_test"]:
        row = next(x for x in r["rows"] if x["commit"] == sha)
        print(f"  {sha} {', '.join(f'{i} ({k})' for i, k in sorted(row['items'].items()))}")
    print(f"assisted commits with a review trailer git parses: "
          f"{r['assisted_with_a_parsed_review_trailer']}")
    print("assisted commits per item: "
          + ", ".join(f"{i} {n}" for i, n in r["assisted_per_item"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
