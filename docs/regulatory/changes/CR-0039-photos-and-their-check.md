# CR-0039: Photos in the book, and the check of their credits

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-24, by the software lead |
| Source | improvement: roadmap 2.3.0, Theme I (docs/ROADMAP-2.3.0-illustrations.md, sections 3 and 4) |
| Decision | approved, 2026-11-25, by the software lead in writing (decision in the project thread, 09:25 UTC) |
| Commits | eade60e (the photo build and check), merged in 55fd363 |

## Description

The book may carry photos by others, under the photo policy of the illustrations plan (section 3):
public domain, CC0 or CC BY only, no faces, brands or identifiable places, metadata stripped, a
credit in the caption and on a back-matter page. The book's figure tool, `book/tools/figures.py`,
builds a photo like any other figure (a 300 ppi PDF for print, gray with its contrast stretched for
the black-ink profile, a JPEG of at most 1600 px wrapped in SVG for the EPUB), and its `check`
command, run as the CTest test `book.figures`, gains the photo checks: every photo has an entry in
`book/figures/photos/credits.json` with every field, an allowed license, a date the license page
was read, and the SHA-256 of the file as stored; no metadata is left in the file; the caption ends
with the credit; the photo has 300 ppi at its printed width; and the credits page is current and in
the book. `book/tools/test_photos.py` (CTest `book.photos_tool`) shows each check failing on a bad
photo and passing on a good one. `book/LICENSE` says that the photos keep their own licenses.

## Reason

The author asked for photos (2026-11-24). A photo is the one kind of figure whose rights are not
the author's, and the repository is public: one image with a wrong or missing license is an
infringement in a public repository and in every built book. A check that runs on every change
makes the policy hold without relying on memory, as `book.figures` already does for alt text and
references.

## Impact analysis

### Requirements

None. The change is to the book's build tooling and its figure check, not to MiniDAQ.

### Software items and safety class

None of MiniDAQ's software items changes; `book/tools/` is the book's build tooling, outside the
product and outside the tool list of the verification plan, like the rest of `figures.py`.

### Risk

No hazard or risk control is affected. The risk this change controls is a legal one for the book,
recorded in the illustrations plan (section 8), not a hazard of the device.

### SOUP

None. Pillow is already installed with matplotlib for the figures (`analysis/requirements.lock`);
it is used here to read and write the photos and is not part of MiniDAQ.

### Interfaces and data formats

None of MiniDAQ's. A new file format for the book: `book/figures/photos/credits.json`, described
in `book/figures/photos/README.md`.

### Documents

`book/LICENSE` gains a paragraph on the photos' licenses. No controlled document changes.

### Regulatory

None: the intended use and every safety-relevant function are unchanged.

## Verification

- `python3 -B book/tools/test_photos.py`: a photo that follows the policy passes; no credit, a
  share-alike license, EXIF left in the file, a file changed after its credit, too few pixels for
  the printed width, a caption without the credit, a missing field and a bad date each fail; the
  built photo is a PDF for print and an SVG of at most 1600 px for the EPUB.
- `python3 -B book/tools/figures.py check` passes on the book (no photos yet).
- The book's PDF and EPUB build as before; EPUBCheck reports no error.

The tests that verify it include `Photos.test_a_photo_that_follows_the_policy_passes`,
`Photos.test_a_share_alike_license_fails`, `Photos.test_exif_left_in_the_file_fails`,
`Photos.test_a_file_changed_after_its_credit_fails` and
`Photos.test_the_built_photo_is_gray_for_black_ink_and_small_for_the_epub`.

## Decision

Approved by the software lead on 2026-11-25 at 09:25 UTC, in writing in the project thread, after the
change was implemented and merged under review (eade60e, merged in 55fd363); the photos themselves
follow under this approval, each with its credit. Implemented: `tools/check_changes.py` reads the tests
of `book/tools/` since 773ef25 (MDQ-PR-104).
