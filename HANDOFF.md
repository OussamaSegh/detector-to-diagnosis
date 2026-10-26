# Handoff: how to continue this work

This file is for an agent (or a person) who has to pick up the generation of *Detector to
Diagnosis* (formerly titled after a product) and MiniDAQ if the current session is lost. Read it fully before you change
anything. It is kept up to date with every chapter and every release. The CHANGELOG and the git
log record what changed. This file records why, how, and what is left.

Last updated: 2026-10-26 11:10 UTC: colored covers for both volumes (book/assets/cover.tex).

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
| (before 1.0.0) | Part IX and the architecture appendix |
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
- Mark an uncertain claim with "verify:".
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
- Every commit message ends with these lines:

  ```
  Review: change control checklist, items 1 to 6.

  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: <the session's link, as the session's attribution instructions give it>
  ```

  A new session uses its own Claude-Session line.
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
| `book/build.sh` | Builds the book with Pandoc and XeLaTeX (8.5 x 11 in PDF, and EPUB); trim and margins are set in one place at its top. `book/build.sh kdp [book|solutions|both]` writes the KDP interior PDFs (gutter for the page count), full-wrap covers and EPUBs to `book/build/kdp/`, and runs EPUBCheck (`EPUBCHECK_JAR`); workflow `kdp.yml` runs it in CI. Code listings are included from the repo at build time with `include` and `snippet` markers (`// [snippet:name]`). |
| `book/src/front/how-to-use.md`, `copyright.md` | How to use the book (chapter shape, core and full paths, the repository's tags) and the copyright page (MIT for the code, disclaimer, AI-assistance note). |
| `book/assets/cover.tex` | The front covers and the full-wrap KDP covers (TikZ; `\nlftrimw`, `\nlftrimh`, `\nlfwrap`, `\nlfspine`, `\nlfpages`, `\nlfauthor`; the 7 x 10 design scaled to the trim), one source for both volumes: `\nlfvolume` is `book` (violet ring) or `solutions` (teal ring, "Solutions Manual"). `build.sh` compiles it into `build/cover/cover-<volume>.pdf`, which becomes page 1 of the PDF (with `\frontmatter` patched so no blank page follows), and renders it at 240 dpi to the EPUB cover PNG. The author name is on the cover; no version. |
| `minidaq/` | The C++20 code. `include/minidaq/` holds the core, format, processing, pipeline, rt, control and output layers; `src/`; `apps/` (server, ctl, sim, ...); `tests/unit/` (GoogleTest); `tests/support/property.hpp`. |
| `exercises/chNN/eK_name/` | Exercises, each with `README.md`, `starter/`, `solution/` (and `NOTES.md`), and `tests/`. Built with `-DMINIDAQ_BUILD_EXERCISES=ON`. Starters are built with `-DMINIDAQ_BUILD_STARTERS=ON` and run with `ctest -L starter` (they must fail). |
| `docs/regulatory/` | The software file: SRS (`srs.md`, 133 requirements, v7), SDP (`sdp.md`, v5), risk file (`risk/`), SOUP list, problem reports (`problem-reports.json` gives `known-anomalies.md`), trace matrix, CAPAs, change requests, QMS design file (`qms/design-file.json`), and release records (`releases/X.Y.Z.md`). |
| `docs/adr/` | Architecture decision records 0001 to 0015. |
| `docs/architecture/` | `software-items.json` (items, class, paths) and `layers.json`. |
| `tools/` | Checkers and generators: `trace_matrix.py`, `design_file.py`, `anomalies.py`, `check_layers.py`, `check_risk.py`, `coverage.py`, `mutation_test.py`, `perf_gate.py`, `make_sbom.py`, `static_analysis.sh`, `release_checks.sh`, and more. |
| `measurements/` | Raw evidence behind every number in the book, one folder per chapter, plus `release-X.Y.Z/`. |
| `ci/run_all.sh` | The six CI presets locally: debug, clang-release, gcc-cxx23, hardened, asan-ubsan and tsan. |
| `.github/workflows/` | `ci.yml` (presets, static analysis, fuzz smoke, SBOM, Grype, document control), `codeql.yml`, and `perf.yml`. `perf.yml` never runs because there is no self-hosted runner. |

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
solutions. The user dropped the phone and Kindle PDFs (2026-10-26); do not add them back. The
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
4. Bump `VERSION`, add the CHANGELOG section, and update `book/src/front/edition.md`. For a KDP
   upload, build with `book/build.sh kdp both`.
5. Commit and push. **Wait for green GitHub CI on that release commit** (SDP section 8,
   MDQ-PR-016).
6. Tag `book-vX.Y.Z` (locally, and a line in `.github/tags.txt` pushed to main), build the
   book and the solutions, zip the clone, and copy everything to
   `the project files folder: neurolf-book/vX.Y.Z/`.
7. Write the release report as a Claude Doc.

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

Release report Claude Docs:

- 0.1.0: https://claude.ai/artifact/CzEKc4tPTdN8JW7XnCVW5A
- 0.2.0: https://claude.ai/artifact/FHtXBkNSkxvrqmio2LmMPp
- 0.3.0: https://claude.ai/artifact/7CsiwjyrUfGem6d5SPA2tp
- 0.4.0: https://claude.ai/artifact/8iBrgKkciRovqngjwEHpSX

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

### In progress (as of the last update)

Chapters 20 and 21 are complete and tagged locally: ch20 on eb77c71, ch21 on 6150f42, where ci,
gates and codeql were green on GitHub (the user pushes tags). MDQ-PR-025 (listings not expanded)
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
installed locally with apt, not on CI, tool TL-26). Book: 455 pages, solutions 148. Next:
Chapter 25 (platform: image, systemd, watchdog, signed updates with rollback), then 0.5.0.

