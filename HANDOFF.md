# Handoff: how to continue this work

This file is for an agent (or a person) who has to pick up the generation of *The NeuroLF
Engineer* and MiniDAQ if the current session is lost. Read it fully before you change
anything. It is kept up to date with every chapter and every release. The CHANGELOG and the git
log record what changed. This file records why, how, and what is left.

Last updated: 2026-10-26 02:05 UTC, with the Chapter 21 text (CI pending).

## 1. The goal

The reader is a C++ engineer preparing to work on the data acquisition system of a brain PET
scanner. This repository holds two things:

- **The book** *The NeuroLF Engineer* (`book/`). It has 34 chapters in Parts I to VIII, plus a
  new Part IX and an architecture appendix (section 6). It is a 10-week preparation.
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
- Mark a NeuroLF-specific number with "assumption: confirm with team".
- Never reproduce ISO or IEC text.

Style:

- American spelling, second person.
- No em-dashes.
- Prose lines wrapped at 100 characters.
- Never write "the plan" in the book: readers have no plan.
- State a chapter's week only as it appears in the front-matter schedule table
  (`book/src/front/schedule.md`), and update that table when a Part lands.

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
- **The book is generic** (user decision, 2026-10-26): it is written for any engineer who leads
  a PET DAQ. It names no employer of the reader ("your team", "your company"), quotes and cites no
  role description, and gives no calendar dates for the reader's schedule (weeks 1 to 10 only).
  The NeuroLF's manufacturer appears only in reference entries. Future chapters follow the same
  rule.
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
  Create tags locally. They travel in the release zip and the git bundle, and the user pushes
  them (`git fetch BUNDLE 'refs/tags/*:refs/tags/*' && git push origin --tags`).
- Nothing goes to an external service without the user's approval. Pushing to the user's
  GitHub repository `OussamaSegh/neurolf-engineer` (public since 2026-10-26) is approved.

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
| `book/build.sh` | Builds the book with Pandoc and XeLaTeX (7x10 in PDF, and EPUB). Code listings are included from the repo at build time with `include` and `snippet` markers (`// [snippet:name]`). |
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

At the end of a chapter, after GitHub CI is green: tag `chNN` locally, refresh the bundle, and
update this file and the memory notes.

A release:

1. Run `tools/release_checks.sh OUT 600` on one clean commit, in a git worktree in the
   scratchpad, so the main tree can keep changing. It takes about 1.5 h: six presets, static
   analysis, starters, the tsan stress run, benchmarks, the perf gate, and 10 minutes of
   fuzzing per target.
2. Copy OUT to `measurements/release-X.Y.Z/`.
3. Write `docs/regulatory/releases/X.Y.Z.md` and check it with Exercise 14.5's checker.
4. Bump `VERSION`, add the CHANGELOG section, and update `book/src/front/edition.md` and the
   schedule table.
5. Commit and push. **Wait for green GitHub CI on that release commit** (SDP section 8,
   MDQ-PR-016).
6. Tag `book-vX.Y.Z`, build the book and the solutions, zip the clone, and copy everything to
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
  Chapter 10's exercise tests (CI red on 8284e0e). Run the whole `ctest`, exercises included,
  before every push of a library change.
- Run the readout system tests with the CPUs loaded too (MDQ-PR-019 showed only under load).
  `tools/test_report.py` must run on a clean tree, or the report marks itself invalid.

## 5. Status

### Done

| Version | Content | Release commit | Tag |
|---|---|---|---|
| 0.1.0 | Part I, Chapters 1 to 7 | | |
| 0.2.0 | Part II, Chapters 8 to 12 | | |
| 0.3.0 | Part III, Chapters 13 to 17 | b63ff77 (release checks ran on 8821c48) | book-v0.3.0 = be79f34 |

Release report Claude Docs:

- 0.1.0: https://claude.ai/artifact/CzEKc4tPTdN8JW7XnCVW5A
- 0.2.0: https://claude.ai/artifact/FHtXBkNSkxvrqmio2LmMPp
- 0.3.0: https://claude.ai/artifact/7CsiwjyrUfGem6d5SPA2tp

