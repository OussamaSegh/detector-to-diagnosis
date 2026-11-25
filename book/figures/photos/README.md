# Photos

The book's photos and their credit register (roadmap 2.3.0, Theme I; CR-0039). Drawn and
generated figures stay the default; a photo is used only where it shows something a drawing
cannot.

- **Allowed:** public domain (`PD`), `CC0-1.0`, `CC-BY-3.0`, `CC-BY-4.0`. Never BY-SA, NC, ND,
  GFDL-only, press or product photos, or images from papers, standards and data sheets.
- **Not shown:** faces, patient data, brands, logos, product names, identifiable places.
- **Metadata:** stripped (no EXIF, XMP, IPTC, comments or PNG text).
- **Credit:** one entry per file in `credits.json`: `file`, `title`, `source` (the file page),
  `author` (as the license asks to be credited), `license`, `license_url`, `read_on` (the date
  the license page was read), `read_by`, `sha256` of the file as stored, `changes`.
- **Caption:** ends with the short credit, `Photo: <author>, <license label>.`
- **Size:** at least 300 ppi at the width the figure is printed.

`python3 -B book/tools/figures.py check` enforces all of this, and `figures.py credits --write`
generates the back-matter page `book/src/back/photo-credits.md`, which `book/book.txt` must
include once there is a photo. The photos keep their own licenses, not the book's
(`book/LICENSE`).
