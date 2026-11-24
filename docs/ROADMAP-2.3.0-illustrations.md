# Roadmap for release 2.3.0: illustrations and photos

Status: accepted as Theme I of 2.3.0. Drafted on 2026-11-24, while 2.2.0 is being released, after
the author's remark that the book lacks illustrations and photos that would make its explanations
clearer. Decided the same day under the author's standing delegation (section 9): the photo policy
of section 3 is accepted, the plan becomes Theme I of a wider 2.3.0 and is folded into
`docs/ROADMAP-2.3.0.md` when that roadmap is drafted, and the five prototypes are kept as the
model for the rest. Work starts only after 2.2.0 is released and its independent review is merged
(the step-by-step rule of 2026-11-16).

## 1. Where the book stands

An audit of every chapter on 2026-11-24 (main at 5647d2e) found:

- **240 figures** in 40 chapters and Appendix A, all original: TikZ drawings, matplotlib plots
  generated from MiniDAQ's code and measurements, and a few Graphviz diagrams. The interior
  design of 1.1.0 (`book/docs/PLAN-interior-design.md`) brought them from 25 to over 200. Every
  chapter has between 2 and 12, Part II the most (51).
- **No photos, and no picture of anything physical.** The design plan ruled photos out
  (section 2, "no names, photos, places or company products"). A reader who has never stood
  next to a scanner meets the gantry, the detector block, the SiPM, the front-end board and the
  phantom only as labeled boxes. Chapter 8's detector chain is five boxes in a row; nothing
  shows how the parts sit on each other or how the blocks form the ring.
- **Few images of data that look like what the team looks at.** The book plots sinograms,
  spectra and reconstructions, but not a flood map, a reconstructed brain-like slice, a
  scope-like pulse trace, a mu-map, or MiniDAQ's own output in a DICOM viewer.
- **Mechanisms told in words that a step-by-step picture would show at once.** The clearest
  case was "filter each projection with a ramp, smear it back across the image, add the views"
  (Chapter 28): one sentence for the idea every reconstruction rests on.
- **No front-matter map.** The plan's F.1 to F.3 (book map, MiniDAQ at a glance, reading paths)
  were not made; the Part openers carry the pipeline map instead.
- **Fourteen sections over 900 words without a figure** (counted with code removed): Chapter 3
  "Testing concurrent code", 5 "Benchmark hygiene", 10 "Randoms" and "MiniDAQ's sorter", 14 "The
  development process", 15 "From hazard to harm", 17 "Verifying security", 19 "Test protocols
  and reports", 20 "Reproducible builds", 21 "Reviewing a change", "Reading a crash" and "A crash
  report", 29 "The crossing, measured", 30 "From figures to a specification", 39 "A projector
  with time of flight", 40 "From a field report to a decision", and Appendix A "Patterns".

## 2. What 2.3.0 is for

Make the book's explanations visual where a picture teaches faster than a paragraph, in this
order of value:

1. **Physical views**: what the hardware looks like and how it fits together, drawn (and,
   where a licensed photo exists, photographed).
2. **Data as the team sees it**: images made by running MiniDAQ's code, so a figure changes
   when the code changes and never shows what MiniDAQ does not do.
3. **Mechanisms step by step**: strips that build a result up in stages.
4. **The gaps** of section 1, where a long section has nothing to look at.

It is a book-only release: no change to MiniDAQ's code, requirements, risk controls or
interfaces, so no change request beyond the one for the figure checks (section 4, M1).

## 3. The rules for photos (revises the design plan, section 2)

The design plan's "no photos" rule becomes this policy. Drawn and generated figures stay the
default; a photo is used only where it shows something a drawing cannot (the look of a real
gantry, a crystal array, a SiPM tile, a board).

- **Sources allowed, in order of preference:**
  1. Drawings and renders made by scripts in this repository (the default).
  2. Photos taken for the book and given to it under the book's own terms.
  3. Third-party photos in the **public domain** (including works of the US federal
     government), under **CC0**, or under **CC BY** (3.0 or 4.0).
