#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of book/tools/web.py, the web edition (roadmap 2.0.0, Theme F).

A small EPUB with Pandoc's layout is written here, so the test needs neither Pandoc nor TeX."""
import json
import pathlib
import re
import sys
import tempfile
import unittest
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import web  # noqa: E402

OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title id="t">Test Book</dc:title>
<dc:language>en-US</dc:language></metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />
<item properties="cover-image" id="cover_jpg" href="media/cover.jpg" media-type="image/jpeg" />
<item id="title_page_xhtml" href="text/title_page.xhtml" media-type="application/xhtml+xml" />
<item id="ch001_xhtml" href="text/ch001.xhtml" media-type="application/xhtml+xml" />
<item id="ch002_xhtml" href="text/ch002.xhtml" media-type="application/xhtml+xml" />
</manifest>
<spine><itemref idref="title_page_xhtml" /><itemref idref="nav" /><itemref idref="ch001_xhtml" />
<itemref idref="ch002_xhtml" /></spine>
</package>"""

NAV = """<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>
<nav epub:type="toc" id="toc"><ol class="toc">
<li><a href="text/ch001.xhtml"><span class="section-header-number">1</span> First</a><ol class="toc">
<li><a href="text/ch001.xhtml#sec-a"><span class="section-header-number">1.1</span> Section A</a></li></ol></li>
<li><a href="text/ch002.xhtml">Second</a></li></ol></nav>
<nav epub:type="landmarks" hidden="hidden"><ol><li><a href="text/title_page.xhtml">Title</a></li></ol></nav>
</body></html>"""


def chapter(title, body):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US">
<head><title>x</title><style>code span.kw {{ color: #0033B3; }}</style>
<link rel="stylesheet" type="text/css" href="../styles/stylesheet1.css" /></head>
<body epub:type="bodymatter">{title}{body}</body></html>"""


CH1 = chapter('<section id="ch01" class="level1"><h1><span class="header-section-number">1</span> First</h1>',
              '<p>Coincidence sorting with <code>std::span</code>.</p>'
              '<section id="sec-a" class="level2"><h2>Section A</h2><p>The windowed sorter, see '
              '<a href="ch002.xhtml#end">the end</a>.</p>'
              '<figure><img src="../media/fig.svg" alt="A diagram." /></figure></section></section>')
CH2 = chapter('<section id="second" class="level1"><h1>Second</h1>',
              '<p id="end">Dead time and NECR.</p></section>')


