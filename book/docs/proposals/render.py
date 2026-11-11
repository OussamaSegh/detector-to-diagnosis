#!/usr/bin/env python3
"""Render the design proposals in this directory.

Not called by book/build.sh. The default interior, EPUB, covers and download
page are not inputs to this script, and this script does not write them.

    python3 book/docs/proposals/render.py

Writes the PNG mockups next to design-directions.md. Intermediate files go
to /tmp/d2d-proposals.
"""
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BOOK = REPO / "book"
THEME_SRC = json.loads((BOOK / "templates" / "d2d.theme").read_text())
SAMPLE = HERE / "sample.md"
BOXES = BOOK / "filters" / "boxes.lua"
WORK = Path("/tmp/d2d-proposals")
CACHE = Path("/tmp/d2d-current")
PDF_URL = "https://oussamasegh.github.io/detector-to-diagnosis/detector-to-diagnosis-v1.1.1-dev.pdf"
COVER_URL = "https://oussamasegh.github.io/detector-to-diagnosis/detector-to-diagnosis-v1.1.1-dev-cover.jpg"
DPI = 130

# style -> (color, bold, italic). Unlisted styles keep the book's theme.
FOLIO_SYNTAX = {
    "Keyword": ("#8E3B2F", False, False), "ControlFlow": ("#8E3B2F", False, False),
    "Comment": ("#6B645C", False, True), "Documentation": ("#6B645C", False, True),
    "Annotation": ("#6B645C", False, True), "CommentVar": ("#6B645C", False, True),
    "Information": ("#6B645C", False, True), "RegionMarker": ("#6B645C", False, False),
    "String": ("#1C1917", False, True), "VerbatimString": ("#1C1917", False, True),
    "SpecialString": ("#1C1917", False, True), "SpecialChar": ("#1C1917", False, True),
    "Char": ("#1C1917", False, True),
    "DecVal": ("#3E4A44", False, False), "BaseN": ("#3E4A44", False, False),
    "Float": ("#3E4A44", False, False), "Constant": ("#3E4A44", False, False),
    "DataType": ("#3E4A44", False, False), "BuiltIn": ("#3E4A44", False, False),
    "Attribute": ("#3E4A44", False, False),
    "Function": ("#1C1917", False, False), "Operator": ("#1C1917", False, False),
    "Variable": ("#1C1917", False, False), "Other": ("#1C1917", False, False),
    "Extension": ("#1C1917", False, False),
    "Preprocessor": ("#8E3B2F", False, False), "Import": ("#8E3B2F", False, False),
    "Alert": ("#8E3B2F", False, False), "Error": ("#8E3B2F", False, False),
    "Warning": ("#8E3B2F", False, True),
}
ATLAS_SYNTAX = {
    "Keyword": ("#0E5E54", True, False), "ControlFlow": ("#0E5E54", True, False),
    "Comment": ("#6B6560", False, True), "Documentation": ("#6B6560", False, True),
    "Annotation": ("#6B6560", False, True), "CommentVar": ("#6B6560", False, True),
    "Information": ("#6B6560", False, True), "RegionMarker": ("#6B6560", False, False),
    "String": ("#8C3414", False, False), "VerbatimString": ("#8C3414", False, False),
    "SpecialString": ("#8C3414", False, False), "SpecialChar": ("#8C3414", False, False),
    "Char": ("#8C3414", False, False), "Preprocessor": ("#8C3414", False, False),
    "Import": ("#8C3414", False, False), "Alert": ("#8C3414", True, False),
    "Error": ("#8C3414", True, False), "Warning": ("#8C3414", False, True),
    "DecVal": ("#3D4A6B", False, False), "BaseN": ("#3D4A6B", False, False),
    "Float": ("#3D4A6B", False, False), "Constant": ("#3D4A6B", False, False),
    "Function": ("#1A1C1A", False, False), "DataType": ("#1A1C1A", False, False),
    "BuiltIn": ("#1A1C1A", False, False), "Attribute": ("#0E5E54", False, False),
    "Operator": ("#1A1C1A", False, False), "Variable": ("#1A1C1A", False, False),
    "Other": ("#1A1C1A", False, False), "Extension": ("#1A1C1A", False, False),
}
GANTRY_SYNTAX = {
    "Keyword": ("#161A1E", True, False), "ControlFlow": ("#161A1E", True, False),
    "Comment": ("#5C6570", False, True), "Documentation": ("#5C6570", False, True),
    "Annotation": ("#5C6570", False, True), "CommentVar": ("#5C6570", False, True),
    "Information": ("#5C6570", False, True), "RegionMarker": ("#5C6570", False, False),
    "String": ("#8A5A00", False, False), "VerbatimString": ("#8A5A00", False, False),
    "SpecialString": ("#8A5A00", False, False), "SpecialChar": ("#8A5A00", False, False),
    "Char": ("#8A5A00", False, False), "Preprocessor": ("#8A5A00", False, False),
    "Import": ("#8A5A00", False, False), "Warning": ("#8A5A00", False, True),
    "Alert": ("#8A5A00", True, False), "Error": ("#8A5A00", True, False),
    "DataType": ("#1F6B45", False, False), "BuiltIn": ("#1F6B45", False, False),
    "Attribute": ("#1F6B45", False, False),
    "DecVal": ("#161A1E", False, False), "BaseN": ("#161A1E", False, False),
    "Float": ("#161A1E", False, False), "Constant": ("#161A1E", False, False),
    "Function": ("#161A1E", False, False), "Operator": ("#161A1E", False, False),
    "Variable": ("#161A1E", False, False), "Other": ("#161A1E", False, False),
    "Extension": ("#161A1E", False, False),
}