- **Not allowed:** CC BY-SA, any NC or ND license, GFDL-only, "fair use", press kits,
  manufacturers' product photos, images from papers, standards or data sheets, and anything
  whose license page a person has not read.
- **What a photo may not show:** a person's face or any patient data; a brand, a logo or a
  product name (the generic-book rule); a hospital or a place that can be identified. Images
  of products that are cropped or retouched to remove a logo count as modified (CC BY allows it,
  and the credit says so).
- **Metadata:** EXIF, XMP and IPTC are stripped (no GPS, no camera serial); a check fails a
  file that still has them.
- **The credit register**, `book/figures/photos/credits.json`: for each file, the source URL,
  the author as the license asks to be credited, the license and its URL, the date the license
  page was read, the person who read it, the SHA-256 of the file as stored, and the changes
  made (crop, retouch, grayscale). The caption ends with the short credit ("Photo: author,
  CC BY 4.0"); a "Photo credits" page in the back matter lists them all.
- **The license of the book**, `book/LICENSE`, gets a paragraph: third-party photos under
  `book/figures/photos/` keep their own licenses, listed in the credit register.
- **Where sourcing happens.** Wikimedia Commons is not reachable from the cloud sessions'
  network (tried on 2026-11-24: the proxy refused `commons.wikimedia.org`, and the page reader
  could not open its file pages either). Photos are therefore fetched by a manual GitHub
  Actions job (`photos.yml`, `workflow_dispatch`) that reads the file and its license metadata
  through the Commons API and opens a pull request, or by the author; in both cases a person
  reads the license page before the credit is recorded.

## 4. Milestones

| # | Content | Exit criterion |
|---|---|---|
| M0 | This plan and five prototypes (section 5) on a branch, PR for review | Coordinator's decision on the plan and the prototypes |
| M1 | The pipeline for photos: `book/figures/photos/`, the credit register, raster figures in `figures.py` (copy, resize to 300 ppi at print width, grayscale for `bw`, JPEG for EPUB under 400 KB), the checks of section 6, the back-matter credits page, the `book/LICENSE` paragraph; change request for the new check in `book.figures` | `figures.py check` covers photos; one test photo passes and one bad one (no credit, BY-SA, EXIF left) fails |
| M2 | Part II physical and data views, priority 1 of section 5 | All P1 items of Part II merged |
| M3 | Parts V and VI, and the front-matter map | All P1 items merged; P2 items of Parts V and VI merged or moved to 3.0.0 |
| M4 | Photos: up to 10, sourced through M1's job, each in a chapter where the drawing already exists (the photo shows the real thing next to it) | Each with a credit that a person checked |
| M5 | The gaps of section 1: one figure for each long section where a picture helps (not all fourteen need one; the reason is recorded when one is left as text) | The list closed, item by item |
| M6 | Review and release: B/W proof, Boox PDF on the device, EPUBCheck, page budget, the independent Opus review | Section 6 met; release 2.3.0 |

## 5. The inventory, ranked

Kinds: **TZ** TikZ drawing, **MP** matplotlib from repository code or data, **PH** photo under
section 3, **SS** a screenshot of a tool in this repository (no personal data, no account names).
Priority: **P1** teaches a core idea that has no picture today; **P2** helps clearly; **P3**
nice to have. Effort as in the design plan: S about 1 hour, M about 2.5 hours, L about 5 hours.
"Proto" marks the five prototypes of the M0 pull request.

| # | Ch | Figure | Kind | Source | P | Effort |
|---|---|---|---|---|---|---|
| 1 | 8 | A brain PET scanner, cover off: the ring of blocks, the bore, the bed, a decay and its LOR (proto) | TZ | drawn | P1 | M |
| 2 | 8 | One detector block, exploded: crystals and reflector, coupling, SiPM array, front-end board (proto) | TZ | drawn | P1 | M |
| 3 | 8 | A SiPM pixel's microcells and the pulse as a sum of cells (proto) | TZ | drawn | P1 | M |
| 4 | 28 | Backprojection built up from 1, 4, 16, 192 views, then ramp-filtered (proto) | MP | `tools/recon` projector | P1 | S |
| 5 | 26 | Flood map, peaks in order, lookup table (proto) | MP | Exercise 26.2 solution | P1 | S |
| 6 | Front | The journey of one event: decay, block, board, link, sorter, list mode, sinogram, image, DICOM, PACS, each with its chapter | TZ | drawn, chapter list | P1 | L |
| 7 | 9 | The readout in hardware: blocks, front-end boards, FPGA concentrators, clock fan-out, switch, acquisition PC | TZ | drawn from `docs/hw` | P1 | M |
| 8 | 9 | A pulse as a scope would show it: noisy SiPM pulse, leading-edge and CFD crossings, time over threshold | MP | pulse model of the simulator | P1 | S |
| 9 | 30 | An image-quality phantom in 3D: body, hot spheres, cold insert, the slice the ROIs come from | TZ | drawn, sizes from Ch 30 | P1 | M |
| 10 | 30 | What a reconstructed brain-like slice looks like: a 2D brain phantom, its OSEM image with and without corrections | MP | `tools/recon`, synthetic phantom | P1 | M |
| 11 | 10 | Randoms: prompt window and delayed window on two detectors' time lines, the delayed coincidences counted | TZ | drawn | P1 | S |
| 12 | 27 | Attenuation: the mu-map of a phantom and its correction-factor sinogram, side by side | MP | `tools/recon` | P2 | S |
| 13 | 39 | Time of flight along an LOR: the TOF kernel's weights in the image, for three CTRs | MP | TOF projector | P2 | S |
| 14 | 12 | From list mode to sinogram as a flip book: events binned one second at a time | MP | `minidaq_sim` list mode | P2 | M |
| 15 | 24 | Inside an FPGA, schematically: logic cells, block RAM, clock domains and the CDC FIFO between them | TZ | drawn | P2 | M |
| 16 | 22 | The acquisition PC opened up: CPU sockets, memory, NIC, PCIe, which core reads which queue | TZ | drawn, `platform/` profile | P2 | M |
| 17 | 25 | The embedded platform's board: SoC, flash slots A and B, watchdog, sensors | TZ | drawn | P2 | M |
| 18 | 35 | MiniDAQ's DICOM output in an open-source viewer | SS | Exercise output | P2 | S |
| 19 | 21 | Anatomy of a crash report: signal, backtrace, frames, the line that matters | TZ | a real report from `measurements/` | P2 | M |
| 20 | 3 | Anatomy of a TSan report, annotated | TZ | a recorded report | P2 | S |
| 21 | 14 | One change through the development process, as swim lanes (author, reviewer, CI, software lead) | TZ | `docs/regulatory/changes/` | P2 | M |
| 22 | 37 | An agent session as the reviewer sees it: prompt, plan, diff, gate report (rendered from a recorded session) | SS/TZ | `measurements/agent-evals/` | P2 | M |
| 23 | 20 | Reproducible builds: two machines, two builds, one hash | TZ | drawn | P3 | S |
| 24 | 5 | Benchmark noise: the same benchmark 30 times, strip plot, before and after pinning | MP | `measurements/ch05` | P3 | S |
| 25 | 15 | From hazard to harm for one hazard, as the sequence of events | TZ | `hazards.json` | P3 | S |
| 26 | 17 | Verifying security: which test covers which threat | MP | threat model | P3 | S |
| 27 | 19 | A test protocol and its report, page anatomy | TZ | the repo's protocol | P3 | S |
| 28 | 29 | The Python and C++ crossing, measured: time per call by size | MP | `measurements/ch29` | P3 | S |
| 29 | 40 | From a field report to a decision, as a flow | TZ | maintenance plan | P3 | S |
| 30 | 36 | The repository's own history as a branch graph around a release | MP | `git log` of a tag range | P3 | S |
| 31 | 8 | Photo: a clinical PET/CT gantry (next to item 1) | PH | section 3 | P2 | S |
| 32 | 8 | Photo: a scintillator crystal array or single crystals (next to item 2) | PH | section 3 | P2 | S |
| 33 | 8 | Photo: a SiPM array (next to item 3) | PH | section 3 | P2 | S |
| 34 | 8 | Photo: a photomultiplier tube, for the comparison with SiPMs | PH | section 3 | P3 | S |
| 35 | 24 | Photo: an FPGA development board | PH | section 3 | P3 | S |
| 36 | 30 | Photo: an image-quality phantom (next to item 9) | PH | section 3 | P3 | S |

About 30 new drawings and plots and up to 10 photos. At about a third of a page each, that is
12 to 15 pages at most. Measured on 2026-11-24: the screen PDF of main (5647d2e) has 794 pages,
and with the five prototypes it still has 794 (the figures filled float space already there), with
no overfull box; KDP's limit is 828.

## 6. Acceptance

- `python3 -B book/tools/figures.py check`: 0 problems, which after M1 also means every photo
  has a credit with an allowed license, its hash matches, it carries no EXIF/XMP/IPTC, and it
  is at least 300 ppi at its printed width.
- Every new figure builds in the three profiles (screen, boox, bw) and as SVG or JPEG for the
  EPUB; the book's overfull box count stays 0; EPUBCheck passes.
- Every figure is referenced in its text, has alt text written for a reader who cannot see it,
  and keeps its meaning in gray (checked on the `bw` proof by a person, page by page).
- Drawings of hardware say "drawn, not to scale" in the caption and show no product: a reader
  must not take them for a specific scanner.
- Every number in a figure is the number in the text, or comes from the code that the caption
  names.
- **Page budget**: the screen PDF stays under KDP's 828 pages. If 2.2.0 leaves less room than
  section 5 needs, the P3 items move to 3.0.0, whose two volumes have room.
- The independent Opus review of 2.3.0 covers the figures.

## 7. Out of scope

- Redrawing existing figures in a new style, and the design plan's colors and fonts.
- Animations (the web edition could take them later; the PDF cannot).
- Any figure of a real patient's data, real or "anonymized".
- New build dependencies: TikZ, matplotlib and poppler already build everything above. A 3D
  renderer (POV-Ray, Blender) was considered for photo-like renders and left out: it would be a
  new dependency for the author to approve, and TikZ's exploded views read well in gray.

## 8. Risks

| Risk | Effect | What we do |
|---|---|---|
| A photo's license is wrong or changes | The public repository and the book carry an infringing image | Only PD, CC0, CC BY; a person reads every license page; the hash and date are recorded; a photo is removed at once on doubt |
| A drawing is taken for a real product | The generic-book rule is broken; readers trust details that are invented | "Drawn, not to scale"; generic counts and sizes stated as typical; no product names |
| Page budget | The single-volume PDF passes 828 pages | Measure after each milestone; P3 items move to 3.0.0 first |
| Photos look muddy in black-ink print | The B/W proof loses the detail the photo is for | Grayscale with contrast set per photo in `bw`; check on the proof; drop the photo if the drawing already teaches it |
| EPUB size | Large JPEGs make the EPUB slow on readers | 400 KB per photo, 1600 px on the long side |
| Commons not reachable from sessions | Photo sourcing stalls | M1's GitHub Actions job, or the author |
| Physics drawn wrong | A picture teaches a wrong model | Every physics figure reviewed against the chapter's numbers and references; the Opus review checks them |
| Work on 2.2.0 and 2.3.0 overlaps | Merge conflicts in chapters being edited | 2.3.0 starts after the 2.2.0 release and its review are merged; prototypes touch only Chapters 8, 26 and 28 |

## 9. Decisions taken (2026-11-24)

1. The photo policy of section 3 is accepted; it supersedes the design plan's "no photos" rule,
   since the author asked for photos.
2. The plan is Theme I of a wider 2.3.0, not a book-only release. The table of
   `docs/ROADMAP-3.0.0.md`, section 5, gets a 2.3.0 row when `docs/ROADMAP-2.3.0.md` is drafted.
3. The five prototypes are kept as the model for the rest of the inventory.
