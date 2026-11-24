#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the photo checks of book/tools/figures.py (roadmap 2.3.0, Theme I; CR-0039).

A photo that follows the policy passes; each way of breaking it fails with its own message: no
credit, a license outside PD, CC0 and CC BY, metadata left in the file, a file changed after its
credit was written, too few pixels for its printed width, a caption without the credit, and a
photo with no entry. Each photo is made here, so the test needs nothing from the repository.
Skipped where Pillow is missing.
"""
import hashlib
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import figures  # noqa: E402

try:
    from PIL import Image
except ImportError:
    raise unittest.SkipTest("Pillow is not installed")


def make_photo(path, size=(2000, 1300), exif=False):
    img = Image.new("RGB", size, (90, 120, 150))
    if exif:
        e = Image.Exif()
        e[0x010F] = "SomeCamera"  # Make
        img.save(path, "JPEG", exif=e.tobytes())
    else:
        img.save(path, "JPEG")


def credit(path, **over):
    c = {"file": path.name, "title": "A crystal array", "source": "https://example.invalid/file",
         "author": "A. Photographer", "license": "CC-BY-4.0",
         "license_url": "https://creativecommons.org/licenses/by/4.0/", "read_on": "2026-11-25",
         "read_by": "software lead", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
         "changes": "none"}
    c.update(over)
    return c


def block(name, caption=None, width="100%"):
    cap = caption if caption is not None else "A crystal array. Photo: A. Photographer, CC BY 4.0."
    return ("ch08: fig-x", {"src": f"book/figures/photos/{name}", "caption": cap, "width": width})


class Photos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.photo = self.dir / "crystals.jpg"
        make_photo(self.photo)

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, credits, blocks):
        return figures.photo_problems(self.dir, credits, blocks)

    def test_a_photo_that_follows_the_policy_passes(self):
        self.assertEqual(self.problems([credit(self.photo)], [block("crystals.jpg")]), [])

    def test_a_photo_without_a_credit_fails(self):
        p = self.problems([], [block("crystals.jpg")])
        self.assertTrue(any("no entry in credits.json" in x for x in p), p)
        self.assertTrue(any("has no credit" in x for x in p), p)

    def test_a_share_alike_license_fails(self):
        p = self.problems([credit(self.photo, license="CC-BY-SA-4.0")], [])
        self.assertTrue(any("is not allowed" in x for x in p), p)

    def test_exif_left_in_the_file_fails(self):
        make_photo(self.photo, exif=True)
        p = self.problems([credit(self.photo)], [])
        self.assertTrue(any("metadata left" in x for x in p), p)

    def test_a_file_changed_after_its_credit_fails(self):
        c = credit(self.photo)
        make_photo(self.photo, size=(2100, 1300))
        p = self.problems([c], [])
        self.assertTrue(any("SHA-256" in x for x in p), p)

    def test_too_few_pixels_for_the_printed_width_fails(self):
        make_photo(self.photo, size=(1200, 800))
        p = self.problems([credit(self.photo)], [block("crystals.jpg", width="100%")])
        self.assertTrue(any("px are needed" in x for x in p), p)
        self.assertEqual(self.problems([credit(self.photo)], [block("crystals.jpg", width="60%")]), [])

    def test_a_caption_without_the_credit_fails(self):
        p = self.problems([credit(self.photo)], [block("crystals.jpg", caption="A crystal array.")])
        self.assertTrue(any("must end with the credit" in x for x in p), p)

    def test_a_missing_field_and_a_bad_date_fail(self):
        p = self.problems([credit(self.photo, read_by="", read_on="yesterday")], [])
        self.assertTrue(any("no read_by" in x for x in p), p)
        self.assertTrue(any("not a date" in x for x in p), p)

    def test_the_built_photo_is_gray_for_black_ink_and_small_for_the_epub(self):
        out = self.dir / "out.pdf"
        figures.build_photo(self.photo, "bw", "pdf", out)
        self.assertTrue(out.read_bytes().startswith(b"%PDF"))
        svg = self.dir / "out.svg"
        figures.build_photo(self.photo, "screen", "svg", svg)
        text = svg.read_text()
        self.assertIn('width="1600"', text)
        self.assertLess(len(text), figures.EPUB_MAX_BYTES * 4 // 3 + 1000)


if __name__ == "__main__":
    unittest.main()
