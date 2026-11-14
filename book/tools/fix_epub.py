#!/usr/bin/env python3
"""Post-process a Pandoc EPUB: rename media/*.svgz to *.svg, add accessibility metadata.

Pandoc names SVG images *.svgz (its MIME table lists that extension first) even
though they are plain SVG. The manifest media-type is right, but some readers
look at the extension. Rewrites the archive with 'mimetype' stored first.

The package document gets the accessibility metadata of EPUB Accessibility 1.1
(schema.org access modes, features, hazards and a summary; roadmap 2.0.0, Theme A),
which Pandoc does not write. The summary states what the book provides, not a
conformance claim: no conformance audit has been made.
"""
import re
import sys
import zipfile

A11Y = """<meta property="schema:accessMode">textual</meta>
<meta property="schema:accessMode">visual</meta>
<meta property="schema:accessModeSufficient">textual,visual</meta>
<meta property="schema:accessModeSufficient">textual</meta>
<meta property="schema:accessibilityFeature">alternativeText</meta>
<meta property="schema:accessibilityFeature">MathML</meta>
<meta property="schema:accessibilityFeature">structuralNavigation</meta>
<meta property="schema:accessibilityFeature">tableOfContents</meta>
<meta property="schema:accessibilityFeature">readingOrder</meta>
<meta property="schema:accessibilityFeature">displayTransformability</meta>
<meta property="schema:accessibilityHazard">none</meta>
<meta property="schema:accessibilitySummary">Every figure has a text alternative, and the text refers to each figure by number. Equations are MathML. Headings give the structure, and the table of contents links every chapter and section. Code listings are text. No conformance audit against WCAG has been made.</meta>
"""


def add_a11y(opf: bytes) -> bytes:
    """The package document with the accessibility metadata, once."""
    text = opf.decode("utf-8")
    if "schema:accessMode" in text:
        return opf
    return re.sub(r"</metadata>", A11Y + "</metadata>", text, count=1).encode("utf-8")

def main(path: str) -> None:
    with zipfile.ZipFile(path) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    out = []
    for info, data in items:
        name = info.filename
        if name.endswith(".svgz"):
            name = name[:-1]
        if name.endswith((".xhtml", ".opf", ".ncx", ".html")):
            data = data.replace(b".svgz", b".svg").replace(b"_svgz", b"_svg")
        if name.endswith(".opf"):
            data = add_a11y(data)
        out.append((name, data))
    out.sort(key=lambda t: t[0] != "mimetype")
    with zipfile.ZipFile(path, "w") as zout:
        for name, data in out:
            if name == "mimetype":
                zout.writestr(zipfile.ZipInfo("mimetype"), data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