DIRECTIONS = {
    "folio": {
        "header": HERE / "tex" / "folio.tex",
        "cover": HERE / "tex" / "cover-folio.tex",
        "site": HERE / "site" / "folio.html",
        "site_size": (900, 1680),
        "syntax": FOLIO_SYNTAX,
        "ink": "#1C1917", "codebg": "#F6F1E8", "numbers": "#8A8175",
        "rowcolor": None, "white_text": False,
        "class": "10pt",
        "main": "Linux Libertine O", "sans": "Linux Libertine O", "mono": "Linux Libertine Mono O",
        "indent": True,
        "geometry": ["paperwidth=8.5in", "paperheight=11in", "inner=1.08in", "outer=1.22in",
                     "top=0.90in", "bottom=0.86in", "headheight=14pt", "headsep=9pt", "footskip=22pt"],
    },
    "atlas": {
        "header": HERE / "tex" / "atlas.tex",
        "cover": HERE / "tex" / "cover-atlas.tex",
        "site": HERE / "site" / "atlas.html",
        "site_size": (1280, 1280),
        "syntax": ATLAS_SYNTAX,
        "ink": "#1A1C1A", "codebg": "#F7F4EE", "numbers": "#8A847C",
        "rowcolor": "sand", "white_text": False,
        "class": "11pt",
        "main": "EB Garamond", "sans": "Inter", "mono": "JetBrains Mono",
        "indent": False,
        "geometry": ["paperwidth=8.5in", "paperheight=11in", "inner=0.98in", "outer=1.32in",
                     "top=0.78in", "bottom=0.78in", "headheight=14pt", "headsep=10pt", "footskip=26pt"],
    },
    "gantry": {
        "header": HERE / "tex" / "gantry.tex",
        "cover": HERE / "tex" / "cover-gantry.tex",
        "site": HERE / "site" / "gantry.html",
        "site_size": (1400, 1080),
        "syntax": GANTRY_SYNTAX,
        "ink": "#161A1E", "codebg": "#F3F5F4", "numbers": "#8A93A0",
        "rowcolor": "panel", "white_text": True,
        "class": "10pt",
        "main": "IBM Plex Sans", "sans": "IBM Plex Sans", "mono": "IBM Plex Mono",
        "indent": False,
        "geometry": ["paperwidth=8.5in", "paperheight=11in", "inner=0.78in", "outer=0.70in",
                     "top=0.58in", "bottom=0.78in", "headheight=12pt", "headsep=6pt", "footskip=28pt"],
    },
}


