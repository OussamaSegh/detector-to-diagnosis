# Roadmap for release 2.0.0

Status: accepted. Written on 2026-11-08, while release 1.0.0 (the complete first edition) was
being prepared; the author answered the open questions of section 7 the same day (section 8),
and sections 3 and 4 follow those answers. Nothing here changes 1.0.0. Work starts after the tag
`book-v1.0.0`.

## 1. Where 1.0.0 leaves the project

- The book has 37 chapters in nine Parts and Appendix A (architecture). The 0.9.0 PDF is 679
  pages at 8.5 x 11 in. Amazon KDP's paperback limit is 828 pages, so a second edition has about
  150 pages of room in one volume.
- The text carries about 130 lines marked "verify:" and about 70 marked "assumption: confirm with
  team". The second kind is meant for the reader. Many of the first kind can be settled.
- The book's index is very small (noted by the Part V review and left for after 1.0.0).
- MiniDAQ has three open problem reports, two relevant to safety (`known-anomalies.md`):
  MDQ-PR-006 (a port fault noticed up to 20 ms late), MDQ-PR-007 (the sorter holds its last
  104 ns of singles until more data arrives) and MDQ-PR-009 (simulation code linked into the
  shipped server).
- The threat model (section 7, residual gaps) records three gaps: list-mode files (T-27),
  calibration tables (T-54) and QC reports are not signed. The firmware contract (ICD-FEB) has an
  open item for register map 1.2: a count of datagrams sent per run, the residual of ADR 0018.
- Process: the release checks take more than two hours and run in four parts because the
  container restarts; the perf workflow never runs (no self-hosted runner, CAPA-0004); CR-0025
  moved the gate to an interleaved comparison with the previous release from 1.0.0 on. The
  post-release VERSION bump has turned CI red more than once (`docs.version`).
- Smaller items left over: the simulator's "centre" spelling in code and options (an interface
  change), and two settings the repository owner has not decided (private vulnerability
  reporting, CodeQL code scanning).

## 2. What 2.0.0 is for

A major version means a second edition of the book and a breaking release of MiniDAQ. Proposed
goals:

1. **A better first-edition core**: every "verify:" settled or kept with a reason, a real index,
   errata from readers of 1.0.0 folded in, and an accessible EPUB.
2. **MiniDAQ without its known shortcuts**: the open problem reports and the threat model's gaps
   closed, with the breaking changes they need gathered into one major version.
3. **New material where the first edition is thin**: a short new Part on running the system over
   its life, within the page budget.
4. **A release process that a person can run** in one sitting, with fewer manual steps.
5. **A KDP second edition**, published as such.

## 3. Themes and scope

### Theme A: book quality (no new chapters)

- Settle each "verify:" line: check it against a primary source and remove the marker, or keep it
  and say what could not be checked. Track the count per chapter in a generated report, like
  `known-anomalies.md`, so the number only goes down.
- Build a real index: index terms in the Markdown sources, a check that every key term of the
  glossary is indexed, and a page budget for it (estimate 12 to 20 pages).
- Errata: a public errata page generated from a file in the repository, an issue template for
  readers, and patch releases (1.0.1, 1.0.2) for errata before 2.0.0.
- Cross references: a check that every "Chapter N" and "Exercise N.M" reference points to what it
  names (chapters were added and renumbered over the first edition).
- EPUB accessibility: alt text for every figure, accessibility metadata, EPUBCheck with its
  accessibility checks. The European Accessibility Act applies to e-books sold in the EU
  (verify: its scope for a self-published book).
