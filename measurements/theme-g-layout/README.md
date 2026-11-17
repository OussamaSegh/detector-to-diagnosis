# Theme G: room in one volume (roadmap 2.1.0)

Question: how many pages does a denser layout give back, before Theme H adds text? Exit
criterion: at least 40 pages of room under KDP's 828 for an 8.5 x 11 in paperback.

Method, 2026-11-17: the screen PDF's LaTeX source of 2.0.2-dev (the text of 2.0.1) built with
XeLaTeX after a change of the page geometry only, two passes each, then the chosen layout built
in full with `book/build.sh all both`, `boox both` and `kdp both`.

| Layout (inner, outer, top, bottom in inches) | Pages | Overfull boxes |
|---|---|---|
| 1.0, 0.85, 0.85, 0.85 (2.0.1) | 819 | 0 |
| 1.0, 0.85, 0.75, 0.75 | 796 | 2 vbox before the fix |
| 1.0, 0.80, 0.75, 0.75 | 792 | 4 vbox, 1 hbox |
| 1.0, 0.85, 0.70, 0.70 (chosen) | 784 | 1 vbox before the fix, 0 after |
| 1.0, 0.75, 0.70, 0.70 | 782 | 1 vbox, 3 hbox |

Chosen: top and bottom 0.7 in, the sides unchanged, so the line length (6.65 in, the 1.1.0
interior design) stays as it was. The full build gives 784 pages for the screen PDF and 783 for
the KDP interior: 45 pages of room. The solutions manual goes from 218 to 216 pages. The Boox
PDF has its own margins and does not change.

The running head and the page number move from about 0.48 in to 0.33 in from the page edge
(measured with `pdftotext -bbox` over pages 30 to 780); KDP asks for 0.25 in without bleed.
`page-before-after.png` shows the same page of Chapter 10 before (left, 2.0.1 page 231) and
after (right, page 223).

A bug found on the way: a figure after a long table could run off the page (an `Overfull \vbox`
of about 220 pt, the figure's caption lost below the page). longtable's `\LT@start` sets
`\@colroom` to the whole column and forgets a top float already on the page; three of the
tested layouts had it. `book/templates/book-header.tex` now restores the room when the table
ends on the page where it started, and `book/build.sh` fails a PDF whose log has an
`Overfull \vbox`. With the fix, all three layouts tested (0.85, 0.75 and 0.70) have none.

Not needed: moving Appendix A to the web edition (answer 5 of roadmap 2.0.0), the body font
size and the space around listings.