def rel_luminance(h):
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((rel_luminance(a), rel_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def report_contrast():
    pairs = [
        ("folio oxide on white", "#8E3B2F", "#FFFFFF"),
        ("folio muted on white", "#5E584F", "#FFFFFF"),
        ("atlas teal on white", "#0E5E54", "#FFFFFF"),
        ("atlas teal on sand", "#0E5E54", "#E7E1D4"),
        ("atlas alert on white", "#8C3414", "#FFFFFF"),
        ("gantry amber text on white", "#8A5A00", "#FFFFFF"),
        ("gantry amber on panel", "#F0B429", "#1B2430"),
        ("gantry white on panel", "#FFFFFF", "#1B2430"),
        ("gantry signal on white", "#1F6B45", "#FFFFFF"),
    ]
    print("contrast")
    for name, a, b in pairs:
        print(f"  {contrast(a, b):5.2f}:1  {name}")


def theme_for(spec, ink, codebg, numbers):
    theme = json.loads(json.dumps(THEME_SRC))
    theme["text-color"] = ink
    theme["background-color"] = codebg
    theme["line-number-color"] = numbers
    for name, (color, bold, italic) in spec.items():
        style = theme["text-styles"][name]
        style["text-color"] = color
        style["bold"] = bold
        style["italic"] = italic
    return theme


def meta_for(d):
    lines = [
        "documentclass: book",
        "classoption:",
        "  - openany",
        f"  - {d['class']}",
        f"mainfont: \"{d['main']}\"",
        f"sansfont: \"{d['sans']}\"",
        f"monofont: \"{d['mono']}\"",
        "monofontoptions:",
        "  - Scale=0.90",
        "colorlinks: false",
        "secnumdepth: 2",
    ]
    if d["indent"]:
        lines.append("indent: true")
    return "\n".join(lines) + "\n"


def tint_tables(tex, rowcolor, white_text):
    if not rowcolor:
        return tex
    parts = tex.split(r"\begin{longtable}")
    out = [parts[0]]
    for part in parts[1:]:
        marker = r"\toprule\noalign{}"
        i = part.find(marker)
        if i < 0:
            out.append(r"\begin{longtable}" + part)
            continue
        j = i + len(marker)
        k = part.find(r"\\", j)
        header = part[j:k] if k >= 0 else ""
        if white_text:
            header = header.replace(r"\raggedright", r"\raggedright\color{white}")
            header = header.replace(r"\centering", r"\centering\color{white}")
        rest = part[k:] if k >= 0 else part[j:]
        part = part[:i] + marker + "\n\\rowcolor{" + rowcolor + "}" + header + rest
        out.append(r"\begin{longtable}" + part)
    return "".join(out)


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        log = (r.stdout or "") + (r.stderr or "")
        raise SystemExit(f"failed: {' '.join(cmd)}\n{log[-4000:]}")
    return r


def xelatex(tex):
    work = tex.parent
    for _ in range(2):
        run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name], work)
    log = (work / (tex.stem + ".log")).read_text(errors="replace")
    missing = [ln for ln in log.splitlines() if "Missing character" in ln]
    over = [ln for ln in log.splitlines() if "Overfull" in ln]
    if missing:
        print("  missing glyphs:")
        for ln in missing[:8]:
            print("   ", ln[:160])
    if over:
        print(f"  overfull boxes: {len(over)}")
        for ln in over[:6]:
            print("   ", ln[:160])
    else:
        print("  overfull boxes: 0")


def png_pages(pdf, dest, dpi=DPI):
    dest.mkdir(parents=True, exist_ok=True)
    run(["pdftoppm", "-png", "-r", str(dpi), pdf, str(dest / "p")], dest)
    return sorted(dest.glob("p-*.png"))


def spread(left, right, dest):
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    gap = 16
    canvas = Image.new("RGB", (a.width + b.width + gap, max(a.height, b.height)), (196, 192, 186))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + gap, 0))
    canvas.save(dest, optimize=True)


def shot(html, png, width, height):
    png = Path(png)
    profile = WORK / "chrome" / png.stem
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--hide-scrollbars", "--no-first-run",
        "--disable-extensions", "--force-device-scale-factor=1",
        f"--user-data-dir={profile}", f"--window-size={width},{height}",
        f"--screenshot={png}", html.resolve().as_uri(),
    ]
    try:
        subprocess.run(cmd, cwd=html.parent, text=True, capture_output=True, timeout=25)
    except subprocess.TimeoutExpired:
        pass
    if not png.exists() or png.stat().st_size < 8000:
        raise SystemExit(f"screenshot failed for {html}")


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    print("fetch", url)
    urllib.request.urlretrieve(url, dest)
    return dest