def epub(path, ch1=CH1, ch2=CH2):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml",
                   '<container><rootfiles><rootfile full-path="EPUB/content.opf"/></rootfiles></container>')
        z.writestr("EPUB/content.opf", OPF)
        z.writestr("EPUB/nav.xhtml", NAV)
        z.writestr("EPUB/text/title_page.xhtml", chapter("", '<p class="subtitle">A subtitle</p>'))
        z.writestr("EPUB/text/ch001.xhtml", ch1)
        z.writestr("EPUB/text/ch002.xhtml", ch2)
        z.writestr("EPUB/styles/stylesheet1.css", "body { color: #1F2937; } pre { background: #F5F7FA; }")
        z.writestr("EPUB/media/fig.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
        z.writestr("EPUB/media/cover.jpg", b"\xff\xd8\xff")


class Colors(unittest.TestCase):
    def test_dark_inverts_lightness_and_keeps_text_readable(self):
        self.assertLess(web.contrast(web.dark_color("#FFFFFF"), "#000000"), 1.5)  # white turns dark
        self.assertGreater(web.contrast(web.dark_color("#1F2937"), "#000000"), 9)   # ink turns light
        self.assertEqual(web.dark_color("#FFF"), web.dark_color("#FFFFFF"))

    def test_every_readable_pair_of_the_books_colors_stays_readable(self):
        import palette  # the generated palette.css, as book/build.sh writes it for the EPUB
        with tempfile.TemporaryDirectory() as d:
            palette.css(pathlib.Path(d) / "palette.css")
            css = (HERE.parent / "templates/epub.css").read_text() + (pathlib.Path(d) / "palette.css").read_text()
            css += (HERE.parent / "templates/d2d.theme").read_text()  # the listings' colors
        colors = sorted({c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", css)})
        self.assertGreater(len(colors), 40)
        backgrounds = [c for c in colors if web.contrast(c, "#000000") > 15] + ["#FFFFFF", "#FBFAF7"]
        for bg in backgrounds:
            for fg in colors:
                if web.contrast(fg, bg) >= 4.5:
                    self.assertGreaterEqual(web.contrast(web.dark_color(fg), web.dark_color(bg)), 4.5,
                                            f"{fg} on {bg}")

    def test_dark_css_replaces_every_color(self):
        out = web.dark_css("a { color: #FFFFFF; border: 1px solid #000; } b { x: #12345G; }")
        self.assertNotIn("#FFFFFF", out)
        self.assertIn("#12345G", out)


class Build(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.base = pathlib.Path(self.dir.name)
        epub(self.base / "b.epub")
        self.out = self.base / "read"
        web.build(self.base / "b.epub", self.out, "9.9.0", "../", [("Solutions manual", "https://example.org/")])

    def tearDown(self):
        self.dir.cleanup()

    def test_one_page_per_chapter_and_a_clean_check(self):
        names = sorted(p.name for p in self.out.glob("*.html"))
        self.assertEqual(names, ["ch001.html", "ch002.html", "index.html"])
        self.assertEqual(web.check(self.out), ([], 3))

    def test_links_media_and_navigation_are_rewritten(self):
        page = (self.out / "ch001.html").read_text()
        self.assertIn('href="ch002.html#end"', page)
        self.assertIn('src="media/fig.svg"', page)
        self.assertNotIn("xhtml", page.split("<main")[1])
        self.assertIn('aria-current="page"', page)
        self.assertIn('href="ch001.html#sec-a"', page)  # the current chapter's sections
        self.assertIn('rel="next" href="ch002.html"', page)
        self.assertIn('lang="en-US"', page)
        self.assertNotIn("Title</a>", page)  # the landmarks are not contents
        self.assertTrue((self.out / "media/fig.svg").exists())
        self.assertIn("#0033B3", (self.out / "styles/highlight.css").read_text())
        self.assertNotIn("#1F2937", (self.out / "styles/dark.css").read_text())

    def test_the_search_index(self):
        index = json.loads((self.out / "search.json").read_text())
        sec = {tuple(s[:2]): i for i, s in enumerate(index["sections"])}
        self.assertIn(sec[("ch001.html", "sec-a")], index["words"]["windowed"])
        self.assertIn(sec[("ch002.html", "second")], index["words"]["necr"])
        self.assertIn("std", index["words"])
        self.assertEqual(index["titles"]["ch002.html"], "Second")

    def test_the_check_finds_each_fault(self):
        page = self.out / "ch002.html"
        text = page.read_text()
        page.write_text(text.replace('<p id="end">', '<p id="end"><img src="media/fig.svg" alt=""><a href="ch009.html">x</a>'
                                     '<a href="ch001.html#nowhere">y</a><span id="end"></span>')
                        .replace('lang="en-US"', ""))
        errors, _ = web.check(self.out)
        text = "\n".join(errors)
        for want in ("no alt text", "ch009.html: no such file", "#nowhere: no such anchor", "id end twice",
                     "no lang"):
            self.assertIn(want, text)
        self.assertIn("ch001.html#sec-a", (self.out / "ch001.html").read_text())

    def test_tokens(self):
        self.assertEqual(web.tokens("C++23, std::span and IEC 62304."), ["c++23", "std", "span", "and", "iec", "62304"])


if __name__ == "__main__":
    unittest.main()
