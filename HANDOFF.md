# Handoff: how to continue this work

This file is for an agent (or a person) who has to pick up the generation of *Detector to
Diagnosis* (formerly titled after a product) and MiniDAQ if the current session is lost. Read it fully before you change
anything. It is kept up to date with every chapter and every release. The CHANGELOG and the git
log record what changed. This file records why, how, and what is left.

Last updated: 2026-11-11: the solutions manual cover is Inverse (the slice printed on
paper, SOLUTIONS / MANUAL). The book's cover stays the Plate design. The chapter opener
is the Atlas head. VERSION is still 1.1.1-dev. Release 1.1.0 was 2026-11-10 (tag
book-v1.1.0 on 19c6364); the second full review (PR #9) is merged on main after it.

## Start here (after release 1.1.0)

**Release 1.1.0 (2026-11-10): the illustrated interior.** Internal audit before the checks
(`docs/regulatory/qms/internal-audit-2026-11-10.md`, no nonconformity), fifteen controlled
documents approved by the software lead at their content (MDQ-PR-066 closed; `tools/design_file.py`
now refuses a "draft" status in a release VERSION), SOUP list v22 (review for 1.1) and v23,
release checks in four parts on 9b9e96d (`measurements/release-1.1.0/`, ACC-04 179 of 180
intervals: passed), reproducible build checked, CAPA-0002 closed (effective), release record
`docs/regulatory/releases/1.1.0.md`, tag book-v1.1.0 through `.github/tags.txt`. Open: MDQ-PR-006,
007, 009, 064. No CAPA open.

**Chapter opener (2026-11-11), from the Atlas direction in the design proposals.** Only the
opener changed. The head is a Part-colored kicker (`PART III / CHAPTER 14`), the title in EB
Garamond, the clause after a colon set as the subtitle, and a Part-colored rule. "Why it
matters" is a sand card with a Part-colored bar; its label stays the text ink, because Part I's
teal is 4.2:1 on that sand and Part VIII's gold is 3.8:1, under 4.5:1. "Learning objectives"
and "Prerequisites and estimated time" are small tracked headings in the Part color, and their
old cards are gone. Body text, the other call-outs, listings, figures, tables and Part
openers are the 1.1.0 design. The cover is the Plate design, below. The chapter
emblems are no longer drawn (`\dsetemblem` remains, so the filter still calls it). EB
Garamond and Inter are installed in the `pages` and `kdp` workflows. Screen PDF: 750 pages before and after (the cover is page 1),
0 overfull boxes. Boox PDF: 1024 pages, 0 overfull boxes. Black-ink interior: 749 pages (no
cover), 0 overfull boxes, every font embedded.

**Cover (2026-11-11): the Plate design, chosen from the cover proposals.** The front is the
MLEM reconstruction, edge to edge, above an ink band (`#100E0C`). In the band, 0.58 in inside
the trim: a tracked kicker (PET DATA ACQUISITION), the title in EB
Garamond with *to* in gold italic, the subtitle in Inter, and the author at the lower right. A
gold rule separates the picture from the band. The spine is the same ink, so the back meets it
without a seam; the title reads upward, with a short gold tick at the head and the foot. The
back is that ink, the blurb, and the four steps (singles, coincidences, sinogram, image) in the
plate colors. The barcode area stays empty. The solutions manual does not use this
artwork; its cover is Inverse, next. `cover.tex` sets the type; `cover_art.py`
writes the JPEGs. Screen, EPUB and download-page covers are this front. The KDP wrap is back,
spine and front at the interior's page count (white paper, 0.002252 in per page). The black-ink
interior is 749 pages, so the book's spine is 1.6867 in and the wrap is 18.937 x 11.250 in.

**Solutions cover (2026-11-11): Inverse, chosen from the solutions cover proposals.** The
book stays Plate. The solutions front is the same reconstruction printed in Part I teal and
ink on paper (`#F6F1E7`), above a paper band 4.15 in tall. In the band, 0.58 in inside the
trim: SOLUTIONS in EB Garamond Bold, MANUAL in teal, the line "Companion to Detector to
Diagnosis", the series title, and the author. The spine and the back are the same paper, so
they meet without a seam. The back keeps the blurb and the four steps, drawn in teal and ink,
and the barcode area stays empty. The download page takes its JPEG from this front, as it
does for the book. The KDP black-ink profile replaces each color with the gray of its
lightness: the slice runs from paper to near-black, and the type is ink (16:1 on the paper)
and teal (4.9:1), so the cover still reads in gray. `cover_art.py` writes
`cover-{front,back}-solutions.jpg`; the book's JPEGs are untouched.

**Interior redesign for 1.1.0: complete, on main** (plan `book/docs/PLAN-interior-design.md`,
approved by the user: "Go implement", then "Review and finish everything"). The palette
(`book/tools/palette.json`, one color per Part, profiles screen, boox and bw; `BOOK_INK=bw` stays
the KDP default), the page design (`book/templates/book-header.tex`, `book/filters/design.lua`:
chapter heads with emblems, Part openers with the MiniDAQ map, call-out cards, thumb tabs), the
EPUB colors (`palette.py css`) and the figure pipeline (`book/tools/figures.py`, `{.figure}`
blocks, cached builds, ctest `book.figures`). 231 figures over every chapter and Appendix A
(1.0.0 had 25), each with alt text and a reference; plots read the measurement files they show
(Chapter 37 added `measurements/ch37/mutants.py` for its kill matrix). Appendix figures use the
appendix color (part "A"). Builds on 2026-11-10: screen PDF 745 pages, Boox 1017, KDP bw
interior 744, 0 overfull boxes, every image at 300 ppi or more. Adding a figure: write the
source under `book/figures/{tikz,plots}/<chapter>/`, insert a `{.figure}` block after the
paragraph that refers to it as `Figure [](#fig-id)`, run `figures.py check`.

State on 2026-11-09: the book is complete. Release 1.0.0 (the packaged book, Parts I to IX and
Appendix A) was released on 2026-11-08: release record `docs/regulatory/releases/1.0.0.md` on
33aa5ba, release checks in four parts on 517cd49 (`measurements/release-1.0.0/`), tag
book-v1.0.0 on 33aa5ba through `.github/tags.txt`. The packaged files (book and solutions PDF
and EPUB, KDP interiors and covers, the zip, the SBOM, the record, the CHANGELOG) are kept
outside the repository, in the project's release folder for v1.0.0. Tags ch00 to ch37 and
book-v0.1.0 to book-v1.0.0 are on GitHub; fetch them with
`git fetch --force origin 'refs/tags/*:refs/tags/*'`.

What 1.0.0 decided and found:

- CR-0025 (approved by the user, implemented in df19e58): the release checks' performance gate
  compares the candidate with the previous release, both built on the reference machine and run
  interleaved (`tools/perf_ab.sh`, five rounds, in part 3; the base is the newest `book-v*` tag,
  or `PERF_BASE`); `benchmarks/baseline/book-vm.json` is kept as the trend (`perf-trend.txt`, not
  judged). SRS-PERF-022 holds in at least 99% of the 10 s intervals (SRS version 27, ACC-04 with
  `share` 0.99); `tools/soak.py` counts the intervals above the limit and records the steal time.
- MDQ-PR-063 (closed): `tools/req_baseline.py` let a change request accepted before the
  baseline authorize later changes; a baseline now lists the requests already accepted
  (`requests`). The baseline is at SRS version 27, release 1.0.0.
- ACC-04 failed at 1.0.0 (178 of 180 intervals within 10 ms, 179 needed); the programs of 0.9.0
  gave the same that evening. The user approved releasing with a recorded deviation, and
  MDQ-PR-064 (open) is to find the cause with a finer measure (per-thread schedstat) before the
  limit is judged again. Every other check passed, the gate against 0.9.0 among them.
- SOUP list version 21: the review for release 1.0.0. The next minor version needs a new review
  dated for it (`docs.soup`).

Independent review of 1.0.0 (2026-11-09, review branch claude/project-thread-p4842k): set
VERSION 1.0.1-dev (main was red on `docs.version` after the release: the commit after a release
must set the next -dev version), corrected two stale listing ranges in solutions Chapter 1 and
the benchmark names in the 0.9.0 and 1.0.0 records, and explained the *verify:* marker in How
to use this book. Its open findings were closed on main the same day (thread "Finish open
review items"):

- CAPA-0002's effectiveness check, due at 0.4.0 and never made, was made by an internal audit
  (`docs/regulatory/qms/internal-audit-2026-11-09.md`): not effective, new check due at release
  1.1.0. `tools/check_capa.py` now fails on an overdue check and on a newest release record that
  leaves out an open CAPA (MDQ-PR-065, closed); SDP version 15, section 8 item 9: an internal
  audit before each minor release, cited by its record. MDQ-PR-066 (closed at 1.1.0): fifteen
  controlled documents carried "Status: draft for review"; the software lead approved each at
  release 1.1.0.
- The 133 printed *verify:* markers are gone (Parts I to IX, solutions Chapter 5): citations
  completed from PubMed, IEEE and JACoW records, clause numbers given, "at the time of writing"
  for what may change, or the sentence says what was not checked. The exercise NOTES files keep
  theirs (they are not printed).
- The index: `book/index-terms.txt` (about 560 phrases) and `book/filters/index-terms.lua` index
  the first use of each term in every chapter and the appendix; about 400 main entries and 90
  subentries (was 32). Test `book.index` (`book/tools/index_terms.py`) refuses a dead or
  malformed entry. Add a term there when a chapter introduces one; `[text]{.idx}` spans still
  work and must use the same key.
- The 2.0.0 roadmap (`docs/ROADMAP-2.0.0.md`, with the author's answers in section 8) is on main,
  rebased from claude/project-thread-k78nqm. The branches k78nqm and osszm6 are now stale (a
  force push to update them was refused by the session's permissions); delete them on GitHub.

Second full review (2026-11-10, PR #9, branch claude/project-thread-azh4pv, merged LOCALLY on main
after release 1.1.0, so its fixes go out with the next release):
debug preset 926 of 926 tests, every starter fails and none hangs, the book and the solutions
build (685 and 209 pages, 0 overfull hboxes), Chapter 8's table reproduces from
`minidaq_sim --activity 5e6 --seconds 1 --window 4000`. Fixed: the install line of
How to use this book and the README lacked python3-scipy and python3-matplotlib, so `system.e2e`
failed for a new reader (the other Python tests skip without their packages); Chapter 4 said a
new thread's stack still faults under `mlockall(MCL_FUTURE)` (it does not: measured 0 faults; the
main thread's stack and a refused lock are the real gaps); class A in Chapter 14 follows
Amendment 1; stale statements that the book prints *verify* marks or keeps every measured number
under `measurements/` (Chapters 2, 3 and 8 have no folder there). The two items it left for
the author were decided by the author on 2026-11-10 and done on main: MDQ-PR-067, the license
split (code MIT; book text, figures with their sources, covers and design notes all rights
reserved, `book/LICENSE`, README and copyright page agree); MDQ-PR-068, `measurements/ch08/`
reproduces Chapter 8's rate table exactly, `measurements/ch02/` and `ch03/` hold a rerun of the
chapters' benchmarks built at their tags (the first runs were never kept), each README with the
printed values beside the rerun. Still open: the SRS header reads "MiniDAQ 1.0.0-dev".


Next work: none is asked. VERSION is 1.1.1-dev after release 1.1.0. A next minor version (1.2.0
or 2.0.0, see the roadmap) bumps the Python package versions with it, adds a dated SOUP review
for it, holds the internal audit before its release checks, and takes up MDQ-PR-064. A PR opened by a session starts no ci or gates
run: verify a review branch locally before merging, and merge LOCALLY with the noreply identity.
Next free numbers: MDQ-PR-069, CR-0026, ADR 0033, TL-49. A commit message has ONE trailer
block: `Review:` directly above `Co-Authored-By:`, no blank line between (the commit-msg hook
refuses otherwise).

Fresh container: install the apt packages of `ci.yml` and `pages.yml`, then
`python3 -m pip install --ignore-installed --no-deps -r analysis/requirements.lock` (python3 is
3.13 in /usr/local; without it `system.e2e` fails), `git fetch --unshallow`,
`git config core.hooksPath tools/hooks`, `sysctl -w net.core.rmem_max=4194304`. EPUBCheck for
`book/build.sh kdp`: github.com is blocked; take `epubcheck-5.1.0.jar` and its `pom.xml` from
repo1.maven.org, `mvn dependency:copy-dependencies -DoutputDirectory=lib`, and set
`EPUBCHECK_JAR` to the jar next to `lib/`.

Rules that bit in Parts VII and VIII: run the WHOLE ctest (exercises too) before every commit;
after a VERSION bump re-run cmake in the build directory before ctest (cmake.consumer reads
VERSION at configure time); test build changes in a FRESH build directory; the release checks
build starters with Ninja. Never build or test while part 2's benchmarks or part 3 (gate, soak)
run. The book threads run on an Opus model, never Fable.

## 1. The goal

The reader is a C++ engineer who builds or leads the data acquisition software of a PET scanner. This repository holds two things:

- **The book** *Detector to Diagnosis: Building Regulated Medical Imaging Software in Modern C++*
  (`book/`, outputs `detector-to-diagnosis-*`). It has 34 chapters in Parts I to VIII, plus a
  new Part IX and an architecture appendix (section 6). It is a standalone technical book,
  8.5 x 11 in, publishable on Amazon KDP.
- **MiniDAQ**, the running project: a simulated PET data acquisition system with its regulated
  software file. The code is in `minidaq/`, with `exercises/`, `docs/`, `tools/`, `fuzz/`,
  `benchmarks/` and `python/`.

The book is released one Part at a time:

| Version | Content |
|---|---|
| 0.1.0 | Part I |
| 0.2.0 | Part II |
| 0.3.0 | Part III |
| 0.4.0 | Part IV, Chapters 18 to 21 |
| 0.5.0 | Part V, Chapters 22 to 25 |
| 0.6.0 | Part VI, Chapters 26 to 30 |
| 0.7.0 | Part VII, Chapters 31 and 32 |
| 0.8.0 | Part VIII, Chapters 33 and 34 |
| 0.9.0 | Part IX, Chapters 35 to 37, and Appendix A |
| 1.0.0 | The complete, packaged book |

The chapter-by-chapter outline (scope, sections, exercises and milestone of every chapter) is
in the plan document: https://claude.ai/artifact/S5ee4ACY7Big7ghVJQ8Md7 (Claude Doc). The
ranked skills document is at https://claude.ai/artifact/S92yccm1t8aPP1Rk75Rahf.

## 2. The user's rules (all of them apply to every chapter)

Quality:

- "I want top quality": depth and correctness come before speed.
- Every chapter gets a full review.
- Every number in the text is checked against code or a measurement in `measurements/`.
- GitHub CI and static analysis are run, not only the local tests.

Accuracy:

- Never invent a reference or a number.
- Do not print "verify:" markers (resolved after the 1.0.0 review, 2026-11-09): give the
  source, write "at the time of writing" for what may change, or say in the sentence what the
  book did not check.
- Mark a product-specific number with "assumption: confirm with team".
- Never reproduce ISO or IEC text.

Style:

- American spelling, second person.
- No em-dashes.
- Prose lines wrapped at 100 characters.
- Never write "the plan" in the book: readers have no plan.
- A chapter gives only its reading, exercise and milestone hours; no weeks, no schedule.
- New figures render at dpi=300; a wide table's column widths sum to 1 or less.

Each chapter follows this template:

1. box-why, a day-in-the-life opening, learning objectives, and prerequisites with time.
2. Sections that go from intuition to a worked example, with box-mistakes, box-regulated and
   box-askteam.
3. Exercises (E/M/H), each with Goal, Starter, Acceptance and Time. Every starter must fail
   its acceptance test, never hang. Every solution must pass.
4. A MiniDAQ milestone with a definition of done.
5. Check yourself.
6. A summary of at most 10 bullets.
7. Real references.

A chapter has 5,000 to 9,000 words of prose. Count the prose before "## Exercises", with code
blocks removed.

Commits and pushing:

- Commit author: `OussamaSegh <23560339+OussamaSegh@users.noreply.github.com>` (GitHub's
  no-reply address, since 2026-10-26). Use
  `git -c user.name=OussamaSegh -c user.email=23560339+OussamaSegh@users.noreply.github.com commit`.
- **No personal information in any commit** (user rule, 2026-10-26, when the repository became
  public): no e-mail address, full name, phone, address, employer or job details, role
  description text, salary or offer details, private situation, tokens or credentials, and no
  private links (claude.ai sessions or projects, the project files folder). Check every diff
  for them before committing; `git grep -i -E "gmail|@[a-z]+\.(com|ch)"` finds the common case.
  One exception (user decision, 2026-10-26): the author name "Oussama Seghaier" is allowed in the
  repository (title page, copyright page, covers, default `BOOK_AUTHOR`).
- **The book is generic** (user decision, 2026-10-26): it is written for any engineer who leads
  a PET DAQ. It names no employer of the reader ("your team", "your company"), quotes and cites no
  role description, and gives no calendar dates and no schedule.
  Since the retitling (2026-10-26) it names no particular scanner or manufacturer either: write
  "your scanner" and cite only public standards, guidance and textbooks. Future chapters follow
  the same rule.
- **The book is publishable on Amazon KDP** (user rule, 2026-10-26 14:56 UTC): a standalone
  technical book for any engineer. No study schedule, no week numbers, no "first weeks or 90 days
  at your new job" plan, no reader-specific onboarding (a chapter may still give reading and
  exercise hours). KDP specifications: a supported trim size (8.5 x 11 in, one volume, user
  decision 2026-10-26; at most 828 pages, and the KDP build fails above it), margins and gutter for the
  page count, embedded fonts, no bleed problems, a copyright page, a full-wrap paperback cover
  sized for the spine width, and an EPUB that passes EPUBCheck. Part V onward follows it as it is
  written; Parts I to IV and the build were retrofitted in PR #2 (merged 2026-10-26); Chapter 34
  must be written generic. KDP asks at upload whether the content is AI-generated; the copyright
  page says the book was written with AI help.
- Every commit message follows the commit policy (Chapter 36, `tools/commit_policy.json`,
  checked in CI from its `since` commit and by the commit-msg hook): a subject of at most 72
  characters without a final period, a blank line, a body wrapped at 72, and ends with ONE
  paragraph of trailers, the review line inside it (no blank line between them):

  ```
  Review: change control checklist, items 1 to 6.
  Co-Authored-By: <as the session's attribution instructions give it>
  Claude-Session: <the session's link, as the session's attribution instructions give it>
  ```

  A commit that changes a requirement, a hazard or a software item names its CR-NNNN or
  MDQ-PR-NNN (or a CR lists it in Commits). A PR branch's commits must follow it too (CI checks
  them). A new session uses its own Claude-Session line.
- "Always push, don't wait": run `git push -q origin main` after every commit. Commit in small
  steps within a chapter.
- Tag pushes are refused from cloud sessions (HTTP 403). The GitHub API is no way around it:
  on 2026-10-26 POST git/refs and POST git/tags both returned 403 ("Write access to this GitHub
  API path is not permitted through this proxy"), and the GitHub MCP tools cannot create tags.
  The way around it (2026-10-26, asked by the user): add a line `NAME FULLSHA MESSAGE` to
  `.github/tags.txt`, commit and push to main. The workflow `.github/workflows/tags.yml` then
  creates the annotated tag, as github-actions[bot]. It never moves a tag: one at another
  commit fails the job. GITHUB_TOKEN alone is not enough: GitHub refuses a tag whose commit has
  workflow files that differ from main's (first run, 2026-10-26: ch00 made, ch01 refused,
  "without `workflows` permission"), so the job needs the repository secret `TAGS_TOKEN`, a
  fine-grained token that only the user can create (this repository, Contents and Workflows
  read and write). Without it the job falls back to GITHUB_TOKEN and dispatches ci.yml on each
  new `book-v*` tag itself (ci.yml has `workflow_dispatch` from 0.4.0 on). Still create the
  tag locally too, so the release zip and the git bundle carry it. Check with
  `git ls-remote --tags origin`. The user added `TAGS_TOKEN` on 2026-10-26 (it needed Contents
  and Workflows set to read and write); run 40323265570 then made all 25 tags (ch00 to ch21,
  book-v0.1.0 to book-v0.3.0), each at the commit of the manifest, and CI ran on each. The
  user may revoke the token after a release; a run then fails with "Permission denied", and a
  new token goes into the same secret. A session can start the workflow with
  `gh workflow run tags.yml --ref main`.
- Nothing goes to an external service without the user's approval. Pushing to the user's
  GitHub repository `OussamaSegh/detector-to-diagnosis` (public since 2026-10-26; named neurolf-engineer until the retitling) is approved.

Dependencies and process:

- RapidCheck was refused, so MiniDAQ uses its own property harness (ADR 0015). Adding any new
  dependency needs the user's approval.
- Do not use subagents unless the user asks.
- Never modify the repository while `ci/run_all.sh` or a mutation run is running. The mutation
  tool edits source files in place.
- Keep the user posted with short messages and a progress checklist. Never pause between Parts
  to ask: the coordinator said "keep going through all Parts without pausing".
- An independent review of Parts I to III is at https://claude.ai/artifact/ACecmKtAFJg6kLwT1PuFnx.
  The user asked for it to be taken fully into account. Its open job-fit gaps:
  - Part V must give hardware control real depth: a register and command interface, bring-up,
    and control exposed through the Chapter 6 API.
  - Part VI needs at least one exercise that crosses C++ and Python (pybind11 or a shared file
    format).

## 3. Layout

| Path | What |
|---|---|
| `book/src/` | The chapters, in `partN/chNN-*.md`, and the front matter in `front/`. `book/book.txt` and `book/solutions.txt` give the order. |
| `book/solutions/chNN.md` | The solutions manual. |
| `book/build.sh` | Builds the book with Pandoc and XeLaTeX (8.5 x 11 in PDF, and EPUB); trim and margins are set in one place at its top. `book/build.sh kdp [book|solutions|both]` writes the KDP interior PDFs (gutter for the page count), full-wrap covers and EPUBs to `book/build/kdp/`, and runs EPUBCheck (`EPUBCHECK_JAR`); workflow `kdp.yml` runs it in CI. `book/build.sh boox [book|solutions|both]` writes `*-boox-air-5c.pdf` to `book/build/out/`: the screen PDF on a 6.18 x 8.24 in page (a 10.3 in 4:3 E Ink screen, Onyx Boox Air 5C), narrow margins, 9 pt tables, its own cover of that size (`build/cover/cover-<volume>-boox.pdf`). Code listings are included from the repo at build time with `include` and `snippet` markers (`// [snippet:name]`). |
| `book/src/front/how-to-use.md`, `copyright.md` | How to use the book (chapter shape, core and full paths, the repository's tags) and the copyright page (MIT for the code, disclaimer, AI-assistance note). |
| `book/assets/cover.tex`, `book/tools/cover_art.py` | The front covers and the full-wrap KDP covers (the Plate design, 2026-11-11). `cover_art.py` simulates a PET scan end to end (an FDG-like brain phantom, its sinogram with Poisson noise, an MLEM image; numpy, SciPy, Pillow; fixed seeds) and draws the artwork at 300 dpi into `book/assets/cover-{front,back}-{book,solutions}.jpg`: the front is the reconstruction, edge to edge, above an ink band; the back is the same ink with the four steps singles, coincidences, sinogram and image in those colors. The book is this Plate artwork. The solutions manual is Inverse: the same slice in teal and ink on paper, a paper band 4.15 in tall, and a paper spine and back. The JPEGs are committed, so the book build needs only XeLaTeX; run the script again only to change the artwork. `cover.tex` sets the type in EB Garamond and Inter; the spine matches the back, so they meet without a seam. It is drawn for the 8.5 x 11 trim and stops on any other. `\nlfvolume` is `book` (Plate) or `solutions` (Inverse); the positions marked "shared with cover_art.py" must match the script. `build.sh` compiles it into `build/cover/cover-<volume>.pdf`, page 1 of the screen PDF, and a 200 dpi JPEG for the EPUB cover. `build.sh all` also writes `<stem>-cover.jpg` (front, 300 dpi) and `<stem>-cover.pdf` (full wrap for the screen PDF's pages less the cover page) for the download page; the Boox front cover is the same design scaled. The back cover keeps KDP's barcode area (2 x 1.2 in at the lower right) empty. The author name is on the cover; no version. |
| `minidaq/` | The C++20 code. `include/minidaq/` holds the core, format, processing, pipeline, rt, control and output layers; `src/`; `apps/` (server, ctl, sim, ...); `tests/unit/` (GoogleTest); `tests/support/property.hpp`. |
| `exercises/chNN/eK_name/` | Exercises, each with `README.md`, `starter/`, `solution/` (and `NOTES.md`), and `tests/`. Built with `-DMINIDAQ_BUILD_EXERCISES=ON`. Starters are built with `-DMINIDAQ_BUILD_STARTERS=ON` and run with `ctest -L starter` (they must fail). |
| `docs/regulatory/` | The software file: SRS (`srs.md`, 237 requirements, v27), SDP (`sdp.md`, v14), risk file (`risk/`), SOUP list, problem reports (`problem-reports.json` gives `known-anomalies.md`), trace matrix, CAPAs, change requests, QMS design file (`qms/design-file.json`), and release records (`releases/X.Y.Z.md`). |
| `docs/adr/` | Architecture decision records 0001 to 0032. |
| `docs/architecture/` | `software-items.json` (items, class, paths) and `layers.json`. |
| `tools/` | Checkers and generators: `trace_matrix.py`, `design_file.py`, `anomalies.py`, `check_layers.py`, `check_risk.py`, `coverage.py`, `mutation_test.py`, `perf_gate.py`, `make_sbom.py`, `static_analysis.sh`, `release_checks.sh`, and more. |
| `measurements/` | Raw evidence behind every number in the book, one folder per chapter, plus `release-X.Y.Z/`. |
| `ci/run_all.sh` | The six CI presets locally: debug, clang-release, gcc-cxx23, hardened, asan-ubsan and tsan. |
| `.github/workflows/` | `ci.yml` (presets, static analysis, fuzz smoke, SBOM, Grype, document control), `gates.yml` (gate self-test), `codeql.yml`, `kdp.yml`, `pages.yml`, `tags.yml` and `perf.yml`. `perf.yml` never runs because there is no self-hosted runner; `pages.yml` and the CodeQL upload need a public repository (it was private on 2026-11-08 and 09, public again since 2026-11-09). |

Other presets: release, profile, fuzz, and coverage (Clang source-based coverage with MC/DC,
which builds the exercises).

Durable copies outside the container:

- `the project files folder: neurolf-book/vX.Y.Z/` holds each release: the book and solutions as PDF
  and EPUB, `minidaq-vX.Y.Z.zip` (a full git clone with tags), the SBOM, the release record and
  the CHANGELOG.
- `the project files folder: neurolf-book/backup/neurolf-wip.bundle` is a git bundle of every branch
  and tag. Refresh it after each chapter with `git bundle create ... --all`.
- If the container is lost, run `git clone` from GitHub, then fetch the tags from the bundle.

## 4. How to build, check and release

Every chapter:

```sh
cmake --preset debug && cmake --build --preset debug && ctest --preset debug -LE starter
ci/run_all.sh                     # all six presets; about 1 h on 4 vCPUs
tools/static_analysis.sh build/debug
python3 tools/trace_matrix.py . --write    # after adding // REQ: tags
python3 tools/anomalies.py . --write       # after editing problem-reports.json
python3 tools/design_file.py . --write     # after adding files under docs/
cmake -S . -B build/starters -DCMAKE_BUILD_TYPE=Release -DMINIDAQ_BUILD_EXERCISES=ON \
  -DMINIDAQ_BUILD_STARTERS=ON && cmake --build build/starters && ctest --test-dir build/starters -L starter
book/build.sh                     # the PDF must have 0 overfull hboxes (grep the .log)
```

The download page https://oussamasegh.github.io/detector-to-diagnosis/ is rebuilt by
`.github/workflows/pages.yml` on every push to main: the EPUB and the PDF of the book and the
solutions, and the Boox Air 5C PDF of both (user request 2026-11-09, `book/build.sh boox both`;
it must also have 0 overfull hboxes). The user dropped the phone and Kindle PDFs (2026-10-26);
do not add them back. The
first runs failed on a missing `lmodern` package and on a slow apt mirror; the workflow now
installs lmodern and retries stalled downloads. Pages itself (Settings, Pages, Source: GitHub
Actions) was set by the user.

At the end of a chapter, after GitHub CI is green: tag `chNN` locally and in
`.github/tags.txt`, refresh the bundle, and
update this file and the memory notes.

A release:

1. Run `tools/release_checks.sh OUT 600` on one clean commit, in a git worktree in the
   scratchpad, so the main tree can keep changing. It takes about 1.5 h: six presets, static
   analysis, starters, the tsan stress run, benchmarks, the perf gate, and 10 minutes of
   fuzzing per target.
2. Copy OUT to `measurements/release-X.Y.Z/`.
3. Write `docs/regulatory/releases/X.Y.Z.md` and check it with Exercise 14.5's checker.
4. Bump `VERSION`, add the CHANGELOG section, and update `book/src/front/edition.md`. Bump the
   Python package versions with it (`analysis/pyproject.toml`, `minidaq_analysis.__version__`,
   `recon/python/pyproject.toml`; `0.8.0-dev` is `0.8.0.dev0`): `analysis.pytest` fails otherwise
   (Part VII review). For a KDP upload, build with `book/build.sh kdp both`.
5. Commit and push. **Wait for green GitHub CI on that release commit** (SDP section 8,
   MDQ-PR-016).
6. Tag `book-vX.Y.Z` (locally, and a line in `.github/tags.txt` pushed to main), build the
   book and the solutions, zip the clone, and copy everything to
   `the project files folder: neurolf-book/vX.Y.Z/`.
7. Write the release report as a Claude Doc.
8. In the next commit on main, set the next -dev VERSION (and the Python package versions);
   otherwise `docs.version` turns every build-test job red (missed after 1.0.0, fixed by the
   1.0.0 review). A patch -dev keeps the SOUP review of the minor version valid.

Known gotchas are kept in the project memory notes: neurolf-build-gotchas,
neurolf-book-layout-gotchas, neurolf-data-io-gotchas and neurolf-release-process. The most
important ones:

- Benchmarks on the VM vary up to 5x. Report the minimum, median and maximum, and never run
  them while fuzzing or a mutation run is active.
- Run `tools/static_analysis.sh` after every C++ change, apps included. GitHub CI has caught
  what the local run missed.
- Requirement IDs (`// REQ: SRS-XXX-nnn`) are not checked for reuse. Grep before choosing a new
  one.
- `pkill -f pattern` can kill the tool's own shell. Kill by PID.
- Mutation runs: build/release and build/coverage hold mutant code while a run is active.
  Rebuild them before you measure anything.
- `tools/coverage.py` keeps about 640 MB of profiles in `BUILD/coverage-profiles/`. Never put
  them in `measurements/`.
- Exercise 18.5's solution records the SHA-256 of `minidaq/include/minidaq/format/readout_packet.hpp`.
  Any change to that header makes `ch18/e5_kill_survivors/solution/survivors` fail until the
  mutation run in its README is repeated.
- A change to MiniDAQ's behavior can break exercise solutions: the tie rule SRS-SRT-013 broke
  Chapter 10's exercise tests (CI red on f9cd6c7). Run the whole `ctest`, exercises included,
  before every push of a library change.
- Run the readout system tests with the CPUs loaded too (MDQ-PR-019 showed only under load).
  `tools/test_report.py` must run on a clean tree, or the report marks itself invalid.

## 5. Status

### Done

| Version | Content | Release commit | Tag |
|---|---|---|---|
| 0.1.0 | Part I, Chapters 1 to 7 | | |
| 0.2.0 | Part II, Chapters 8 to 12 | | |
| 0.3.0 | Part III, Chapters 13 to 17 | e32e702 (release checks ran on 57ef123) | book-v0.3.0 = 37af8f4 |
| 0.4.0 | Part IV, Chapters 18 to 21 | 6912009 (checks on 61c2e1a and 6766495) | book-v0.4.0 = 6912009 |
| 0.5.0 | Part V, Chapters 22 to 25 | 438ea37 (checks on 6ef606e) | book-v0.5.0 = 438ea37 |
| 0.6.0 | Part VI, Chapters 26 to 30 | the release commit (checks on 893413d) | book-v0.6.0 |
| 0.7.0 | Part VII, Chapters 31 and 32 | 3f7d720 (checks on cfb708f) | book-v0.7.0 = 3f7d720 |
| 0.8.0 | Part VIII, Chapters 33 and 34 | 5770582 (checks on d262ff0) | book-v0.8.0 = 5770582 |
| 0.9.0 | Part IX, Chapters 35 to 37, Appendix A | 8d34971 | book-v0.9.0 = 8d34971 |
| 1.0.0 | The complete, packaged book | 33aa5ba (checks on 517cd49) | book-v1.0.0 = 33aa5ba |

Release report Claude Docs:

- 0.1.0: https://claude.ai/artifact/CzEKc4tPTdN8JW7XnCVW5A
- 0.2.0: https://claude.ai/artifact/FHtXBkNSkxvrqmio2LmMPp
- 0.3.0: https://claude.ai/artifact/7CsiwjyrUfGem6d5SPA2tp
- 0.4.0: https://claude.ai/artifact/8iBrgKkciRovqngjwEHpSX
- 0.5.0: https://claude.ai/artifact/Eizn2MGX4aL6ovV9MTgzm2
- 0.6.0: https://claude.ai/artifact/KihwgqRBH9AxmEgheq5Ndy

For 0.3.0:

- CI failed on the release commit because the release record was not indexed in the design
  file. This was fixed in 0262322 and recorded as MDQ-PR-016. The rule since then is to tag
  only after CI on the release commit is green.
- The writer measured 15.9 to 17.0 M coincidences/s, below Chapter 12's 18 to 20. Re-measure it
  at 0.4.0.

Chapter 18 (unit and component testing): commits 1eb9046 to bd8742e, tag `ch18` (local) at
bd8742e, GitHub CI green. Property harness (ADR 0015), coverage and mutation tools, SRS v7, SDP v5,
Exercises 18.1 to 18.5, `measurements/ch18/`.

Chapter 19 (system testing): commits f9cd6c7, 68a63e2, 8d115d8, aa538e6.

- System tests in `minidaq/tests/system/` (Python stdlib): control (15), acquisition (5),
  readout (4), stats (10). STP `docs/regulatory/verification/stp.md`, `tools/test_report.py`
  (STR), `tools/soak.py`; release_checks.sh runs both.
- Found and fixed: MDQ-PR-017 (sorter ties, SRS-SRT-013), MDQ-PR-018 (minidaq_send fault report),
  MDQ-PR-019 (tracker reordered over-count). CR-0005. MDQ-PR-015 closed by the coverage review.
- SRS v8 (SRS-CTL-040 to 044, SRS-SYS-001 to 005), SDP v6. Exercises 19.1 to 19.5.
- `measurements/ch19/`: soak (PASS, with a recorded latency deviation), coverage (88.6% lines),
  system test report of 8d115d8 (34 of 34 pass).
- Tag `ch19` (local) at e12c5f0. Local CI green on aa538e6; GitHub CI on e12c5f0 was red only
  because of MDQ-PR-020 (runner rmem_max), fixed in 74a98ed (GitHub CI green). The tag message
  says so.

Chapter 20 (CI for regulated software): commits 74a98ed (MDQ-PR-020), 447cc4a (CR-0006),
b9234db (MDQ-PR-021), 23c40ab (MDQ-PR-022, Exercise 5.2 speed test now relative to the starter),
d1073fb (repro report lists manifest and toolchain), 7654434 (perf_ab fails if sides differ).

- `hardened` preset now has `-g` and `MINIDAQ_REPRODUCIBLE` (cmake/Reproducible.cmake, the two
  `-ffile-prefix-map` maps; source map first, so GCC (last wins) and Clang (longest) agree).
- `tools/release_bundle.py` (make, verify, programs), `tools/repro_check.sh` (CI job
  reproducible-build), `tools/check_tools.py` and the tool list
  `docs/regulatory/verification/tools.json` (23 tools; also fails for non-executable scripts),
  `tools/gate_selftest.py` (15 faults; workflow `gates.yml`), `tools/perf_ab.sh` (workflow
  `perf.yml`, A/B on one runner). SDP v7, SOUP list v5, design file clause 4.1.6.
- `measurements/ch20/` (README): gate self-test 15/15 on 74a98ed (12 min); reproducible locally
  and across machines (GitHub runner builds the same programs; only BUILDINFO.json differs,
  by CMake/Ninja/Python versions); package 24.2 MB; A/A 1/15 false alarms locally, 0/4 on GitHub.
- GitHub artifacts cannot be downloaded here (blob host blocked): read results from job logs.
- Trap: never write a literal requirement tag (REQ + colon) in tools/*.py; the trace matrix
  scans tools/ too.

### History of Parts VII to IX (complete; kept for reference)

Part VIII (thread started 2026-11-04).

- Chapter 33 complete: `quantize_as_on_link` + `minidaq_sim --link 1` (SRS-SIM-024),
  `tools/e2e.py` (TL-40, test `system.e2e`, ~35 s debug), `acceptance.json` ACC-01..09 +
  `tools/acceptance.py` (TL-41), `srs-baseline.json` (SRS v21) + `tools/req_baseline.py` (TL-42,
  `docs.baseline`), SRS v22, SDP v12, threat model v8, CR-0020 (implemented), ADR 0028,
  MDQ-PR-055, `measurements/ch33/`, Exercises 33.1 to 33.3, `book/src/part8/`,
  `book/solutions/ch33.md`.
- Chapter 34 complete: `tools/survey.py` (TL-43, `tools.survey`, SRS-SVY-001..003, SRS v23),
  CR-0021 (also removed two dead prefixes from software-items.json), ADR 0029, threat model v9,
  `measurements/ch34/`, Exercises 34.1 to 34.3 (34.3 is a mutation exercise, 7 mutants),
  `book/src/part8/ch34-first-90-days.md`, `book/solutions/ch34.md`.
- Release 0.8.0 (2026-11-04): checks in four parts on d262ff0 (`measurements/release-0.8.0/`);
  part 3 failed twice, the perf gate (every benchmark ~0.9 of `book-vm.json`) and ACC-04 (soak
  p99 up to 55.6 ms > 10 ms). The 0.7.0 programs on the same machine failed both the same way
  (interleaved perf equal; 0.7.0 soak p99 206.6 ms): the user approved releasing with a recorded
  deviation. If the next release's part 3 fails the same way, a CR for the gate's baseline and
  the latency margin is due. CAPA-0001 closed as effective. New reports: MDQ-PR-056 (CI lacked
  SciPy for `system.e2e`), 057 (`fuzz_calibration` oracle, found in an UNREAD CI run of the
  Part VII review: read a review branch's runs before merging), 058 (gate step hid its build
  output). SOUP v17; baseline retaken at SRS v23. Any later SRS change needs an approved CR
  naming the requirement, or docs.baseline fails.
- RELEASED 0.8.0 on 2026-11-04: CI green on 5770582 (ci, gates, codeql, kdp, pages), tag
  book-v0.8.0 on 5770582; the packaged files and the report are kept outside the repository. VERSION 0.9.0-dev, SOUP list v18 (review for
  0.9). Opus Part VIII review asked of the coordinator. Next: Part IX (see "Start here").
- RELEASED 0.9.0 on 2026-11-08: CI green on 8d34971 (ci, gates, codeql, kdp, pages), tag
  book-v0.9.0 on 8d34971; deviation for ACC-04 and ACC-08 approved; CR-0025 proposed. VERSION
  1.0.0-dev, SOUP list v20. Opus review of Part IX and Appendix A asked of the coordinator.
- RELEASED 1.0.0 on 2026-11-08: checks on 517cd49, record on 33aa5ba, tag book-v1.0.0 on
  33aa5ba; CR-0025 implemented, MDQ-PR-063 closed, MDQ-PR-064 open, deviation for ACC-04
  approved (see "Start here").
- RELEASED 1.1.0 on 2026-11-10: the illustrated interior (231 figures); checks on 9b9e96d,
  record and tag book-v1.1.0 on the release commit; CAPA-0002 closed, MDQ-PR-066 closed.
- Opus review of Part VIII (2026-11-04): PR #6 (branch claude/project-thread-uss0ag) MERGED
  LOCALLY (79187ef): e2e sorter partition with out_of_order and a stricter damaged-link test
  (MDQ-PR-059), acceptance.py commit prefix of at least 7 characters (MDQ-PR-060), Chapters 33
  and 34 text (Chapter 34 prose now over 5,000 words), the 0.8.0 record's diff claim corrected.
  One wording adjusted at the merge. Its fixes go out with 0.9.0.
- Lessons: a fresh clone is shallow; run `git fetch --unshallow` or docs.changes fails;
  problem-reports.json and tools.json are hand formatted (append, never json.dump the file); the
  pre-commit hook needs `git clang-format --staged -- '*.cpp' '*.hpp'` for touched C++ lines.

Part VII (thread started 2026-11-03).

- Done: `fuzz/fuzz_calibration.cpp` (owed to 0.7.0, in release_checks); Chapter 31 complete:
  `analysis/` (TL-33), its lock file and CI job `python`, SRS-ANA-001 to 006 (SRS v20), H-14
  with RC-45/46, CR-0017, ADR 0026, architecture v17, SOUP list v14, tools TL-33 to TL-36,
  threat model v5 (gap: QC reports are not signed), `measurements/ch31/`, Exercises 31.1 to
  31.3, text `book/src/part7/` and `book/solutions/ch31.md`.
- User approved (decision card, 2026-11-03): SciPy, Matplotlib, pytest, mypy, ruff, Numba,
  scikit-build-core. NOT approved: Conan, lmfit, Jupyter. Do not use them.
- Lessons: the analysis tests skip (77) without the lock file's packages; the CI job sets
  MINIDAQ_ANALYSIS_REQUIRED=1. Python here is /usr/local/bin/python3 (3.13); use
  `python3 -m mypy` and `python3 -m ruff`, not the uv tool ones. Book build needs
  fonts-texgyre and fonts-inconsolata (apt). Numerical derivatives need a step floor for a
  parameter near zero (CR-0017).
- Chapter 31 tagged: ch31 on 21fe31e (first green ci after it; MDQ-PR-047 fixed there).
- Chapter 32 complete (text, solutions, code): installed CMake package `recon` and
  `cmake.consumer`; workflow presets + `cmake/toolchains/` + `docs.presets`; wheel via
  scikit-build-core (`recon/python/pyproject.toml`, `recon.wheel`, CI job python);
  `.clang-format` (Google, 100 cols) checked on CHANGED LINES ONLY by `tools/check_format.py`
  (CI job `format`, gate fault `format`) and `tools/hooks/pre-commit` (install with
  `git config core.hooksPath tools/hooks`; it also refuses e-mail addresses that are not
  placeholders, whitespace errors, ruff in analysis/). SRS-BLD-001 to 005 (SRS v21), TL-37
  (clang-format-18) and TL-38, coding standard v5, SDP v11, architecture v18, threat model v6,
  CR-0018, ADR 0027, `measurements/ch32/build-times.txt`, Exercises 32.1 to 32.3
  (`minidaq_cmake_exercise`). MDQ-PR-048 (Exercise 21.3 thread start) and MDQ-PR-049 (compiler
  not in a fresh cache with toolchain files) fixed.
- Lessons: test build changes in a FRESH build directory (old caches hide toolchain-file
  changes); the hook refuses a literal address in its own test (build it at run time); the book
  build needs latexmk and librsvg2-bin too (apt) in a fresh container.
- CAPA-0001 action done (pre-0.7.0): `tests.waits` checks `// clock: <kind>` and
  `// threads: joined|started` (same line or two above); every speed test must be a row of the
  CAPA's margin table (six exercise rows added, measured under load); gate fault `clocks`;
  coding standard v6. MDQ-PR-050 (ADR 0027 options not a list) fixed. LESSON: run the WHOLE
  ctest before a commit that touches docs/adr (the ADR linter is an exercise test).
- SOUP review for 0.7.0 DONE (SOUP list v15): nlohmann 3.12.0 latest, OpenSSL no advisory
  after 2026-09-29, pybind11 3.1.0 latest; lock file: Pillow 12.3.0 and Pygments 2.17.2 had
  advisories (MDQ-PR-051) -> 13.0.0 / 2.21.0, CR-0019, `tools/lock_audit.py` (TL-39, CI job
  python; pypi.org JSON works from here, api.osv.dev and api.github.com do not). Threat model
  v7 = the release review (done). Locally pip needs --ignore-installed for Debian packages.
- Release checks 0.7.0 part 1 on 1572784 FAILED: MDQ-PR-052 (Ex 10.4 absolute 30 M rate, now
  only with EX_MIN_SINGLES_PER_S) and MDQ-PR-053 (starters need -G Ninja for Ex 32.3). CAPA-0001
  0.7.0 result written (not effective; 047, 048, 052). Part 1 restarted on the fix commit.
- Release checks 0.7.0: all four parts PASSED on cfb708f (measurements/release-0.7.0, gate
  passed outright). Release record docs/regulatory/releases/0.7.0.md, VERSION 0.7.0. ch32 tagged
  at 8092b58. Owed to 0.8.0: make fuzz_calibration faster (20 exec/s: each input writes a whole
  table); CAPA-0001 check at 0.8.0.
- RELEASED 0.7.0 on 2026-11-04: tag book-v0.7.0 on 3f7d720, files in the project folder
  `neurolf-book/v0.7.0/`, report https://claude.ai/artifact/8c2d5uiF7UkF8AZQZLMtsw. VERSION
  0.8.0-dev, SOUP list v16 (review for 0.8). The bump found MDQ-PR-054 (`cmake.consumer` asked
  for a fixed recon 0.7; it now reads VERSION). Opus Part VII review asked of the coordinator.
  Next: Part VIII (see "Start here").
- Opus review of Part VII (2026-11-04): PR #5 (branch claude/project-thread-6umbqv) MERGED
  LOCALLY (5f5611c): Chapter 31 text fixes, the Python package versions tied to VERSION, one
  exercise docstring. Its three left items fixed after the merge: wheel LICENSE (symlink
  recon/python/LICENSE, checked by recon.wheel), "a fifth" in histogram-speed.txt, and the
  format-cost numbers now recorded (measurements/ch32/format-cost.txt). Its fixes go out with
  0.8.0.

Older notes follow.

Chapters 20 and 21 are complete and tagged: ch20 on eb77c71, ch21 on 6150f42, where ci,
gates and codeql were green on GitHub. MDQ-PR-025 (listings not expanded)
and MDQ-PR-026 (Exercise 21.5 and the bisect log of git 2.55, which quotes the term) are closed.
Part IV is written and released as 0.4.0.

Privacy (2026-10-26): the book is generic (e50a79e). The user chose a fresh repository: the
history was rewritten locally with git filter-repo (noreply author, committer and tagger on every
commit and tag; old file versions scrubbed of personal data), every cited commit hash was mapped
to the rewritten one (d048834), and the clean history goes to a new, empty GitHub repository of
the same name once the user has deleted and recreated it. Hashes from before 2026-10-26 04:40 UTC
in old notes or logs outside the repository refer to the old history. A private backup of the
old history is in the project files (`backup/old-history-before-privacy-rewrite.bundle`); never
push it.

Part V (started 2026-10-26): Chapter 22 (talking to hardware from Linux) is written: register
map hw/feb.toml and its generator tools/regmap_gen.py (test docs.regmap), typed registers,
MmioBus, FakeBoard, SlowControl (SiPM bias law, temperature alarms, latched faults), the
hardware port of the acquisition service (API 2.2), `minidaq_server --hardware FILE`,
SRS-HW-001 to 010, H-10, ADR 0017, CR-0008 (b27d6ad), exercises 22.1 to 22.4. New C++ under
minidaq/*/hw, config/hardware_config and control/hardware is formatted with clang-format
(Google style, 100 columns). New Markdown documents must be added to a clause of
docs/regulatory/qms/design-file.json (docs.design_file).
Chapter 23 (high-throughput networking) is written: minidaq/net/host_counters (core layer, item
readout), UdpDetector reports socket_drops (SO_RXQ_OVFL and /proc/net/udp, the tail of a run
included; counted by the integrity verdict, RC-29) and host_*/nic_* deltas; bm_udp_receive;
measurements/ch23 (drop accounting 18/18 runs, buffer footprint, receive cost); SRS-RDO-013 to
015 (SRS v12), ADR 0018 (no kernel bypass), CR-0009 (2389c6c), architecture v9, exercises 23.1
to 23.4. The host_*/nic_* counters are host-wide and vary between runs: a test that compares
detector_counters across runs must leave them out (ch19/e5 did not, and failed intermittently;
fixed in Chapter 24's commit). Static analysis must be re-run after every last edit: a tidy
finding in host_counters.cpp reached main and the CI gate self-test caught it (418a3bb).
Chapter 24 code (firmware contract) is in: docs/hw/icd-feb.md (ICD-FEB, controlled document),
register map 1.1 (fifo_empty, fifo_overflow, fifo_level), SlowControl firmware check every cycle
and trigger control (set_triggers wakes the cycle; drained() needs a status read made after the
triggers-off write), service start/stop sequencing (trigger_timeout, drain_timeout, ServiceOptions
and hardware description 1.1 "run"), integrity counts /hardware/boards/i/fifo_overflows and
/hardware/drain_timeouts, API 2.3, SRS-HW-011 to 015 (SRS v13), RC-30, RC-31, ADR 0019, CR-0010,
architecture v10, measurements/ch24/run_sequence (stop 123 to 140 ms with boards vs 3 to 21 ms
without). The sender's packet count (tail loss on the network) is an ICD open item for map 1.2.
Chapter 24 text (book/src/part5/ch24-fpga-interface.md), solutions and Exercises 24.1 to 24.4
(handshake checker, Gray code, output FIFO model, split counter) are written; hw/rtl holds the
SystemVerilog FIFO and its testbench (test hw.rtl runs only where iverilog is installed; it is
installed locally with apt, not on CI, tool TL-26). Book: 455 pages, solutions 148.
Chapter 25 (embedded Linux platform) is written: platform/platform.json (minidaq-platform-1)
and tools/platform_check.py (IQ facts, platform SBOM; TL-27), packaging/ (hardened
minidaq.service, minidaq-rollback.service, sysctl, udev, sysusers; check tools/check_units.py,
test packaging.units), rt::Heartbeat/HealthMonitor, control::ServiceManagerLink and Watchdog
(sd_notify without libsystemd; READY after the API listens, WATCHDOG only while every loop
beats), FakeBoard fault hung_bus, item update (Ed25519 manifest, A/B slots, trial/confirm/
rollback, repair in open(), power-cut test after every step), minidaq_update, tools/make_update.py
(TL-28), SRS-PLT-001 to 011 (SRS v14), RC-32 to RC-34, threats T-39 to T-53 (threat model v3),
ADR 0020, CR-0011 (b0995fb), architecture v11, SOUP list v8, docs/platform/installation.md (INST
v1). measurements/ch25/service_and_update (READY 5 to 9 ms; hung bus unhealthy at 5 s, systemd
acts 10 s after the last ping; install 46 to 62 ms, rollback 5 ms; 45 syscalls, none refused by
@system-service minus @privileged; exposure 9.4 unhardened, 1.7 shipped). Text
book/src/part5/ch25-embedded-platform.md, solutions and Exercises 25.1 to 25.4 (watchdog
environment, SemVer precedence, power cut model, verify tree). This container has no systemd as
PID 1: the units are checked offline only.
Apple silicon (user has a MacBook Air M5): How to use this book recommends an Ubuntu 24.04 arm64
VM (OrbStack or UTM). The aarch64 cross build (g++-aarch64-linux-gnu, -Werror) passes; under
qemu-user 728 of 773 unit and solution tests pass, and the rest are emulator limits
(timeouts from slowness, /proc/self/exe is qemu, SO_RXQ_OVFL and crash signals not emulated,
no binfmt for the Python tool tests); DetectorSimulator.SameSeedSameStream and
Sinogram.APointSourceDrawsASinusoid pass without a time limit (268 s and 354 s under qemu). make_sbom.py and platform_check.py read the native package on multiarch
hosts.
Release 0.5.0 (2026-11-03; resumed by the user 2026-11-02 22:26 UTC): the release checks ran
in four parts on 6ef606e (MDQ-PR-041: the machine restarts about hourly, so
`tools/release_checks.sh OUT 600 PART` with PART 1 to 4, each under 45 minutes, each as a tracked
background Bash). Everything passed except the baseline gate, explained by the A/B against
book-v0.4.0 in `measurements/release-0.5.0/perf-ab/`. Coverage review
`measurements/release-0.5.0/coverage-review.md`; its tests found MDQ-PR-042 to 044. CAPA-0004
closed as effective; CAPA-0001 not effective again (MDQ-PR-034, 039, 040), with a margin table of
every named timing test and a new check at 0.6.0: add each new timing test of Part VI to that
table. Follow-ups promised by the coverage review for 0.6.0: a system test of the watchdog when
the hardware heartbeat stops (hung bus), and tests of the hardware description's forms (not an
object, version not a string).

Release 0.6.0 (2026-11-03): the release checks ran in four parts on 893413d; everything passed
except the baseline gate, which flagged the same three rows as at 0.5.0 (the first run shared the
machine with a build by mistake: never build while part 2's benchmarks or part 3 run); the A/B
against book-v0.5.0 in `measurements/release-0.6.0/perf-ab/` found no regression. The reviews
after the checks added the coverage review's tests (ef85887, 7fa5b1d) and found MDQ-PR-045 (a
watchdog test race, missed in a CI run that also failed for another reason) and MDQ-PR-046 (the
calibration tables had no threat model review): a9c5ba7, whose programs are byte-identical to
893413d's; the extended stress run and the coverage were run again on a9c5ba7. CAPA-0001 not
effective again; next check at 0.7.0. Promised for 0.7.0: a fuzz target for the calibration
table file (`config::parse_calibration`), which shares the fuzzed configuration reader but has
no target of its own.

Release 0.4.0 (2026-10-26): part 1 of the release checks passed on 61c2e1a, part 2 on 6766495
(the gate failed, explained by the A/B in `measurements/release-0.4.0/perf-ab/`); the programs,
benchmarks and fuzz targets of both commits are byte-identical (`identical-binaries.txt`). The
coverage review is `measurements/release-0.4.0/coverage-review.md`. CAPA-0003 closed as
effective; CAPA-0001 and CAPA-0004 are re-checked at 0.5.0. Disk: a full part 1 run with the
writer benchmark needs about 10 GB free; delete old build directories first.

Part VI plan for Chapter 26 (started 2026-11-03), so a later session can pick it up:
- core `processing/calibration` (in item `processing`): CalibrationTable (per crystal: energy
  E = a + b*c + q*c^2 of the 11-bit energy code c, identity a=0 b=0.5 q=0; time offset in ps;
  table id, version, scanner serial, created, valid_until, reference temperature, procedure,
  CRC-32 of the coefficients), checks of ranges, apply(Single&). Drift monitor: per block mean of
  calibrated energies in 430..590 keV against 511.
- pipeline: decode applies the table; sort holds back a tail of (max - min time offset) so a
  correction never makes a single late; horizon 0 without a table (unchanged speed).
- application `config/calibration_file`: strict JSON reader (object_reader), CRC check, scanner
  match, expiry refused at configure; acquisition config `calibration.file`.
- sim: per-crystal gain, a saturation nonlinearity and time skews, with truth.
- run record metadata `calibration` (id, version, file SHA-256 from the adapter, CRC).
- tools/calib (Python, numpy only: no scipy or scikit-image, which would be new dependencies):
  photopeak fit, time offsets by least squares (conjugate gradient on the graph Laplacian),
  writes the table; tool TL-29. SRS-CAL-001 to 007, hazard H-11 (wrong calibration).
- Done and pushed: a4e9eac (core), 689e79d (pipeline), 8294fd8 (simulator), c55d36b (file,
  config 1.4, service, API 2.4), then tools/calib with tools/test_calib.py (ctest tools.calib,
  about 30 s, skips without numpy; CI installs python3-numpy) and measurements/ch26 (about 4
  minutes: a centred cylinder, 20 MBq, 3 s, no phantom; gains 0.18% rms, delays 20.9 ps rms,
  summed FWHM 23.0% to 12.0%; a point source is refused by the partners criterion and would be
  130 ps rms wrong). The end-to-end check showed the server's curvature limit (0.4 each way) too
  strict for a saturating SiPM: now 0.4 down and 1.5 up (max_curvature_down/up), and the tool
  checks the server's limits before it writes. minidaq_sim's default source is a cylinder IN a
  90 mm water phantom: calibration runs need --phantom 0. Then the documents (format spec, ADR
  0021, CR-0012, H-11 with RC-35 to RC-38, architecture v12, TL-29), Exercises 26.1 to 26.3
  (Python, run as ctest via minidaq_python_exercise), the Part VI opener, the chapter text, the
  solutions and section 5 of the measurement (the monitor's baseline with a phantom: -0.89%).
  **Chapter 26 is done** (2026-11-03); tag ch26 once GitHub CI is green on its last commit.
- Exercises 26.1 gains by photopeak fit, 26.2 flood map and crystal LUT (numpy peak finding),
  26.3 time offsets by least squares (H); crystal LUT stays an exercise (boards identify crystals).
- pybind11 for Chapter 29: approved by the user on 2026-11-03 (decision card). Record it as a
  SOUP item when Chapter 29 adds it.

Chapter 27 (corrections), 2026-11-03:
- MiniDAQ: `processing/singles_counter` (per crystal in the energy window, per block every single)
  counted in the decode stage; `control/corrections_record` writes `run.corrections` (format 1)
  into the run record at the end of a run. NOTE: the run record nests the service's report under
  `run`, so the tool reads `record["run"]["corrections"]`. MDQ-L1 spec v3 describes it.
- minidaq_sim: `--efficiency-spread`, `--crystal-seed`, `--source-radius`, `--source-length`,
  `--truth-sino PREFIX` (prompts, delayeds, trues, scatters, randoms sinograms).
- `tools/recon` (TL-30, numpy only): listmode reader, sinogram binning (EndToEnd test equals
  `minidaq_listmode sino` bin for bin), corrections; ctest `tools.recon` (about 25 s).
- Findings worth keeping: randoms from singles must subtract each crystal's prompts (kill-all;
  +31% without, -1.8% with); a Gaussian tail fit fails for a head's short tails (2.4x); the
  scatter scale must be a Poisson likelihood in counts (least squares on S/n runs low and noisy
  because end slices have n of a few percent); the randoms in the tails (6 per scatter count)
  make the scatter 14% high; dead time from per-block singles matches the simulator to 0.03%.
- measurements/ch27/corrections.py takes a work dir to reuse runs (about 10 minutes from scratch).
- CR-0013, ADR 0022, SRS v16 (SRS-COR-001 to 003, SRS-SIM-023), H-12 with RC-39 and RC-40,
  architecture v13. Exercises 27.1 to 27.3 (Python). **Chapter 27 is done** (2026-11-03); tag
  ch27 once GitHub CI is green on its last commit.
- Old code still says "centre" (sim `centre_mm`, the `--centre` option): renaming is an API change,
  left for a decision.

Chapter 28 (reconstruction), 2026-11-03:
- `tools/recon` (TL-31, same package as TL-30): `project.bin_lines` (each bin's own angle: a view
  interleaves k = 2v for odd r and 2v + 1 for even r; s = -R sin(pi r / N)), `project.Projector`
  (Joseph, weights kept per view, 89 MB for 192 x 227 and 128 x 128; back is the exact adjoint),
  `mlem.osem` (corrections in the model, interleaved subsets, per-subset sensitivity), `chain`
  (Chapter 27's corrections on whole runs).
- Findings worth keeping: the lines are at R_eff = 156 mm, not the 150 mm front faces (a point
  source comes out 3.6% too close to the axis at 150); a single realization's CRC varies by about
  0.1, and the scatter estimate adds about +0.08 to the 12 mm rod, so CRC above 1 is expected;
  the noise grows 19.5% (it 4) to 80.6% (it 32) while the contrast is reached by it 3 to 8.
- measurements/ch28/reconstruct.py reuses the ch27 work dir (simulates point, rods, phantom_b).
- CR-0014, ADR 0023, SRS v17 (SRS-REC-001 to 003), H-13 with RC-41 and RC-42, TL-31,
  architecture v14. Exercises 28.1 to 28.3 (Python; 28.2 and 28.3 carry their own projector in
  tests/projector.py). The ADR linter of Exercise 6.3 runs on docs/adr: Options must be a
  numbered list (or ### subsections). **Chapter 28 is done** (2026-11-03); tag ch28 once GitHub
  CI is green on its last commit.
  Tagged ch28 on 86edea6 (2026-11-03).

Chapter 29 (C++ and Python), 2026-11-03:
- `recon/` (top level, outside the product): `recon::JosephProjector` (weights on the fly,
  `walk` shared by forward and back, threads with an image per thread for back), GoogleTest in
  `recon/tests` (also under tsan). Module `recon_cpp` (`recon/python/recon_cpp.cpp`, pybind11
  3.1.0 pinned by commit; `c_style | forcecast`, shape checks, GIL released). Option
  `MINIDAQ_BUILD_RECON_PYTHON` (ON except sanitizers/fuzz; FATAL_ERROR without python3-dev; CI
  installs python3-dev). `project.CppProjector`; `tools/test_recon_cpp.py` (ctest
  `tools.recon_cpp`, env MINIDAQ_RECON_CPP) subclasses test_recon's Projection and
  Reconstruction (their `make` attribute). static_analysis.sh and trace_matrix.py cover recon/.
- Findings: the first C++ version was no faster than numpy on one thread (66 vs 62 ms); removing
  the division per step halved it (34 ms); 4 threads 14 ms; OSEM 4x8 1.17 s -> 0.18 s.
  Agreement 4e-8 forward, 5e-9 back (numpy weights are float32).
- Exercises 29.1 (pybind11 module `rows`; CMake `minidaq_pybind_exercise`), 29.2 (C++ threads;
  TSan reports the starter's race), 29.3 (Python equivalence check).
- CR-0015, ADR 0024, SRS v18 (SRS-REC-004 to 006), RC-43 under H-13, SOUP list v11, SBOM KNOWN,
  TL-32 (pybind11), TL-31 extended, architecture v15; how-to-use lists python3-numpy and
  python3-dev. **Chapter 29 is done** (2026-11-03); tag ch29 once GitHub CI is green.
- CI on the first push failed: Clang + the runner's libstdc++ needs <algorithm> for
  std::max_element, and the hardened preset's global -fPIE/-pie broke the pybind11 module (TLS
  relocation). recon/CMakeLists.txt adds -fPIC and drops -pie for the module when hardening
  (fc3b431).

Chapter 30 (image quality), 2026-11-03:
- `tools/recon/fbp.py` (arc correction to pi R / N = 1.28 mm, spatial Ram-Lak kernel, Joseph
  back, scaled by pi/views * ds / pixel^2) and `tools/recon/quality.py` (`width`,
  `parabolic_peak`, `point_profiles`, `disc`, `contrast_recovery`, `background_variability` with
  ddof=1, `place_background_rois`). Tests `ImageQuality` (SRS-IQ-001 to 003), also as
  `CppImageQuality` in test_recon_cpp.py.
- measurements/ch30/quality.py imports measurements/ch28/reconstruct.py for its simulation and
  phantom; work dir shared with ch27/ch28 (adds point_x*, wpoint_x*, phantom_r2..5, rod_r*).
  Do not run two simulations and the analysis together on 15 GB: a sim was OOM-killed.
- Findings: FBP radial FWHM 0.76-1.35 mm near the center depends on pixel and point position
  (bins 1.28 mm, as wide as the response); parallax: radial 2.97 mm at 50, 5.05 at 100; the
  100 mm point comes out ~1 mm too far out (oblique photons interact shallower than R_eff).
  OSEM's width of a point converges in 1-2 iterations (also in a warm background). Protocol OSEM
  4x8 + 4 mm Gaussian over 6 realizations: CRC 12 mm 0.976 (SD 0.027), 8 mm 0.877 (0.040), BV
  12 mm 3.2% (0.9%). Region choice changes CRC by up to 0.3; the hottest pixel is the least
  repeatable.
- CR-0016, ADR 0025, SRS v19 (SRS-IQ-001 to 004; 004 is M with evidence in section 3), RC-44
  under H-13 (inspection of measurements/ch30/quality.txt), TL-31 extended, architecture v16.
  Exercises 30.1 to 30.3 (Python). **Chapter 30 is done** (2026-11-03); tag ch30 once GitHub CI
  is green.
- Released as 0.6.0 (see the release paragraph above). Next: the Part VI review (message the
  coordinator), then Part VII.

### Left to do, in order

1. **Part IV review**: done. PR #1 merged on 2026-10-26 (d801e22, one line rewrapped in
   f36a99e); its fixes go out with the next release. VERSION is 0.5.0-dev with the SOUP reviews
   for 0.5 (789ab17); remember this bump right after every release, or docs.version turns CI red.
2. **Part V** (22 to 25): released as 0.5.0 on 2026-11-03 (release commit 438ea37, tag
   book-v0.5.0 on GitHub, report https://claude.ai/artifact/Eizn2MGX4aL6ovV9MTgzm2). VERSION is
   0.6.0-dev with the SOUP review for 0.6 (SOUP list v10). Part V review: PR #3 merged on
   2026-11-03 (3c14b67, text fixes in chapters 22 to 25; every claim checked against the
   measurement files and the testbench); the mmio_bus.cpp O_SYNC comment it noted was fixed on
   main. Its other note, the book's very small index, is a decision for before 1.0.0. Later
   Part reviews run on an Opus model: the user said never to use Fable again.
3. **Part VI** (26 to 30): released as 0.6.0 on 2026-11-03 (checks on 893413d, tag
   book-v0.6.0, report https://claude.ai/artifact/KihwgqRBH9AxmEgheq5Ndy). VERSION is 0.7.0-dev
   with the SOUP review for 0.7 (SOUP list v13). Part VI review: PR #4 merged locally on
   2026-11-03 (text fixes in chapters 26 to 30, solutions 27 and 30, the notes of Exercises 27.2
   and 30.1; each number checked against the code and measurements); one of its numbers corrected
   on main (the highest sample is 5.5% low, not 5.4%). Its fixes go out with 0.7.0.
   Merge review PRs LOCALLY with the noreply identity and push; a merge made on GitHub (web or
   API) takes the account's email as its author (d801e22, 1252200 and 3c14b67 did).
4. **Part VII** (31 and 32): released as 0.7.0 on 2026-11-04 (checks on cfb708f, tag
   book-v0.7.0 on 3f7d720, report https://claude.ai/artifact/8c2d5uiF7UkF8AZQZLMtsw). VERSION is
   0.8.0-dev with the SOUP review for 0.8 (SOUP list v16). Part VII review: PR #5 merged locally on 2026-11-04 (5f5611c).
5. **Part VIII** (33 and 34): written 2026-11-04 and recorded as release 0.8.0 (checks on
   d262ff0, deviation for ACC-04 and ACC-08 approved by the user); released 2026-11-04, tag
   book-v0.8.0 on 5770582. VERSION is 0.9.0-dev (SOUP list v18).
6. **Part IX** (new, numbered after 34), three full chapters:
   - DICOM and PACS integration;
   - Git and team workflow in a regulated team;
   - AI-assisted coding (Claude Code) for medical-device software. Draw on how this book was
     built and checked: context files, small reviewed steps, tests first, tool validation, and
     traceability of AI-written changes.
7. **Architecture appendix**, deeper than Chapter 6: patterns, interfaces and tradeoffs on
   MiniDAQ and its ADRs, and IEC 62304 architecture, software items and SOUP boundaries.
8. **Release 1.0.0**: the complete packaged book, solutions and code.

### Review process for each Part (user rule, 2026-10-25)

When a Part is released, message the coordinator. It starts a review thread (an Opus model; never
Fable) that reviews that Part and opens a PR with fixes on a branch. This thread then reviews the PR
critically (reject or adjust wrong fixes), merges it into main, pushes, and records the merge here.
Keep working on the next Part while the review runs. Part IV (release 0.4.0) is the first Part this
applies to.

### Waiting on the user

- Enable private vulnerability reporting on the GitHub repository (Chapter 17, SECURITY.md).
- Answer whether to enable CodeQL code scanning (asked, no answer yet).

## 6. Decisions already made (do not reopen)

- Spelling is American. The book is 8.5 x 11 in, one volume, built with XeLaTeX. Diagrams use Graphviz. CI uses
  GitHub Actions. Dependencies are pinned by commit with CMake FetchContent, with a
  system-package option.
- Chapters 21, 32 and 34 are deepened in place. Part IX holds only the three new chapters.
- Property-based tests use the in-house harness, not RapidCheck (ADR 0015).
- The user chose to keep the current machine ("Keep it as it is").
- Facts that later chapters rely on:
  - dead time is 1 µs per block (an assumption);
  - the NECR peak is about 70 MBq;
  - the pair stage handles about 70 M singles/s, giving about 2.7 M coincidences/s;
  - a list-mode record (MDQ-L1) is 16 B;
  - the sinogram scale is 0.963 (depth of interaction);
  - the run record is `<prefix>-<run>.run.json`.