def build_direction(name, d):
    print(f"== {name}")
    work = WORK / name
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    theme = work / "theme.theme"
    theme.write_text(json.dumps(theme_for(d["syntax"], d["ink"], d["codebg"], d["numbers"])))
    meta = work / "meta.yaml"
    meta.write_text(meta_for(d))
    tex = work / "sample.tex"
    cmd = [
        "pandoc", str(SAMPLE), "--from",
        "markdown+smart+fenced_divs+bracketed_spans+pipe_tables+raw_attribute+raw_tex",
        "--lua-filter", str(BOXES), "--highlight-style", str(theme),
        "--metadata-file", str(meta), "--top-level-division", "chapter",
        "--number-sections", "-t", "latex", "--include-in-header", str(d["header"]),
        "-s", "-o", str(tex),
    ]
    for g in d["geometry"]:
        cmd.extend(["-V", f"geometry:{g}"])
    run(cmd, work)
    tex.write_text(tint_tables(tex.read_text(), d["rowcolor"], d["white_text"]))
    xelatex(tex)
    pages = png_pages(work / "sample.pdf", work / "png")
    print("  pages", len(pages))
    if len(pages) < 4:
        raise SystemExit(f"{name}: expected at least 4 pages, got {len(pages)}")
    shutil.copy(pages[0], HERE / f"{name}-opener.png")
    spread(pages[1], pages[2], HERE / f"{name}-spread.png")
    shutil.copy(pages[3], HERE / f"{name}-figure.png")
    # Keep a later page too if the figure was not alone, so the write-up can see it.
    for i, p in enumerate(pages, 1):
        shutil.copy(p, work / "png" / f"page-{i}.png")


def build_cover(name, d, plate):
    work = WORK / f"cover-{name}"
    work.mkdir(parents=True, exist_ok=True)
    job = work / "cover.tex"
    prefix = ""
    if name == "atlas":
        prefix = f"\\def\\nlfplate{{{plate}}}\\input{{{d['cover']}}}\n"
        # The cover file is \input, so it must not also be a full document we copy.
        job.write_text(prefix)
    else:
        shutil.copy(d["cover"], job)
    xelatex(job)
    pages = png_pages(work / "cover.pdf", work, dpi=140)
    shutil.copy(pages[0], HERE / f"{name}-cover.png")


def build_sites():
    for name, d in DIRECTIONS.items():
        w, h = d["site_size"]
        shot(d["site"], HERE / f"{name}-download.png", w, h)
        print("site", name)


