#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tests of the EPUB's figure numbers (book/filters/figures.lua after design.lua), review of 1.2.0.

The EPUB of 1.2.0 printed the appendix's figure references as ".10" to ".17" (erratum E-009):
design.lua numbers the appendix itself outside LaTeX and marks its headings unnumbered, and
figures.lua skipped them. The captions had no number at all. Skipped where Pandoc is missing
(the CI build jobs do not install it; the pages and kdp workflows build the EPUB with it).
"""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

BOOK = pathlib.Path(__file__).resolve().parent.parent

DOC = r"""# Part I: Things {.part}

# Alpha {#ch01}

See Figure [](#fig-a) and Figure [](#fig-b).

![cap a](x.png){#fig-a}

![cap b](x.png){#fig-b}

```{=latex}
\appendix
```

# Appendix thing {#app-x}

See Figure [](#fig-c).

![cap c](x.png){#fig-c}
"""


@unittest.skipUnless(shutil.which("pandoc"), "Pandoc is not installed")
class FigureNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "doc.md"
            src.write_text(DOC)
            cls.html = subprocess.run(
                ["pandoc", str(src), "-t", "html", "--number-sections",
                 "--lua-filter", str(BOOK / "filters/design.lua"),
                 "--lua-filter", str(BOOK / "filters/figures.lua")],
                check=True, capture_output=True, text=True).stdout

    def test_references_count_per_chapter_and_the_appendix_restarts_at_a(self):
        refs = dict(re.findall(r'<a\s+href="#(fig-[a-z]+)">([^<]*)</a>', self.html))
        self.assertEqual(refs, {"fig-a": "1.1", "fig-b": "1.2", "fig-c": "A.1"})

    def test_each_caption_starts_with_its_number(self):
        caps = re.findall(r'<span class="figure-number">([^<]*)</span>', self.html)
        self.assertEqual(caps, ["Figure 1.1.", "Figure 1.2.", "Figure A.1."])


if __name__ == "__main__":
    unittest.main()
