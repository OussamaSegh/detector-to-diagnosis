#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The web edition of the book (roadmap 2.0.0, Theme F): one HTML page per chapter, from the EPUB.

The web pages are made from the EPUB that book/build.sh builds, not from the Markdown again, so
the web text is the EPUB's text: the same filters, figures with their alt text, MathML and code
listings. Each of the EPUB's spine documents becomes a page with a contents sidebar, previous and
next links, a search box and the book's styles, in light and dark (the dark styles are the light
ones with every color's lightness inverted in CIELAB, so each contrast stays about what it was).

Search needs no library: `search.json` holds, for every section (each h1 to h3), its page, anchor,
title and first words, and an index from each word to the sections that contain it; `search.js`
intersects the sections of the query's words, the last word as a prefix.

Usage:
  web.py build EPUB OUT_DIR --version X.Y.Z [--downloads URL] [--other LABEL=URL]
        writes OUT_DIR/index.html (cover, title and contents), OUT_DIR/chNNN.html and the assets.
        --downloads is the download page relative to OUT_DIR (default ../); --other links the
        other volume (for example "Solutions manual=solutions/").
  web.py check OUT_DIR
        every page has a language, a title, one main landmark and one h1 (the index excepted),
        unique ids, alt text on every image, and every internal link and anchor resolves.

Exit status 0 on success, 1 on a problem.
"""
import html
import json
import pathlib
import posixpath
import re
import sys
import zipfile
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "web"  # web.css and search.js


# --- colors -------------------------------------------------------------------------------------

def _srgb_to_lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _lab_to_srgb(lab):
    L, a, b = lab
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def finv(t):
        return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)
    x, y, z = finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883
    r = 3.2406 * x - 1.5372 * y - 0.4986 * z
    g = -0.9689 * x + 1.8758 * y + 0.0415 * z
    bb = 0.0557 * x - 0.2040 * y + 1.0570 * z

    def gam(c):
        c = min(max(c, 0.0), 1.0)
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(round(gam(c) * 255) for c in (r, g, bb))


def dark_color(hex_color):
    """#RRGGBB (or #RGB) with its CIELAB lightness inverted: L -> 100 - L, hue and chroma kept.
    The darkest text becomes light text on the darkest background, and so on."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    L, a, b = _srgb_to_lab(rgb)
    # Map onto 6..98 rather than 0..100: pure white text on pure black glares. With this mapping
    # every pair of the book's colors that has 4.5:1 in light still has it in dark (tested).
    L2 = 98 - 0.92 * L
    return "#%02X%02X%02X" % _lab_to_srgb((L2, a, b))