def current_site(dest):
    dest.write_text("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Detector to Diagnosis</title>
<style>
:root { --bg: #fbfaf7; --fg: #1d232b; --muted: #5b6573; --card: #ffffff; --line: #dfe3e8; --accent: #1f5fa8; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 2rem; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 24px; }
h2 { font-size: 1.15rem; margin: 32px 0 12px; }
ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
li { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
a { color: var(--accent); }
.dl { font-weight: 600; font-size: 1.05rem; text-decoration: none; }
.what { margin: 4px 0 6px; }
.meta { color: var(--muted); font-size: 0.85rem; overflow-wrap: anywhere; }
code { font-size: 0.85em; }
footer { margin-top: 40px; color: var(--muted); font-size: 0.9rem; }
</style></head><body><main>
<h1>Detector to Diagnosis</h1>
<p class="sub">Building regulated medical imaging software in modern C++. Version 1.1.1-dev, a
work-in-progress edition released Part by Part.</p>
<h2>The book</h2>
<ul>
<li><a class="dl" href="#">EPUB</a><p class="what">Reflowable, for e-readers and reading apps (Apple Books, Google Play Books, Kobo; Send to Kindle converts it).</p><p class="meta">detector-to-diagnosis-v1.1.1-dev.epub, 5.1 MB, SHA-256 <code>824240ba99aed43e207ca5622ad8a625969a62cddea556ca4f7a261a0c712320</code></p></li>
<li><a class="dl" href="#">PDF</a><p class="what">The book's own 8.5 x 11 inch pages, for a tablet, a computer or paper.</p><p class="meta">detector-to-diagnosis-v1.1.1-dev.pdf, 8.6 MB, SHA-256 <code>5437e65489ab307ddcfc44da75cd8f8a374afc87b0a7da08353007a796952f51</code></p></li>
<li><a class="dl" href="#">PDF for Boox Air 5C (10.3 inch E Ink)</a><p class="what">Pages the size of a 10.3 inch 4:3 screen (Onyx Boox Air 5C and similar), narrow margins, so a page fills the screen without zoom; links, bookmarks and color kept.</p><p class="meta">detector-to-diagnosis-v1.1.1-dev-boox-air-5c.pdf, 8.9 MB, SHA-256 <code>a2504ec38dda6199052744d08ecb9ff5036890f28f0e3aa17b7bc7e0d66d4b5e</code></p></li>
<li><a class="dl" href="#">Front cover (JPEG)</a><p class="what">The front cover at 300 dpi, 2550 x 3300 pixels.</p><p class="meta">detector-to-diagnosis-v1.1.1-dev-cover.jpg, 1.2 MB, SHA-256 <code>d5ed588eaffb8deb54db417bd1b5eef4b7f02b61d6cb2dc192e00bdf9fa1cf7e</code></p></li>
<li><a class="dl" href="#">Print cover (PDF)</a><p class="what">The paperback's full wrap for 8.5 x 11 inch pages on white paper: back cover, spine and front cover with 1/8 inch bleed, the spine sized for this edition's page count, the barcode area left empty.</p><p class="meta">detector-to-diagnosis-v1.1.1-dev-cover.pdf, 1.9 MB, SHA-256 <code>f063275d1777139d214ff3d146ab5df209ad7976df3fb35a4db590c084758a7f</code></p></li>
</ul>
<h2>The solutions manual</h2>
<ul>
<li><a class="dl" href="#">EPUB</a><p class="what">Reflowable, for e-readers and reading apps.</p><p class="meta">detector-to-diagnosis-solutions-v1.1.1-dev.epub, 1.0 MB, SHA-256 <code>2d782313f4d5bc627128bb63e4fc1f6bbc366a50fe410e2ca716e2d176310d78</code></p></li>
<li><a class="dl" href="#">PDF</a><p class="what">The book's own 8.5 x 11 inch pages.</p><p class="meta">detector-to-diagnosis-solutions-v1.1.1-dev.pdf, 2.4 MB, SHA-256 <code>cdcf773f973b56fe472b4df3be9f0b397174f04e85cc01eb8184b9806c52d989</code></p></li>
</ul>
<footer><p>Built from <a href="#">the companion repository</a> at commit <code>340ac27</code> by GitHub Actions. Every code listing in the book is included from that repository and is compiled and tested there. The book is for learning; it is not a substitute for a manufacturer's quality management system.</p></footer>
</main></body></html>
""")


def reference_pages():
    pdf = fetch(PDF_URL, CACHE / "book.pdf")
    out = WORK / "current"
    out.mkdir(parents=True, exist_ok=True)
    # File pages of the screen PDF published for 1.1.1-dev (commit 340ac27).
    wanted = {1: "current-cover", 22: "current-part", 24: "current-opener",
              25: "current-code", 26: "current-table", 27: "current-callout", 28: "current-listing"}
    for n, name in wanted.items():
        run(["pdftoppm", "-png", "-r", "110", "-f", str(n), "-l", str(n),
             str(pdf), str(out / name)], out)
        src = next(out.glob(f"{name}-*.png"))
        shutil.copy(src, HERE / f"{name}.png")
    html = WORK / "current-site.html"
    current_site(html)
    shot(html, HERE / "current-download.png", 860, 1500)


def plate():
    src = fetch(COVER_URL, CACHE / "cover.jpg")
    im = Image.open(src)
    crop = im.crop((1250, 1400, 2450, 2600))
    dest = WORK / "plate.png"
    WORK.mkdir(parents=True, exist_ok=True)
    crop.save(dest)
    return dest


def main():
    report_contrast()
    WORK.mkdir(parents=True, exist_ok=True)
    art = plate()
    for name, d in DIRECTIONS.items():
        build_direction(name, d)
        build_cover(name, d, art)
    build_sites()
    reference_pages()
    print("wrote PNGs in", HERE)


if __name__ == "__main__":
    main()