Release 0.4.0 (2026-10-26): part 1 of the release checks passed on 61c2e1a, part 2 on 6766495
(the gate failed, explained by the A/B in `measurements/release-0.4.0/perf-ab/`); the programs,
benchmarks and fuzz targets of both commits are byte-identical (`identical-binaries.txt`). The
coverage review is `measurements/release-0.4.0/coverage-review.md`. CAPA-0003 closed as
effective; CAPA-0001 and CAPA-0004 are re-checked at 0.5.0. Disk: a full part 1 run with the
writer benchmark needs about 10 GB free; delete old build directories first.

### Left to do, in order

1. **Part IV review**: done. PR #1 merged on 2026-10-26 (d801e22, one line rewrapped in
   f36a99e); its fixes go out with the next release. VERSION is 0.5.0-dev with the SOUP reviews
   for 0.5 (789ab17); remember this bump right after every release, or docs.version turns CI red.
2. **Part V** (22 to 25): hardware layer, embedded Linux, networking, and a tuned receiver. It
   must give hardware control real depth (review gap). Release 0.5.0.
3. **Part VI** (26 to 30): calibration, corrections, 2D OSEM, C++ OSEM with bindings, and
   image quality. It needs a C++ and Python crossing exercise. Release 0.6.0.
4. **Part VII** (31 and 32): the scientific Python package. Deepen Chapter 32 (CMake and
   dependency management) to full depth. Release 0.7.0.
5. **Part VIII** (33 and 34): capstone MiniDAQ 1.0 and day-one readiness. Deepen Chapter 34
   (the first 90 days: questions to ask, a ramp-up plan) to full depth. Release 0.8.0.
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

When a Part is released, message the coordinator. It starts a review thread (Fable model if
possible) that reviews that Part and opens a PR with fixes on a branch. This thread then reviews
the PR critically (reject or adjust wrong fixes), merges it into main, pushes, and records the
merge here. Keep working on the next Part while the review runs. Part IV (release 0.4.0) is the
first Part this applies to.

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
