# Plan: a colorful, illustrated interior for *Detector to Diagnosis*

Status: PROPOSAL, waiting for the author's approval. Nothing in this plan is implemented.
Written 2026-11-09 against main 43f0332 (VERSION 1.0.1-dev, book 679 pages at 8.5 x 11 in,
solutions 208 pages). Request: "Make interior design more colorful, with as many
illustrations as possible. Plan first."

## 1. Where the interior is today

What the build does now (`book/build.sh`, pandoc 3.1 + XeLaTeX, `book` class, 10 pt, `openany`):

| Element | Today |
|---|---|
| Fonts | TeX Gyre Pagella (text), Heros (sans), Inconsolata (code) |
| Colors | five dark tones in `book/templates/book-header.tex` (`nlfblue` 1F4E79, `nlfred`, `nlfgreen`, `nlfgold`, `nlfgrey`); links in `nlfblue` |
| Chapter and Part openers | the `book` class defaults: black text, no color, no artwork |
| Callout boxes | six tcolorbox styles (`boxes.lua`): Why it matters, In a regulated product, Ask your team, Common mistakes, Note, MiniDAQ milestone; thin frame, 4 to 8% tint, no icon |
| Code | pandoc `tango` highlighting, no background, no frame |
| Tables | pandoc longtables, plain rules, no header tint |
| Figures | **25 in the whole book**: 11 matplotlib PNGs (`book/tools/figures/`, Chapters 5, 8 to 12) and 14 Graphviz diagrams (`diagrams.lua`) |
| EPUB | `templates/epub.css`, the same five tones; diagrams as SVG |
| Covers | new design on branch `claude/project-thread-itcwk8` (not yet on main): book = dark teal with teal 2DD4BF / gold FACC15 accents, solutions = deep violet with cyan 22D3EE / pink EC4899 accents |

Figures per Part today: I 10, II 9, III 5, IV 0, V 0, VI 0, VII 0, VIII 0, IX 0, appendix 1.
Chapters 1, 7 and 13 to 37 (except 14, 15, 17) have no figure at all, although Chapters 26
to 30 are about images. That gap is the main thing this plan fixes.

## 2. Constraints, checked

**Page count.** KDP's maximum is 828 pages for black and premium color ink, but **600 for
standard color**. The book is 679 pages now and the 2.0.0 roadmap adds a Part X (about 60
pages). This plan adds about 70 pages (section 6), so ~750 pages for 1.x and ~810 for 2.0.0:
inside 828, with little room left. The roadmap's answer 5 (denser layout first) stays the
fallback.

**Print cost on KDP** (Amazon.com, large trim, from KDP's printing cost help page, 2026-11-09):

| Ink | Fixed + per page | 679 pages | Allowed page range |
|---|---|---|---|
| Black | 1.00 + 0.017 USD | 12.54 USD | 110 to 828 |
| Standard color | 1.00 + 0.0402 USD | (28.30 USD) not allowed | 72 to **600** |
| Premium color | 1.00 + 0.08 USD | 55.32 USD | 42 to 828 |

(Amazon.de: black 11.61 EUR, premium color 49.30 EUR for 679 pages.) At a 60% royalty a
premium color paperback needs a list price above ~92 USD. Standard color is only possible
in two volumes of under 600 pages each (about 16 USD print cost per volume).
The author decided on 2026-11-09 not to upload to KDP for now, so print cost does not
block anything. The plan keeps every page **legible when printed in black ink**, so a black
and white paperback stays possible at 12.54 USD without a second design.

**Screen variants.** The screen PDF, the EPUB and the Boox Air 5C PDF are free and show
color. The Boox's Kaleido 3 color layer has a lower resolution (150 ppi color against 300
ppi black) and muted, darker colors: pale tints vanish, thin colored lines break up, colored
small text gets fuzzy. The `boox` build therefore gets its own color profile (section 3.4).

**Grayscale and color vision.** Color is never the only carrier of meaning: every callout has
an icon and a border style, every plotted series has a marker or dash pattern or a direct
label, every diagram category has a shape or fill pattern. Categorical colors come from a
color-blind safe set (Okabe-Ito based); images use perceptually uniform maps (viridis,
cividis) that stay monotone in gray.

