#!/usr/bin/env python3
"""Post-process a Pandoc EPUB: rename media/*.svgz to *.svg.

Pandoc names SVG images *.svgz (its MIME table lists that extension first) even
though they are plain SVG. The manifest media-type is right, but some readers
look at the extension. Rewrites the archive with 'mimetype' stored first.
"""
import sys
import zipfile

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