For 0.3.0:

- CI failed on the release commit because the release record was not indexed in the design
  file. This was fixed in 897a31e and recorded as MDQ-PR-016. The rule since then is to tag
  only after CI on the release commit is green.
- The writer measured 15.9 to 17.0 M coincidences/s, below Chapter 12's 18 to 20. Re-measure it
  at 0.4.0.

Chapter 18 (unit and component testing): commits b76f319 to a95b11c, tag `ch18` (local) at
a95b11c, GitHub CI green. Property harness (ADR 0015), coverage and mutation tools, SRS v7, SDP v5,
Exercises 18.1 to 18.5, `measurements/ch18/`.

Chapter 19 (system testing): commits 8284e0e, 6919df2, c3152c7, bddbd57.

- System tests in `minidaq/tests/system/` (Python stdlib): control (15), acquisition (5),
  readout (4), stats (10). STP `docs/regulatory/verification/stp.md`, `tools/test_report.py`
  (STR), `tools/soak.py`; release_checks.sh runs both.
- Found and fixed: MDQ-PR-017 (sorter ties, SRS-SRT-013), MDQ-PR-018 (minidaq_send fault report),
  MDQ-PR-019 (tracker reordered over-count). CR-0005. MDQ-PR-015 closed by the coverage review.
- SRS v8 (SRS-CTL-040 to 044, SRS-SYS-001 to 005), SDP v6. Exercises 19.1 to 19.5.
- `measurements/ch19/`: soak (PASS, with a recorded latency deviation), coverage (88.6% lines),
  system test report of c3152c7 (34 of 34 pass).
- Tag `ch19` (local) at ecc1cb3. Local CI green on bddbd57; GitHub CI on ecc1cb3 was red only
  because of MDQ-PR-020 (runner rmem_max), fixed in 27a2b53 (GitHub CI green). The tag message
  says so.

Chapter 20 (CI for regulated software): commits 27a2b53 (MDQ-PR-020), f63f5bf (CR-0006),
1e069f5 (MDQ-PR-021), de1b7cf (MDQ-PR-022, Exercise 5.2 speed test now relative to the starter),
2d123f5 (repro report lists manifest and toolchain), 2893d09 (perf_ab fails if sides differ).

- `hardened` preset now has `-g` and `MINIDAQ_REPRODUCIBLE` (cmake/Reproducible.cmake, the two
  `-ffile-prefix-map` maps; source map first, so GCC (last wins) and Clang (longest) agree).
- `tools/release_bundle.py` (make, verify, programs), `tools/repro_check.sh` (CI job
  reproducible-build), `tools/check_tools.py` and the tool list
  `docs/regulatory/verification/tools.json` (23 tools; also fails for non-executable scripts),
  `tools/gate_selftest.py` (15 faults; workflow `gates.yml`), `tools/perf_ab.sh` (workflow
  `perf.yml`, A/B on one runner). SDP v7, SOUP list v5, design file clause 4.1.6.
- `measurements/ch20/` (README): gate self-test 15/15 on 27a2b53 (12 min); reproducible locally
  and across machines (GitHub runner builds the same programs; only BUILDINFO.json differs,
  by CMake/Ninja/Python versions); package 24.2 MB; A/A 1/15 false alarms locally, 0/4 on GitHub.