- Refresh what aged: standards and guidance cited in Part III and Chapter 17 (for example the
  status of IEC 62304's second edition; verify: before writing), tool versions in the text.

### Theme B: MiniDAQ corrections (breaking changes allowed)

- MDQ-PR-009: a product build without the simulator, or a simulator refused outside service
  mode; the simulated-source tests keep their own build. Touches Chapters 6, 19 and 33.
- MDQ-PR-007: time markers from the readout flush the sorter (register map 1.2 with the
  firmware model, FakeBoard and the ICD).
- ICD open item: the datagrams-sent counter in register map 1.2, so that loss after the last
  datagram that arrived is found (closes the residual of ADR 0018).
- Threat model gaps T-27 and T-54: sign list-mode files and calibration tables (Ed25519, as for
  update bundles, so no new dependency), and the QC report with them.
- MDQ-PR-006: decide whether a faster fault reaction is worth its cost, or close it with the
  reasoning already in the release review.
- Interface clean-up held for a major version: "centre" to "center" in the simulator's options and
  fields, and any other renames found by a review of the control API (API 3.0, configuration
  schema 2.0, with a migration note and a test that 2.x requests are refused clearly).
- Toolchain: C++23 becomes the baseline, within what GCC 13 supports (section 8, answer 4; the
  `gcc-cxx23` preset already builds it). The text of Part I then shows `std::expected` and the
  other C++23 features where they replace hand-made code.

Every item goes through the usual route: change request, SRS rows, risk and threat model review,
tests with requirement tags, measurements, and the chapter text that describes it.

### Theme C: new material (Part X, about 3 chapters)

Candidates, to be ranked by the author (section 7). Each is a full chapter with code, tests,
exercises and a MiniDAQ milestone, so each is 25 to 35 pages.

1. **Clock distribution and time synchronization**: how a multi-board scanner keeps one time
   base, PTP (IEEE 1588) and dedicated clock links, what MiniDAQ's time markers need, and how to
   test skew. Fits Part II and Theme B's time markers.
2. **Maintenance and post-market**: the released product over years: problem reports from the
   field, patch releases under IEC 62304's maintenance process, SOUP that reaches end of life,
   telemetry and service logs, and how a change request is judged after release. MiniDAQ's own
   1.0 to 2.0 history is the worked example.
3. **Time of flight**: timing resolution from detector to reconstruction, what TOF changes in the
   list-mode format, the sorter and the projector, and its measurement. Deepens Parts II and VI.
4. **Scaling the acquisition**: from one acquisition PC to several, partitioning the coincidence
   search, and failure of one node. Large, and may need hardware the book cannot assume.
5. **GPU reconstruction**: offloading the projector. Needs a new dependency (CUDA or SYCL) and
   hardware that CI does not have; listed for completeness, not recommended.

Recommendation: 1, 2 and 3. Decided (section 8): 1, then 3, then 2, as Chapters 38 to 40;
4 and 5 are out of scope for 2.0.0. They use what MiniDAQ already has, need no new
dependency, and fit the page budget.

### Theme D: tooling and release process

- One command for the steps after a release commit: VERSION bump to the next `-dev`, SOUP review
  stubs, CHANGELOG section, Python package versions, edition page. Ends the recurring red
  `docs.version` after a release.
- Release checks that resume: each part records what passed, so a restarted machine continues
  instead of starting over; a generated release-record skeleton filled from `measurements/`.
- A stable performance machine for the gate, or a documented decision that CR-0025's interleaved
  comparison is the gate for good and `perf.yml`, the check that never runs behind CAPA-0004,
  is removed.
- Flaky timing tests (for example `FrameReader.CostIsLinear` under `ctest -j8`) into CAPA-0001's
  margin table or rewritten.
- An arm64 CI job (native or emulated) for readers on Apple silicon, who are told in "How to use
  this book" to use an arm64 Linux VM.

### Theme E: KDP second edition

- Edition page, copyright page and cover say "Second Edition"; the CHANGELOG lists what changed
  for readers of the first.
- Whether KDP treats it as an update of the existing title or a new title with its own ISBN
  depends on how much changed (verify: KDP's current rule on new editions before deciding).
- Page budget check in the KDP build stays at 828; if the new Part and the index do not fit, the
  options are a denser layout, moving Appendix A or the solutions online, or two volumes.

## 4. Order and milestones

The first edition was released one Part at a time, each with an independent review on an Opus
model. The same rhythm is kept.

| Milestone | Content | Exit criterion |
|---|---|---|
| 1.0.x | Errata from readers and from the 1.0.0 review, free | Patch release per batch of errata |
| 1.1.0 | Theme D first (post-release script, resumable checks), then Theme A; the errata window of four to six weeks runs alongside | Verify count down to the ones kept with a reason; index in the PDF; EPUBCheck clean with accessibility |
| 1.2.0 | Theme B, non-breaking items (register map 1.2, time markers, signing), with Chapter 38, clock distribution | Problem reports and threat gaps closed or re-decided; chapter recipe complete; release checks pass |
| 1.3.0 | Chapter 39, time of flight | Chapter recipe complete (code, tests, exercises, measurements, review) |
| 2.0.0-dev | Theme B, breaking items: control API 3.0, configuration schema 2.0, product build without the simulator, C++23 baseline | Earlier chapters, exercises and solutions updated to the new interface |
| 2.0.0-rc | Chapter 40, maintenance and post-market, with MiniDAQ's 1.0 to 2.0 history as its example; Theme E files | Chapter recipe complete; page count within the KDP limit |
| 2.0.0 | Second Edition: whole-book review, full release checks, KDP files | CI green on the release commit; tag `book-v2.0.0` |

Each release from 1.1.0 on gets the independent Opus review of the first edition before the
next one starts. Theme C starts only after the errata window, so feedback can still change the
Part X list.

Themes A and D come first because they make every later step cheaper and give readers of 1.0.0
something soon. Breaking changes are grouped in one step so the book's text about interfaces is
rewritten once.

## 5. Out of scope for 2.0.0

- A translation, a video course or a hardcover edition.
- New third-party dependencies, unless the author approves each one (standing rule).
- A real scanner's data or any manufacturer's product: the book stays generic.

## 6. Risks

| Risk | Effect | Response |
|---|---|---|
| Page budget: 679 pages plus about 100 for Part X and 15 for the index leaves little room | The KDP build fails above 828 pages | Count pages at every milestone; decide early between a denser layout, moving material online, or two volumes |
| Breaking changes ripple into earlier chapters, exercises and solutions | Starters or solutions fail; text describes the old interface | Group breaking changes in one milestone; run the whole ctest with exercises and the starters; grep the text for every renamed field |
| Exercise 18.5 records the SHA-256 of `readout_packet.hpp` | Any change to that header breaks the exercise until its mutation run is repeated | Plan the header change and the mutation run together |
| The reference machine's speed varies | Gate or soak fails for the machine, not the code | Rely on CR-0025's interleaved gate; record steal time; never benchmark while building |
| Standards and guidance change while the edition is written | Text is wrong at publication | Mark with "verify:" and check each again before 2.0.0 |
| Scope grows (Theme C candidates 4 and 5) | Edition never ships | Fix the Part X list at the start; anything else goes to a later edition |
| A new chapter needs a dependency | Wait for approval; SOUP work | Ask at the start of the chapter, with alternatives |
| Public repository | Personal information in a commit | Scan every diff, as for the first edition |

## 7. Open questions for the author

1. Is 2.0.0 a KDP second edition sold as a new edition, or a free update of the first? This
   decides how much must change and how it is labeled.
2. Which new chapters, in which order? The recommendation is clock distribution, maintenance and
   post-market, and time of flight.
3. Are breaking changes to MiniDAQ wanted (control API 3.0, configuration schema 2.0, product
   build without the simulator), or should 2.0.0 stay compatible?
4. Should C++23 become the baseline, with Part I updated to match?
5. If the book no longer fits 828 pages, which option: denser layout, material moved online, or
   two volumes?
6. Should scope wait for reader feedback on 1.0.0 (for example a few weeks of errata) before
   Theme C starts?

## 8. Answers (author, 2026-11-08)

1. **Second edition.** 2.0.0 is published on KDP as the Second Edition, as a new title with its
   own ISBN if KDP's rule on new editions requires it (verify: before publishing). The PDF and
   EPUB stay free on the download page. Errata for 1.0.0 ship free as 1.0.x.
2. **Part X: clock distribution, then time of flight, then maintenance and post-market.** Clock
   distribution goes with the time markers of 1.2.0, time of flight builds on it, and maintenance
   comes last because its worked example is MiniDAQ's 1.0 to 2.0 history. Scaling the
   acquisition and GPU reconstruction are out of scope for 2.0.0.
3. **Breaking changes are wanted**, grouped in the one 2.0.0-dev milestone: control API 3.0,
   configuration schema 2.0, a product build without the simulator (MDQ-PR-009), with a
   migration note and a test that 2.x requests are refused clearly.
4. **C++23 becomes the baseline, limited to what GCC 13 supports** (the compiler of Ubuntu
   24.04 and of the Mac VM set-up; Clang 18 with the same standard library must build it too):
   for example `std::expected`, `std::unreachable`, `if consteval` and the multidimensional
   subscript operator, not explicit object parameters ("deducing this"), `std::print`,
   `std::ranges::to` or modules, which need GCC 14 or later (verify: each against the
   compilers' C++23 status pages before Part I is changed). The text says what each feature
   replaces, for readers still on C++17 or C++20.
5. **Over 828 pages: a denser layout first, then Appendix A moved online, two volumes only as a
   last resort.** The solutions are already a separate book.
6. **Partly wait for feedback.** Themes D and A start right after 1.0.0. Theme C starts after
   about four to six weeks of errata from readers of 1.0.0, so that feedback can still change
   the Part X list.
