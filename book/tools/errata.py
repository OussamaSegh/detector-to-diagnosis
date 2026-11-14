#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The book's errata (roadmap 2.0.0, Theme A): checks book/errata.json and writes its page.

Each erratum names where it is, the released versions that have the error, the version that
fixes it (or null while it is open) and what the reader should read instead. The check refuses
an id out of sequence, a version that was never released (no tag line in .github/tags.txt for
book-vX.Y.Z; a fix may also name a coming version, later than the newest release), a fix not later than every version it was
found in, and an empty field.

Usage:
  errata.py check ROOT          exit status 0 if book/errata.json is consistent
  errata.py page ROOT OUT.html  writes the errata page of the download page
"""
import html
import json
import pathlib
import re
import sys

FIELDS = ("id", "where", "found_in", "fixed_in", "text")


def key(v):
    return tuple(int(x) for x in re.match(r"\d+\.\d+\.\d+", v).group(0).split("."))


def released(root):
    """The versions with a release tag line in .github/tags.txt."""
    text = (root / ".github/tags.txt").read_text()
    return set(re.findall(r"^book-v(\d+\.\d+\.\d+) ", text, re.M))


def load(root):
    return json.loads((root / "book/errata.json").read_text())["errata"]


def check(errata, versions):
    """errata: the list; versions: the released versions."""
    errors = []
    for n, e in enumerate(errata, 1):
        name = e.get("id", f"entry {n}")
        missing = [f for f in FIELDS if f not in e or (e[f] in ("", []) and f != "fixed_in")]
        if missing:
            errors.append(f"{name}: missing {', '.join(missing)}")
            continue
        if e["id"] != f"E-{n:03d}":
            errors.append(f"{name}: expected id E-{n:03d} (ids are in sequence, none reused)")
        for v in e["found_in"]:
            if v not in versions:
                errors.append(f"{name}: found in {v}, which was never released")
        fixed = e["fixed_in"]
        if fixed is not None:
            if not re.fullmatch(r"\d+\.\d+\.\d+", fixed):
                errors.append(f"{name}: fixed_in {fixed} is not X.Y.Z")
            elif fixed not in versions and versions and key(fixed) <= max(key(v) for v in versions):
                errors.append(f"{name}: fixed in {fixed}, which was never released and is not "
                              f"a coming version (not later than the newest release)")
            elif any(key(fixed) <= key(v) for v in e["found_in"]):
                errors.append(f"{name}: fixed in {fixed}, not later than every version it was found in")
    return errors


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Errata, Detector to Diagnosis</title>
<style>
:root {{ --bg: #fbfaf7; --fg: #1d232b; --muted: #5b6573; --card: #ffffff; --line: #dfe3e8;
        --accent: #1f5fa8; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg: #14181d; --fg: #e6e9ed; --muted: #a3acb8; --card: #1c2128; --line: #2d343d;
          --accent: #7fb2ff; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg);
       font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width: 760px; margin: 0 auto; padding: 40px 16px 64px; }}
h1 {{ font-size: 2rem; margin: 0 0 4px; }}
.sub {{ color: var(--muted); margin: 0 0 24px; }}
ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
li {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }}
.head {{ font-weight: 600; }}
.meta {{ color: var(--muted); font-size: 0.85rem; }}
a {{ color: var(--accent); }}
</style>
</head>
<body>
<main>
<h1>Errata</h1>
<p class="sub">Errors in the released text of <em>Detector to Diagnosis</em> and its solutions
manual, newest first. This is version {version}. <a href="index.html">Back to the downloads</a>.</p>
<p>Found another? <a href="{repo}/issues/new?template=erratum.yml">Report an erratum</a>.</p>
<ul>
{items}
</ul>
</main>
</body>
</html>
"""


def page(errata, version, repo):
    items = []
    for e in reversed(errata):
        status = f"fixed in {e['fixed_in']}" if e["fixed_in"] else "open"
        items.append(
            f'<li id="{html.escape(e["id"])}"><p class="head">{html.escape(e["id"])}: '
            f'{html.escape(e["where"])}</p><p>{html.escape(e["text"])}</p>'
            f'<p class="meta">In {html.escape(", ".join(e["found_in"]))}; {status}.</p></li>')
    return PAGE.format(version=html.escape(version), repo=html.escape(repo), items="\n".join(items))


def main(argv):
    if len(argv) < 3 or argv[1] not in ("check", "page"):
        print(__doc__)
        return 1
    root = pathlib.Path(argv[2]).resolve()
    errata = load(root)
    current = (root / "VERSION").read_text().strip()
    if argv[1] == "check":
        errors = check(errata, released(root))
        for e in errors:
            print(e)
        print(f"errata: {len(errata)} entries, " + ("ok" if not errors else f"{len(errors)} problem(s)"))
        return 1 if errors else 0
    repo = "https://github.com/OussamaSegh/detector-to-diagnosis"
    pathlib.Path(argv[3]).write_text(page(errata, current, repo))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