def dark_css(css):
    """The same rules with every hex color replaced by its dark counterpart."""
    return re.sub(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b", lambda m: dark_color(m.group(0)), css)


def contrast(c1, c2):
    """WCAG contrast ratio of two #RRGGBB colors."""
    def lum(h):
        h = h.lstrip("#")
        def lin(c):
            c /= 255
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# --- the EPUB -----------------------------------------------------------------------------------

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def tokens(text):
    """Lowercase words for the search index: letters and digits, with inner . + # _ - kept
    (std::span becomes std and span; C++23, 62304, mlockall, sched_fifo stay whole)."""
    return [w.strip(".-_") for w in re.findall(r"[a-z0-9][a-z0-9_.+#-]*", text.lower())
            if len(w.strip(".-_")) > 1]


class Epub:
    def __init__(self, path):
        self.zip = zipfile.ZipFile(path)
        container = self.zip.read("META-INF/container.xml").decode()
        self.opf = re.search(r'full-path="([^"]+)"', container).group(1)
        self.base = posixpath.dirname(self.opf)
        opf = self.zip.read(self.opf).decode()
        items = {m.group(1): m.group(2) for m in
                 re.finditer(r'<item\b[^>]*\bid="([^"]+)"[^>]*\bhref="([^"]+)"', opf)}
        items.update({m.group(2): m.group(1) for m in
                      re.finditer(r'<item\b[^>]*\bhref="([^"]+)"[^>]*\bid="([^"]+)"', opf)})
        self.spine = [items[i] for i in re.findall(r'<itemref\b[^>]*\bidref="([^"]+)"', opf)]
        cover = re.search(r'<item\b[^>]*properties="cover-image"[^>]*href="([^"]+)"', opf) or \
            re.search(r'<item\b[^>]*href="([^"]+)"[^>]*properties="cover-image"', opf)
        self.cover = cover.group(1) if cover else None
        self.title = strip_tags(re.search(r"<dc:title[^>]*>(.*?)</dc:title>", opf, re.S).group(1))
        lang = re.search(r"<dc:language>(.*?)</dc:language>", opf)
        self.lang = lang.group(1) if lang else "en"

    def read(self, href):
        return self.zip.read(posixpath.join(self.base, href)).decode("utf-8")

    def names(self):
        return self.zip.namelist()


def page_name(href):
    """text/ch005.xhtml -> ch005.html"""
    return posixpath.basename(href).replace(".xhtml", ".html")


def rewrite(body):
    """A spine document's body markup, for a page in OUT_DIR."""
    body = re.sub(r'(href|src)="(?:\.\./)?text/', r'\1="', body)
    body = re.sub(r'(href)="([^"#:]+)\.xhtml', r'\1="\2.html', body)
    body = re.sub(r'(href|src)="\.\./(media|styles)/', r'\1="\2/', body)
    body = body.replace(' epub:type="', ' data-epub-type="')
    return body


def nav_entries(nav):
    """[(level, href, label html)] of the EPUB's table of contents, in order."""
    out, level = [], 0
    toc = re.search(r'<nav\b[^>]*epub:type="toc"[^>]*>(.*?)</nav>', nav, re.S)
    nav = toc.group(1) if toc else nav
    for m in re.finditer(r"<(/?)ol\b[^>]*>|<a href=\"([^\"]+)\"[^>]*>(.*?)</a>", nav, re.S):
        if m.group(0).startswith("<ol"):
            level += 1
        elif m.group(0).startswith("</ol"):
            level -= 1
        elif m.group(2):
            href = re.sub(r"^text/", "", m.group(2))
            href = re.sub(r"\.xhtml", ".html", href)
            out.append((level, href, m.group(3).strip()))
    return out


def label_text(label):
    """The text of a contents label, with its section number: '<span>1</span> Title' -> '1 Title'."""
    return re.sub(r"\s+", " ", strip_tags(label)).strip()


# --- pages --------------------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="generator" content="book/tools/web.py">
<link rel="stylesheet" href="styles/epub.css">
<link rel="stylesheet" href="styles/highlight.css">
<link rel="stylesheet" href="web.css">
<link rel="stylesheet" href="styles/dark.css" media="(prefers-color-scheme: dark)">
<script src="search.js" defer></script>
</head>
<body class="web">
<a class="skip" href="#content">Skip to the text</a>
<header class="bar">
  <button class="menu" type="button" aria-controls="contents" aria-expanded="false">Contents</button>
  <a class="home" href="index.html">{book}</a>
  <form class="search" role="search" action="index.html" onsubmit="return false">
    <label for="q" class="vh">Search the book</label>
    <input id="q" type="search" placeholder="Search" autocomplete="off" data-index="search.json">
    <div class="results" id="results" aria-live="polite" hidden></div>
  </form>
  <nav class="links" aria-label="Elsewhere">{others}<a href="{downloads}">Downloads</a></nav>
</header>
<div class="layout">
<nav class="contents" id="contents" aria-label="Contents">
<p class="mobile-links">{others}<a href="{downloads}">Downloads</a></p>
<ol>
{contents}
</ol>
</nav>
<main id="content">
{body}
<nav class="pager" aria-label="Previous and next">{pager}</nav>
</main>
</div>
<footer class="foot"><p>{book}, version {version}. The web edition has the text of the EPUB of
the same version. <a href="{downloads}">PDF, EPUB and errata</a>.</p></footer>
</body>
</html>
"""


def contents_html(entries, current):
    """The sidebar: every top-level entry; the sections of the current page under it."""
    lines, depth = [], 0
    for i, (level, href, label) in enumerate(entries):
        page = href.split("#")[0]
        if level == 1:
            if depth:
                lines.append("</ol></li>")
                depth = 0
            cur = ' aria-current="page" class="current"' if page == current else ""
            subs = [e for e in entries[i + 1:] if e[0] > 1 and e[1].split("#")[0] == page]
            lines.append(f'<li><a href="{href}"{cur}>{label}</a>' + ("" if subs and page == current else "</li>"))
            if subs and page == current:
                lines.append("<ol>")
                depth = 1
        elif level == 2 and depth and page == current:
            lines.append(f'<li><a href="{href}">{label}</a></li>')
    if depth:
        lines.append("</ol></li>")
    return "\n".join(lines)


def sections_of(body):
    """[(anchor, title, text)] of a page body, cut at each h1 to h3 that has an id."""
    heads = list(re.finditer(r'<(h[1-3])\b[^>]*?\bid="([^"]+)"[^>]*>(.*?)</\1>', body, re.S))
    # Pandoc puts the id on the enclosing <section>; take that when the heading has none.
    if not heads:
        heads = list(re.finditer(r'<section\b[^>]*\bid="([^"]+)"[^>]*>\s*<(h[1-3])\b[^>]*>(.*?)</\2>', body, re.S))
        heads = [(m.start(), m.group(1), m.group(3)) for m in heads]
    else:
        heads = [(m.start(), m.group(2), m.group(3)) for m in heads]
    out = []
    for i, (start, anchor, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        chunk = re.sub(r"<(math|style|script)\b.*?</\1>", " ", body[start:end], flags=re.S)
        chunk = re.sub(r"^.*?</h[1-3]>", " ", chunk, count=1, flags=re.S)  # the heading is the title
        out.append((anchor, label_text(title), re.sub(r"\s+", " ", strip_tags(chunk)).strip()))
    return out


def build(epub_path, out, version, downloads="../", others=()):
    ep = Epub(epub_path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "styles").mkdir(exist_ok=True)
    (out / "media").mkdir(exist_ok=True)
    nav_href = next(h for h in ep.spine if "nav" in h) if any("nav" in h for h in ep.spine) else None
    nav = ep.read(nav_href or "nav.xhtml")
    pages_set = {page_name(h) for h in ep.spine if h.startswith("text/ch")}
    entries = [e for e in nav_entries(nav) if e[1].split("#")[0] in pages_set]
    pages = [h for h in ep.spine if h.startswith("text/ch") and h.endswith(".xhtml")]
    css_links = []
    epub_css, highlight = "", ""
    for name in sorted(ep.names()):
        rel = posixpath.relpath(name, ep.base) if ep.base else name
        if rel.startswith("media/"):
            (out / rel).write_bytes(ep.zip.read(name))
        elif rel.startswith("styles/") and rel.endswith(".css"):
            css_links.append(rel)
            epub_css += ep.zip.read(name).decode() + "\n"
    titles, bodies = {}, {}
    for href in pages:
        doc = ep.read(href)
        style = re.search(r"<style>(.*?)</style>", doc, re.S)
        if style and not highlight:
            highlight = style.group(1)
        body = rewrite(re.search(r"<body\b[^>]*>(.*)</body>", doc, re.S).group(1))
        h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", body, re.S)
        name = page_name(href)
        titles[name] = label_text(h1.group(1)) if h1 else name
        bodies[name] = body
    (out / "styles/epub.css").write_text(epub_css)
    (out / "styles/highlight.css").write_text(highlight)
    (out / "styles/dark.css").write_text(
        "/* The light styles with each color's CIELAB lightness inverted (book/tools/web.py). */\n"
        + dark_css(epub_css + "\n" + highlight))
    for asset in ("web.css", "search.js"):
        (out / asset).write_text((ASSETS / asset).read_text())
    other_links = "".join(f'<a href="{html.escape(u)}">{html.escape(l)}</a>' for l, u in others)
    names = list(bodies)
    sections, words = [], {}
    for i, name in enumerate(names):
        prev = f'<a rel="prev" href="{names[i - 1]}">Previous: {html.escape(titles[names[i - 1]])}</a>' if i else ""
        nxt = f'<a rel="next" href="{names[i + 1]}">Next: {html.escape(titles[names[i + 1]])}</a>' if i + 1 < len(names) else ""
        (out / name).write_text(PAGE.format(
            lang=ep.lang, title=html.escape(f"{titles[name]} | {ep.title}"), book=html.escape(ep.title),
            downloads=html.escape(downloads), others=other_links, version=html.escape(version),
            contents=contents_html(entries, name), body=bodies[name], pager=prev + nxt))
        for anchor, title, text in sections_of(bodies[name]):
            n = len(sections)
            sections.append([name, anchor, title, text[:180]])
            for w in set(tokens(title + " " + text)):
                words.setdefault(w, []).append(n)
    (out / "search.json").write_text(json.dumps(
        {"titles": titles, "sections": sections, "words": dict(sorted(words.items()))},
        separators=(",", ":"), ensure_ascii=False))
    cover = ""
    if ep.cover:
        cover = (f'<img class="cover" src="{html.escape(ep.cover)}" alt="Front cover of {html.escape(ep.title)}" '
                 f'width="425" height="550">')
    title_page = ep.read(next(h for h in ep.spine if "title_page" in h)) if any("title_page" in h for h in ep.spine) else ""
    subtitle = re.search(r'<p class="subtitle">(.*?)</p>', title_page, re.S)
    full = "\n".join(f'<li class="l{lvl}"><a href="{h}">{lab}</a></li>' for lvl, h, lab in entries if lvl <= 2)
    landing = (f'<section class="landing">{cover}<div><h1>{html.escape(ep.title)}</h1>'
               + (f'<p class="subtitle">{subtitle.group(1)}</p>' if subtitle else "")
               + f'<p>Version {html.escape(version)}, the web edition: one page per chapter, with the '
               f'text, figures and listings of the EPUB. <a href="{names[0]}">Start reading</a>.</p></div></section>'
               f'<h2 id="all-contents">Contents</h2><ol class="toc-full">{full}</ol>')
    (out / "index.html").write_text(PAGE.format(
        lang=ep.lang, title=html.escape(ep.title), book=html.escape(ep.title), downloads=html.escape(downloads),
        others=other_links, version=html.escape(version), contents=contents_html(entries, None),
        body=landing, pager=f'<a rel="next" href="{names[0]}">Start: {html.escape(titles[names[0]])}</a>'))
    return len(names) + 1


# --- the check ----------------------------------------------------------------------------------

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = self.title = None
        self.in_title = False
        self.ids, self.dup, self.links, self.no_alt = set(), [], [], []
        self.mains = self.h1 = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.in_title, self.title = True, ""
        if tag == "main":
            self.mains += 1
        if tag == "h1":
            self.h1 += 1
        if "id" in a:
            (self.dup.append(a["id"]) if a["id"] in self.ids else self.ids.add(a["id"]))
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "img" and not (a.get("alt") or "").strip():
            self.no_alt.append(a.get("src"))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def check(out):
    errors, parsed = [], {}
    out = out.resolve()  # links are resolved to absolute paths, so the pages are keyed by them too
    for path in sorted(out.rglob("*.html")):
        p = Page()
        p.feed(path.read_text())
        parsed[path] = p
    for path, p in parsed.items():
        where = path.relative_to(out)
        if not p.lang:
            errors.append(f"{where}: no lang on <html>")
        if not (p.title or "").strip():
            errors.append(f"{where}: no title")
        if p.mains != 1:
            errors.append(f"{where}: {p.mains} main landmarks")
        if p.h1 != 1 and path.name != "index.html":
            errors.append(f"{where}: {p.h1} h1 headings")
        errors += [f"{where}: id {i} twice" for i in sorted(set(p.dup))]
        errors += [f"{where}: image {s} has no alt text" for s in p.no_alt]
        for link in p.links:
            if re.match(r"[a-z]+:", link):
                continue
            file, _, anchor = link.partition("#")
            target = (path.parent / file).resolve() if file else path
            if file.endswith("/"):
                target = target / "index.html"
            if file and not target.exists():
                if not file.startswith("../"):  # the download page is outside OUT_DIR
                    errors.append(f"{where}: link {link}: no such file")
                continue
            if anchor and target in parsed and anchor not in parsed[target].ids:
                errors.append(f"{where}: link {link}: no such anchor")
    index = json.loads((out / "search.json").read_text()) if (out / "search.json").exists() else None
    if index is None:
        errors.append("no search.json")
    else:
        for page, anchor, _, _ in index["sections"]:
            target = (out / page).resolve()
            if target not in parsed or anchor not in parsed[target].ids:
                errors.append(f"search.json: {page}#{anchor} does not resolve")
    return errors, len(parsed)


def main(argv):
    if len(argv) >= 4 and argv[1] == "build":
        args, downloads, others, version = argv[2:], "../", [], "unknown"
        while "--version" in args:
            i = args.index("--version")
            version = args[i + 1]
            del args[i:i + 2]
        while "--downloads" in args:
            i = args.index("--downloads")
            downloads = args[i + 1]
            del args[i:i + 2]
        while "--other" in args:
            i = args.index("--other")
            others.append(tuple(args[i + 1].split("=", 1)))
            del args[i:i + 2]
        n = build(pathlib.Path(args[0]), pathlib.Path(args[1]), version, downloads, others)
        print(f"web edition: {n} pages in {args[1]}")
        return 0
    if len(argv) == 3 and argv[1] == "check":
        errors, n = check(pathlib.Path(argv[2]))
        for e in errors[:200]:
            print(e)
        print(f"web edition {argv[2]}: {n} pages, " + ("ok" if not errors else f"{len(errors)} problem(s)"))
        return 1 if errors else 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