- GitHub artifacts cannot be downloaded here (blob host blocked): read results from job logs.
- Trap: never write a literal requirement tag (REQ + colon) in tools/*.py; the trace matrix
  scans tools/ too.

### In progress (as of the last update)

Chapter 20 is complete and tagged ch20 locally on 069e5a0, where ci, gates and perf were green on
GitHub. Chapter 21 is written (code 0e03f6c, exercises 3231443 and aeb0b42, text and solutions
after them); local CI was green on all six presets for the code. Left for Chapter 21: GitHub CI
green on the last commit, then tag ch21 locally (the user pushes tags). MDQ-PR-025 (Chapter 20's
listings were not expanded) is fixed in the same commit as the text.

Privacy (2026-10-26): the book is generic (e670ec4). The history rewrite that removes the old
e-mail address from 100 commits and scrubs old file versions is prepared but not run: the
session's safety check blocked git filter-repo, and the user was asked directly. A private
backup of the old history is in the project files (`backup/old-history-before-privacy-rewrite.bundle`);
never push it. After a rewrite, remap the commit hashes cited in documents (CR Commits fields,
CHANGELOG, problem reports, measurements, HANDOFF) from filter-repo's commit map.

### Left to do, in order

1. Finish Chapter 20 (above).
2. **Chapter 21**: GitHub CI and the tag (see above).
3. **Part IV review and release 0.4.0.** It includes:
   - the CAPA-0003 and CAPA-0004 effectiveness checks;
   - the writer re-measurement;
   - weeks 6 and 7 hours in the schedule table;
   - Part IV marked complete in `edition.md`.
4. **Part V** (22 to 25): hardware layer, embedded Linux, networking, and a tuned receiver. It
   must give hardware control real depth (review gap). Release 0.5.0.
5. **Part VI** (26 to 30): calibration, corrections, 2D OSEM, C++ OSEM with bindings, and
   image quality. It needs a C++ and Python crossing exercise. Release 0.6.0.
6. **Part VII** (31 and 32): the scientific Python package. Deepen Chapter 32 (CMake and
   dependency management) to full depth. Release 0.7.0.
7. **Part VIII** (33 and 34): capstone MiniDAQ 1.0 and day-one readiness. Deepen Chapter 34
   (the first 90 days: questions to ask, a ramp-up plan) to full depth. Release 0.8.0.
8. **Part IX** (new, numbered after 34), three full chapters:
   - DICOM and PACS integration;
   - Git and team workflow in a regulated team;
   - AI-assisted coding (Claude Code) for medical-device software. Draw on how this book was
     built and checked: context files, small reviewed steps, tests first, tool validation, and
     traceability of AI-written changes.
9. **Architecture appendix**, deeper than Chapter 6: patterns, interfaces and tradeoffs on
   MiniDAQ and its ADRs, and IEC 62304 architecture, software items and SOUP boundaries.
10. **Release 1.0.0**: the complete packaged book, solutions and code.

### Review process for each Part (user rule, 2026-10-25)

When a Part is released, message the coordinator. It starts a review thread (Fable model if
possible) that reviews that Part and opens a PR with fixes on a branch. This thread then reviews
the PR critically (reject or adjust wrong fixes), merges it into main, pushes, and records the
merge here. Keep working on the next Part while the review runs. Part IV (release 0.4.0) is the
first Part this applies to.

### Waiting on the user

- Push all 24 tags (ch00 to ch20, book-v0.1.0 to book-v0.3.0): GitHub has none of them yet
  (checked 2026-10-26). They are in the bundle. Cloud sessions cannot push tags.
- Enable private vulnerability reporting on the GitHub repository (Chapter 17, SECURITY.md).
- Answer whether to enable CodeQL code scanning (asked, no answer yet).

## 6. Decisions already made (do not reopen)

- Spelling is American. The PDF is 7x10 in, built with XeLaTeX. Diagrams use Graphviz. CI uses
  GitHub Actions. Dependencies are pinned by commit with CMake FetchContent, with a
  system-package option.
- Chapters 21, 32 and 34 are deepened in place. Part IX holds only the three new chapters.
- Property-based tests use the in-house harness, not RapidCheck (ADR 0015).
- There is one 10-week schedule table in the front matter. Chapters refer to it.
- The user chose to keep the current machine ("Keep it as it is").
- Facts that later chapters rely on:
  - dead time is 1 µs per block (an assumption);
  - the NECR peak is about 70 MBq;
  - the pair stage handles about 70 M singles/s, giving about 2.7 M coincidences/s;
  - a list-mode record (MDQ-L1) is 16 B;
  - the sinogram scale is 0.963 (depth of interaction);
  - the run record is `<prefix>-<run>.run.json`.
- Verified company facts, usable without hedges:
  - NeuroLF 510(k) K241751 was cleared on 2024-07-15, product code KPS;
  - the MDR CE mark was announced on 2024-10-02.