**Accessibility.** Every figure carries alt text (separate from the caption), written for a
reader who cannot see it. Text in color meets WCAG 4.5:1 contrast. The EPUB keeps
accessibility metadata (roadmap Theme A).

**Build time.** Today a full `build.sh all both` takes about 2 minutes. 200+ figures must
not slow every build: each figure is built once into `book/build/figures/`, keyed by a hash
of its source and inputs (as `diagrams.lua` does for Graphviz), and TikZ is compiled
standalone, never inline. Target: cold figure build under 6 minutes, warm build +10 s.

**Licensing and generic rule.** All art is original: TikZ, matplotlib and Graphviz, drawn
from repository code and data. No stock images, no clip art, no icon fonts (icons are drawn
in TikZ), no traced figures from standards or papers ("after the figure in ..., in this
book's words", as Chapter 15 already does). No names, photos, places or company products;
no personal information anywhere in figure data or metadata.

**Dependencies.** matplotlib 3.11.2 and numpy are already in `analysis/requirements.lock`;
TikZ and Graphviz are already in the CI images. The only possible new tool is `dvisvgm` (TeX
Live, to turn TikZ into SVG for the EPUB); `pdftocairo` from poppler-utils is the fallback.
Either needs the author's approval as a build dependency (not SOUP: it never ships in MiniDAQ).

## 3. The color system

### 3.1 Identity

The book's base identity follows its cover: **deep teal** (0F766E) as the main accent and
**gold** (A16207 in print, FACC15 only on dark backgrounds) as the second. The solutions
manual follows its own cover: **violet** (6D28D9) with **cyan** (0E7490). Plots that show
intensities (sinograms, images, maps) use **viridis**, which runs dark violet, teal, yellow:
the two covers' colors, and monotone in gray.

### 3.2 One color per Part

Each Part gets a hue for its opener, running heads, chapter number badge, thumb tab, table
header tint and code-frame rule. All give white text at least 4.5:1 contrast (checked):

| Part | Topic | Color | White contrast | L* |
|---|---|---|---|---|
| I | Modern C++ | teal 0F766E | 5.5:1 | 44 |
| II | PET physics and DAQ | violet 6D28D9 | 7.1:1 | 37 |
| III | Standards | rose 9F1239 | 8.0:1 | 34 |
| IV | Testing and quality | blue 1D4ED8 | 6.7:1 | 39 |
| V | Hardware and networking | amber B45309 | 5.0:1 | 47 |
| VI | Calibration and reconstruction | magenta A21CAF | 6.3:1 | 41 |
| VII | Scientific Python and the build | green 15803D | 5.0:1 | 47 |
| VIII | MiniDAQ 1.0 | gold A16207 | 4.9:1 | 47 |
| IX | Hospital, team, tools | cyan 0E7490 | 5.4:1 | 45 |
| Appendix | Architecture | slate 475569 | 7.6:1 | 36 |

Part color is decoration and orientation only: the Part number is always printed next to it,
so gray print loses nothing.

### 3.3 Page elements

**Part openers.** A full page: a vertical color band in the Part color (inside the margins,
no bleed, see question 5), the Part number large, the title, a three-line abstract, the list
of chapters with page numbers, and a **pipeline map**: the MiniDAQ chain from detector to
diagnosis with this Part's stages lit up. One TikZ template, data from a small YAML file.

**Chapter openers.** A colored band with a large chapter number in a Part-colored badge, the
title, and a **chapter emblem**: a small original illustration of the chapter's central
idea (a ring of detectors for Chapter 8, a ring buffer for Chapter 3, a sinogram for
Chapter 12 ...), drawn in the Part color. Then "Learning objectives" and "Prerequisites and
estimated time" as a two-column card. `openany` stays, so openers add no blank pages.

**Running heads and thumb tabs.** Running heads get a thin Part-colored rule; outer edge
thumb tabs (a short colored block, stepping down per Part) make the Parts findable when the
book is closed or flipped on a tablet. Thumb tabs are skipped in the KDP interior unless
bleed is chosen.

**Callouts.** One family, seven kinds, each with a drawn icon, a left bar and a title strip.
Semantic colors are fixed across the book (not the Part color):

| Kind (source class) | Title | Color | Icon | Border in gray print |
|---|---|---|---|---|
| Key idea (`box-why`) | Why it matters | teal 0F766E | lightbulb | solid bar |
| Regulatory note (`box-regulated`) | In a regulated product | indigo 4338CA | section mark | double bar |
| Warning (`box-mistakes`) | Common mistakes | vermillion C2410C | warning triangle | thick bar + dashed frame |
| Exercise (new `box-exercise`) | Exercise n.m | green 15803D | pencil | solid bar, numbered tab |
| Ask your team (`box-askteam`) | Ask your team | violet 7E22CE | speech bubbles | dotted bar |
| MiniDAQ milestone (`box-milestone`) | MiniDAQ milestone | gold A16207 | flag | full frame |
| Note (`box-note`) | Note | slate 475569 | info circle | thin bar |

"Check yourself" questions get a numbered card style, "Summary" a tinted key-points box.
Exercise boxes need a small change to the chapter sources (wrap each exercise in
`::: box-exercise`); the filter numbers them.

**Code listings.** A custom pandoc highlight theme (`book/templates/d2d.theme`) replacing
`tango`: light warm-gray background (F6F7F9), a 2 pt left rule in the Part color, the listing
caption as a title strip with the file path, keyword colors tested at 4.5:1 on that
background and kept distinct in gray by weight (keywords bold, comments italic). Line numbers
on listings longer than 15 lines. Shell sessions get a dark variant (prompt in teal).

**Tables.** Header row tinted in the Part color (white bold text), very light zebra rows
(6% gray, which prints cleanly in black ink), booktabs-weight rules, numbers right-aligned.
Implemented with `xcolor[table]` in the header and a Lua filter, tested with longtable page
breaks.

**Figures.** Caption with a colored "Figure n.m" label, a light frame only for screenshots,
and the alt text kept in the source. Plots use one matplotlib style (`d2d.mplstyle`): Heros
font at the book's sizes, line widths at least 0.8 pt, no chart junk.

### 3.4 Three color profiles from one source

One file, `book/templates/palette.tex` (and `palette.css`, `d2d.mplstyle`, a Graphviz
attribute set), all generated from `book/tools/palette.json`:

- **screen** (PDF, EPUB): the colors above.
- **boox**: same hues, tints raised from 5 to 12%, lines at least 1 pt, colored text only at
  10 pt bold or larger, figures rendered for 150 ppi color.
- **print-bw** (optional KDP black ink interior): the same layout, tints in gray, Part color
  bands as 25% gray. Built and checked, uploaded only if the author ever decides to print.

## 4. The figure pipeline

- One directory per kind: `book/figures/tikz/`, `book/figures/plots/` (matplotlib scripts,
  moving the 9 from `book/tools/figures/`), `book/figures/dot/` (and the existing
  `docs/**.dot` stay where they are, included as today).
- **Generated from repository data wherever the data exists:** bit layouts from
  `docs/formats/`, the state machine from `docs/architecture/acquisition-states.json`,
  software items from `software-items.json`, the risk matrix from `hazards.json`, the trace
  graph from the SRS and tests, the CI gate graph from `ci.yml`, CMake target graphs from
  `cmake --graphviz`, sinograms, reconstructions, spectra and flood maps from the
  `measurements/chNN/*.py` scripts and MiniDAQ's own tools with fixed seeds. A figure then
  changes when the code changes, and it can never show what MiniDAQ does not do.
- `book/tools/figures.py` builds every figure into PDF (print) and SVG or PNG (EPUB), caching
  by hash, in parallel. `build.sh` calls it; the pages workflow caches `book/build/figures`.
- `book/tools/check_figures.py` (a ctest `book.figures` and part of the release checks):
  every figure has alt text and an id, is referenced in the text, comes from a source in the
  repository, uses only palette colors; the palette passes a contrast test, a gray-separation
  test (categorical L* steps), and a color-vision simulation test (deuteranopia, protanopia,
  tritanopia, minimum distance between categories).
- PNG only where vector is too heavy (flame graphs, dense scatter); 300 dpi print, 200 dpi
  EPUB.

## 5. Illustration inventory

Tools: **TZ** TikZ, **MP** matplotlib, **GV** Graphviz. **gen** means drawn from repository
data or by running MiniDAQ code. Effort per figure for a writing session, including checks
and alt text: **S** about 1 hour, **M** about 2.5 hours, **L** about 5 hours. "Restyle" means an
existing figure regenerated in the new palette. Every chapter also gets its opener emblem
(TZ, S), not listed per chapter.

### Front matter and Part openers

| # | Figure | Tool | Effort |
|---|---|---|---|
| F.1 | Book map: nine Parts as a path from the detector to the diagnosis, in Part colors | TZ | M |
| F.2 | MiniDAQ at a glance: the pipeline with the chapter that builds each stage | TZ gen (software-items.json) | M |
| F.3 | Reading paths: which Parts for which reader | TZ | S |
| P.1-9 | Part opener template with pipeline map (one template, nine data sets) | TZ gen | L once + S each |

### Part I: Modern, low-latency C++ (10 existing figures today in Part I, all Graphviz or PNG)

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 1 | Ownership and lifetime: owners, borrowers and views on a timeline | TZ | M |
| 1 | Strong types: which unit mix-ups the compiler stops | TZ | S |
| 1 | Error handling in real-time code: exception, `std::expected` or abort, as a decision tree | GV | S |
| 1 | Concepts: an event processor checked against its constraints | TZ | S |
| 1 | Undefined behavior: which sanitizer finds which kind (matrix) | TZ | S |
| 2 | Memory hierarchy latency ladder, log scale | MP | S |
| 2 | AoS and SoA in cache lines, hot and cold fields colored | TZ | M |
| 2 | The 64-bit event word, bit fields colored | TZ gen (docs/formats) | M |
| 2 | False sharing: two cores, one cache line | TZ | M |
| 2 | Allocation strategies: arena and pool on a timeline | TZ | S |
| 2 | Restyle the two existing diagrams | GV | S |
| 3 | Happens-before for release and acquire | TZ | M |
| 3 | SPSC ring buffer: head, tail, wrap | TZ | M |
| 3 | Batches and back-pressure with drop counters | TZ | M |
| 3 | Throughput against batch size | MP gen (benchmarks) | S |
| 3 | `std::jthread` and stop tokens: lifecycle | TZ | S |
| 3 | Restyle three existing diagrams | GV | S |
| 4 | CPU layout of the rt-fifo profile (replaces the Graphviz one) | TZ | S |
| 4 | Latency histogram and tail, normal against rt-fifo | MP gen (measurements/ch04) | S |
| 4 | Scheduling timeline: SCHED_FIFO against the normal scheduler | TZ | M |
| 4 | Page faults: locked and prefaulted memory | TZ | S |
| 4 | Clocks: TSC, CLOCK_MONOTONIC and a PTP offset | TZ | M |
| 5 | Restyle both flame graphs | MP gen (measurements/ch05) | S |
| 5 | Benchmark noise: repeated runs as a strip plot | MP gen | S |
| 5 | Branchy, branchless and SIMD speedups | MP gen | S |
| 5 | Performance budget waterfall: time per stage against the budget | MP gen (performance-budget.md) | M |
| 5 | The regression gate as a flow | GV | S |
| 6 | Ports and adapters (hexagonal view of MiniDAQ) | TZ | M |
| 6 | State machine, states colored by kind | GV gen (acquisition-states.json) | S |
| 6 | Configuration: from file to a validated object | GV | S |
| 6 | Control API: a sequence diagram of configure, start, stop | TZ | M |
| 6 | Logging off the hot path: the log ring | TZ | S |
| 6 | An ADR's life | GV | S |
| 7 | Defense in depth for a C++ binary | TZ | S |
| 7 | Static analysis findings, by tool and outcome | MP gen (measurements/ch07) | S |
| 7 | Fuzzing coverage over time | MP gen (measurements/ch07) | S |
| 7 | Hardening flags and what each one blocks | TZ | S |
| 7 | SBOM as a dependency graph | GV gen (CycloneDX file) | S |

### Part II: PET physics and data acquisition

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 8 | From a decay to two 511 keV photons (positron range, non-collinearity) | TZ | M |
| 8 | Photoelectric effect and Compton scattering | TZ | M |
| 8 | The detector chain: crystal, photosensor, ASIC, FPGA | TZ | M |
| 8 | True, scattered, random and multiple coincidences in a ring | TZ | M |
| 8 | The resolution budget as stacked bars | MP gen (simulator parameters) | S |
| 8 | A brain PET geometry and its field of view | TZ | M |
| 8 | Simulated annihilations in the ring, colored by event type | MP gen (simulator) | M |
| 8 | Restyle the energy spectrum | MP gen | S |
| 9 | A pulse: leading edge, constant fraction and time over threshold | MP | M |
| 9 | Coarse and fine time stamps on a clock | TZ | M |
| 9 | The event word specification as a bit diagram | TZ gen (shared with 2) | S |
| 9 | Failure modes of a readout link | GV | S |
| 9 | A UDP datagram of MiniDAQ events | TZ gen | S |
| 9 | Restyle time walk and components | MP, GV | S |
| 10 | The singles stream with windows opening | TZ | M |
| 10 | Fixed and per-single windows | TZ | S |
| 10 | Geometry acceptance: the fan of allowed lines of response | TZ gen | M |
| 10 | Merging boards: a k-way merge with a heap | TZ | M |
| 10 | Randoms by the delayed window | TZ | S |
| 10 | Sorter throughput against singles rate | MP gen (measurements/ch10) | S |
| 10 | Restyle the two existing plots | MP | S |
| 11 | Paralyzable and non-paralyzable dead time on a timeline | TZ | M |
| 11 | Pile-up of two pulses | MP | S |
| 11 | The NEMA NU 2 phantom and source | TZ | M |
| 11 | End-to-end throughput budget, stage by stage | MP gen | M |
| 11 | Restyle the three existing plots | MP | S |
| 12 | The 16-byte list-mode record | TZ gen | S |
| 12 | From a line of response to (s, phi): the sinogram construction | TZ | M |
| 12 | Ring differences and the Michelogram | TZ | M |
| 12 | Crash-safe writing: write, fsync, rename | TZ | S |
| 12 | File formats compared | TZ | S |
| 12 | The patient-data boundary | TZ | S |
| 12 | Restyle sinograms (viridis) and writer plot | MP gen | S |

### Part III: Medical device software standards

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 13 | Restyle the standards map | GV gen | S |
| 13 | EU MDR route to the CE mark for this device class | GV | M |
| 13 | FDA routes: 510(k), De Novo, PMA | GV | S |
| 13 | Timeline of the regulations and standard editions | TZ | M |
| 13 | The post-market loop | TZ | S |
| 13 | Who regulates what: EU, US, Switzerland as blocks | TZ | S |
| 14 | IEC 62304 processes as a V, mapped to MiniDAQ's files | TZ | M |
| 14 | Restyle the classification diagram | GV | S |
| 14 | A SOUP item's life | GV | S |
| 14 | Traceability: requirements to tests, as a coverage heat map | MP gen (SRS, tests) | M |
| 14 | A sprint inside the 62304 activities | TZ | M |
| 14 | Problem resolution flow | GV | S |
| 15 | The risk management process | TZ | S |
| 15 | Risk matrix before and after controls | MP gen (hazards.json) | M |
| 15 | FMEA: risk priorities as a Pareto chart | MP gen (fmea-sorter.json) | S |
| 15 | The order of risk controls | TZ | S |
| 15 | Restyle hazard chain and fault tree | GV gen | S |
| 16 | Design controls as a waterfall | TZ | M |
| 16 | The design and development file as a tree | GV gen (design-file.json) | M |
| 16 | Change control with impact analysis | GV | S |
| 16 | A CAPA's states | GV gen (capa records) | S |
| 16 | Verification and validation | TZ | S |
| 16 | An audit's timeline | TZ | S |
| 17 | Restyle the data flow diagram, trust boundaries in color | GV gen | S |
| 17 | STRIDE by element, as a heat map | MP gen (threat model) | M |
| 17 | The authenticated control API: handshake sequence | TZ | M |
| 17 | Vulnerability management: SBOM, advisory, triage | GV | S |
| 17 | IEC 81001-5-1 activities in the life cycle | TZ | S |

### Part IV: Testing, verification and quality

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 18 | MiniDAQ's test pyramid with real counts | TZ gen (ctest labels) | S |
| 18 | Seams: ports and fakes | TZ | S |
| 18 | A property-based test shrinking a failure | TZ | M |
| 18 | Coverage per software item | MP gen (measurements/ch18) | S |
| 18 | Requirement tags from test to SRS | GV | S |
| 19 | Test levels and their environments | TZ | S |
| 19 | Golden data: how it is made and checked | GV | S |
| 19 | A soak: rate and memory over hours | MP gen (measurements/ch19/soak) | S |
| 19 | A hardware-in-the-loop bench | TZ | M |
| 19 | The anatomy of a test report | TZ | S |
| 20 | The pipeline's gates | GV gen (ci.yml) | M |
| 20 | Can each gate fail: the planted-fault matrix | TZ | S |
| 20 | Two builds, one hash | TZ | S |
| 20 | The release package | TZ | S |
| 20 | Benchmarks on shared machines: the spread | MP gen (measurements/ch20) | S |
| 21 | A review's flow | GV | S |
| 21 | Reading a crash: an annotated backtrace | TZ | M |
| 21 | The flight recorder ring | TZ | S |
| 21 | Root cause analysis: a cause tree | TZ | M |
| 21 | `git bisect` as a binary search | TZ | S |

### Part V: Hardware, embedded Linux and networking

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 22 | How Linux gives a program its hardware: the layers | TZ | M |
| 22 | A register map, fields colored | TZ gen (register spec) | M |
| 22 | Slow-control buses and sensors | TZ | S |
| 22 | Gain against temperature, with and without the loop | MP gen | M |
| 22 | Timeouts and retries as a state machine | GV | S |
| 23 | The receive path from the wire to `read()` | TZ | M |
| 23 | Where packets are dropped, with counters | MP gen (measurements/ch23) | S |
| 23 | Socket buffer size against drops | MP gen | S |
| 23 | The cost of receiving, per packet | MP gen | S |
| 23 | Kernel path and kernel bypass | TZ | S |
| 24 | An FPGA for a software engineer | TZ | M |
| 24 | valid/ready handshake timing | TZ | M |
| 24 | Crossing clock domains with an asynchronous FIFO | TZ | M |
| 24 | A FIFO's fill level through a burst | MP gen | S |
| 24 | A run's edges: the start and stop sequence | TZ gen (measurements/ch24) | M |
| 25 | The platform's layers | TZ | S |
| 25 | Service dependencies | GV gen (unit files) | S |
| 25 | The watchdog's heartbeat | TZ | S |
| 25 | A/B update with rollback | GV | S |
| 25 | Least privilege: what the service may do | TZ | S |

### Part VI: Calibration, corrections and reconstruction

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 26 | Energy spectra per crystal, before and after calibration | MP gen (measurements/ch26) | M |
| 26 | Flood map: crystal identification | MP gen | M |
| 26 | The calibration table | TZ | S |
| 26 | The calibration procedure | GV | S |
| 26 | Gain drift watched during a run | MP gen | S |
| 27 | From counts to activity: the correction chain | TZ | M |
| 27 | Prompts, delayed and randoms sinograms | MP gen (measurements/ch27) | M |
| 27 | The normalization sinogram | MP gen | S |
| 27 | Attenuation map and correction factors | MP gen | M |
| 27 | The scatter tail fit | MP gen | M |
| 27 | Decay and dead-time factors over a run | MP gen | S |
| 27 | One image without and with each correction | MP gen | M |
| 28 | A line of response through the pixel grid | TZ | M |
| 28 | Projector and adjoint | TZ | S |
| 28 | The MLEM loop | TZ | S |
| 28 | OSEM subsets | TZ | S |
| 28 | A phantom, iteration by iteration (montage) | MP gen (measurements/ch28) | M |
| 28 | Log-likelihood against iterations | MP gen | S |
| 28 | Sinogram and image side by side | MP gen | S |
| 29 | The binding boundary: a NumPy array and a C++ span | TZ | M |
| 29 | One test suite for both sides | TZ | S |
| 29 | Python against C++ projector speed | MP gen (measurements/ch29) | S |
| 29 | The cost of crossing the boundary against batch size | MP gen | S |
| 30 | A point source's profile and its FWHM | MP gen (measurements/ch30) | M |
| 30 | Regions of interest on the phantom | MP gen | M |
| 30 | Contrast recovery against noise, by iteration | MP gen | M |
| 30 | Repeatability across seeds | MP gen | S |
| 30 | How the region decides the number | MP gen | S |

### Part VII: Scientific Python and the build

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 31 | The analysis package's modules | GV gen | S |
| 31 | Reading a run in chunks: memory over time | MP gen | S |
| 31 | A Poisson fit and its residuals | MP gen (measurements/ch31) | S |
| 31 | The time difference that does not fold | MP gen | M |
| 31 | Is the rate constant: a control chart | MP gen | S |
| 31 | A page of the QC report | MP gen | M |
| 31 | Provenance as a graph | GV gen | S |
| 32 | Targets and what they pass on | GV gen (cmake --graphviz) | M |
| 32 | Presets and their inheritance | GV gen (CMakePresets.json) | S |
| 32 | The pinned dependency tree | GV gen | S |
| 32 | Where the build time goes | MP gen (measurements/ch32) | S |
| 32 | An installed package's layout | TZ | S |

### Part VIII: MiniDAQ 1.0

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 33 | The run from decays to an image, with the count at every stage (two-page spread) | TZ gen (measurements/ch33/e2e) | L |
| 33 | Every count between stages, as a flow diagram | MP gen | M |
| 33 | The acceptance specification as a status matrix | TZ gen | S |
| 33 | A damaged run against a clean one | MP gen | S |
| 33 | Flatness | MP gen (measurements/ch33) | S |
| 34 | The first 90 days as a timeline | TZ | M |
| 34 | The order to read the documents | GV | S |
| 34 | The codebase as a treemap of lines by component | MP gen (repository) | M |
| 34 | Files that change together, as a heat map | MP gen (git history) | M |
| 34 | Characterization tests around a change | TZ | S |

### Part IX: The hospital, the team and the tools

| Ch | Figures to add | Tool | Effort |
|---|---|---|---|
| 35 | What leaves the scanner and where it goes | TZ | S |
| 35 | A data element byte by byte: tag, VR, length, value | TZ gen (measurements/ch35) | M |
| 35 | The PET Image object's modules | GV | S |
| 35 | Patient coordinates: image position and orientation | TZ | M |
| 35 | Patient, study, series, instance | TZ | S |
| 35 | An association and a C-STORE | TZ | M |
| 35 | The outbox's states | GV | S |
| 36 | A commit, its tree and its parents | TZ | M |
| 36 | Shapes of the work: branch strategies | TZ | M |
| 36 | Merge, rebase and squash side by side | TZ | M |
| 36 | A commit message's anatomy | TZ | S |
| 36 | Releases on the history (from the repository's tags) | MP gen | M |
| 36 | Identity, signatures and who may push | TZ | S |
| 37 | An assistant's loop in a repository | TZ | S |
| 37 | Where it helps and where it does not | TZ | S |
| 37 | What is in the context | TZ | S |
| 37 | Small steps, each verified | TZ | S |
| 37 | Which check found which mistake | MP gen (measurements/ch37) | S |
| 37 | The assistant in the threat model | GV | S |

### Appendix A and the solutions manual

| Where | Figures to add | Tool | Effort |
|---|---|---|---|
| App. A | Software items (restyle) | GV gen | S |
| App. A | Interfaces as a matrix | TZ gen | M |
| App. A | Threads and queues: the concurrency architecture | TZ | M |
| App. A | SOUP boundaries | GV gen | S |
| App. A | Tradeoffs at a glance | TZ | S |
| Solutions | About one figure per chapter where the answer is a plot or a layout (~30), mostly the reader's expected exercise output | MP gen, TZ | S each |

### Totals

| | Count | Effort (hours) |
|---|---|---|
| New chapter figures | ~180 | ~330 |
| Restyled existing figures | 25 | ~15 |
| Chapter emblems | 37 | ~37 |
| Front matter and Part openers | 3 + 9 | ~15 |
| Solutions figures | ~30 | ~30 |
| Foundation (palette, openers, callouts, code, tables, pipeline, checks) | | ~30 |
| **All** | **~285** | **~460** |

From ~25 figures to ~230 in the book: about 6 per chapter, more where the subject is
visual (Parts II and VI: 7 to 8), fewer where it is process (Part IV: 5).

## 6. Page budget

| Item | Pages |
|---|---|
| 180 figures at ~0.33 page on average (many sit beside text or two to a row) | +60 |
| Chapter openers (band and emblem in the space the title already uses) | +6 |
| Exercise boxes, table and code padding | +5 |
| Front matter figures | +2 |
| **Book** | **~750** (from 679) |
| Solutions | ~225 (from 208) |

With the 2.0.0 Part X (~60 pages) the book reaches ~810 of 828. If that is too tight, in
this order: two figures per row where they pair naturally, 9.5 pt code, then the roadmap's
denser layout.

## 7. Phasing

| Phase | Work | Ships in |
|---|---|---|
| 0 Foundation | palette.json and its four outputs, Part and chapter openers, callouts with icons, `box-exercise`, code theme, tables, figure pipeline and cache, `check_figures.py`, the three profiles | preview PDFs only |
| 1 Pilot: Part II | all Part II figures (~35) and openers; the author reviews screen PDF, Boox PDF, EPUB and a black ink proof | preview PDFs only |
| 2 Rollout A | Parts VI and VIII (the most visual) and Part I | 1.1.0-dev |
| 3 Rollout B | Parts III, IV, V, VII, IX, Appendix A, solutions | 1.1.0-dev |
| 4 Release | release checks, record, tag | **1.1.0** |
| 5 2.0.0 | Part X written in the new style from the start; denser layout if the page budget needs it | 2.0.0 |

One release (1.1.0) for the whole redesign keeps the release overhead (release checks, SOUP
review dated for the minor version, the record) to once, and the reader never gets a book
half old, half new. Each phase is its own thread on an Opus model; each Part is its own
commit series, verified with the full build (0 overfull boxes, EPUBCheck) before pushing.
A minor version (1.1.0) fits: the text and MiniDAQ do not change, only the presentation.

Relation to the 2.0.0 roadmap (branches `claude/project-thread-k78nqm`/`osszm6`, not yet on
main): this plan becomes a new theme (F, interior design) or an item of Theme A (book
quality). The roadmap says Themes A and D start at once and Part X waits for errata; the
redesign fits that window, and Part X then needs no restyling later. Once the roadmap
branch is rebased onto main, its section on themes gets a line pointing here.

## 8. Risks

- **Grayscale print**: if a black ink paperback ever comes, Part colors become gray
  (planned); every figure is proofed in gray by `check_figures.py` and by eye in the pilot.
- **Boox rendering**: the pilot includes a Boox PDF checked on the device by the author;
  the profile's tints and line widths may need one adjustment round.
- **Wrong figures**: a figure drawn by hand can claim what the code does not do. Generated
  figures avoid this; hand-drawn ones (TikZ) get the same per-chapter fact check as the
  text.
- **Build time and CI**: the cache keeps warm builds fast; the pages workflow caches the
  figures directory between runs.
- **Longtable coloring**: `\rowcolors` and longtable page breaks have known interactions;
  tested in Phase 0 on the longest tables (Chapters 14 and 33).

## 9. Questions for the author

1. **Print**: keep the paperback question open and design black-ink-safe (recommended), or
   plan a premium color paperback (~55 USD print cost), or a two-volume standard color one?
2. **Density**: about 6 figures per chapter (this plan, ~750 pages), or "every section gets
   one" (~10 per chapter, ~800 pages, which leaves no room for Part X within 828)?
3. **Part colors**: one color per Part (this plan), or the whole book in teal and gold like
   the cover, with color only in figures and callouts?
4. **Chapter emblems**: a small original illustration on every chapter opener, or a cleaner
   opener with only the number and the band?
5. **Bleed**: color bands and thumb tabs to the page edge (needs a bleed interior and changes
   the margins), or everything inside the margins (recommended)?
6. **Release**: the whole redesign as 1.1.0 (recommended), or a release after each Part?
7. **Pilot Part**: Part II (recommended: physics, the most to draw, figures already there to
   compare), or another?
8. **Covers**: the new covers (branch `claude/project-thread-itcwk8`) are still waiting for
   your OK; the palette follows them, so approving them first fixes the base colors.
