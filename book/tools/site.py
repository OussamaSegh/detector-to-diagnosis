#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Writes the download page of the book for GitHub Pages.

Usage: book/tools/site.py OUT_DIR VERSION FILES...

The files (EPUB and PDF, built by book/build.sh) are copied into OUT_DIR, and OUT_DIR/index.html
lists them with their size and SHA-256, so a reader can check a download."""
import hashlib
import html
import os
import pathlib
import shutil
import sys

KINDS = [  # (suffix of the file name, label, what it is for)
    (".epub", "EPUB", "Reflowable, for e-readers and reading apps (Apple Books, Google Play Books, "
                      "Kobo; Send to Kindle converts it)."),
    (".pdf", "PDF", "The book's own 7 x 10 inch pages, for a tablet, a computer or paper."),
]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Detector to Diagnosis</title>
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
h2 {{ font-size: 1.15rem; margin: 32px 0 12px; }}
ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
li {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }}
a {{ color: var(--accent); }}
.dl {{ font-weight: 600; font-size: 1.05rem; text-decoration: none; }}
.dl:hover {{ text-decoration: underline; }}
.what {{ margin: 4px 0 6px; }}
.meta {{ color: var(--muted); font-size: 0.85rem; overflow-wrap: anywhere; }}
code {{ font-size: 0.85em; }}
footer {{ margin-top: 40px; color: var(--muted); font-size: 0.9rem; }}
</style>
</head>
<body>
<main>
<h1>Detector to Diagnosis</h1>
<p class="sub">Building regulated medical imaging software in modern C++. Version {version}, a
work-in-progress edition released Part by Part.</p>
{sections}
<footer>
<p>Built from <a href="{repo}">the companion repository</a> at commit <code>{commit}</code> by
GitHub Actions. Every code listing in the book is included from that repository and is compiled
and tested there. The book is for learning; it is not a substitute for a manufacturer's quality
management system.</p>
</footer>
</main>
</body>
</html>
"""


def kind_of(name):
    for suffix, label, what in KINDS:
        if name.endswith(suffix):
            return label, what
    raise SystemExit(f"{name}: not an EPUB or PDF of the book")


def size(n):
    return f"{n / 1e6:.1f} MB"


def main(argv):
    if len(argv) < 4:
        raise SystemExit(__doc__)
    out, version, files = pathlib.Path(argv[1]), argv[2], [pathlib.Path(f) for f in argv[3:]]
    repo = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "OussamaSegh/detector-to-diagnosis")
    commit = os.environ.get("GITHUB_SHA", "local")[:7]
    out.mkdir(parents=True, exist_ok=True)
    groups = {"book": [], "solutions": []}
    order = [k[0] for k in KINDS]
    for f in files:
        shutil.copy2(f, out / f.name)
        group = "solutions" if "-solutions-" in f.name else "book"
        groups[group].append(f)
    sections = []
    for group, title in (("book", "The book"), ("solutions", "The solutions manual")):
        if not groups[group]:
            continue
        items = []
        for f in sorted(groups[group], key=lambda p: next(i for i, s in enumerate(order) if p.name.endswith(s))):
            label, what = kind_of(f.name)
            data = f.read_bytes()
            items.append(
                f'<li><a class="dl" href="{html.escape(f.name)}" download>{html.escape(label)}</a>'
                f'<p class="what">{html.escape(what)}</p>'
                f'<p class="meta">{html.escape(f.name)}, {size(len(data))}, SHA-256 '
                f'<code>{hashlib.sha256(data).hexdigest()}</code></p></li>')
        sections.append(f"<h2>{title}</h2>\n<ul>\n" + "\n".join(items) + "\n</ul>")
    (out / "index.html").write_text(PAGE.format(version=html.escape(version), sections="\n".join(sections),
                                                repo=repo, commit=html.escape(commit)))
    print(f"wrote {out / 'index.html'} with {len(files)} files")


if __name__ == "__main__":
    main(sys.argv)
