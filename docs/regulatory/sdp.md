# MiniDAQ software development plan

Version 7 (MiniDAQ 0.4.0-dev, Chapter 20). Status: draft for review.

This plan says how MiniDAQ is developed, verified, released and maintained. It covers the
topics that IEC 62304 expects a software development plan to address, for a teaching
project; it is not a document of the manufacturer's quality management system and does not
reproduce the standard. In a real organization most of this plan points to the quality
system's procedures (document control, change control, training, supplier control) instead
of restating them; MiniDAQ has no quality system, so the plan says what it does itself and
marks what a real one would add.

## 1. Scope and safety class

- **Software system:** MiniDAQ, the acquisition software in this repository: the libraries
  `minidaq_core` and `minidaq_control`, the server `minidaq_server` and the client
  `minidaq_ctl`. Its intended use, and why it is not a medical device, are in
  [intended-use.md](intended-use.md).
- **Safety class:** B, from the classification of its software items in the
  [architecture description](../architecture/architecture.md#4-software-items-and-layers).
  The class decides which activities of this plan apply; section 9 lists what would be added
  for class C.
- **Not in scope:** the development and verification tools in `minidaq/apps/` that are not
  shipped (`minidaq_jitter`, `minidaq_latency`, `minidaq_send`, `minidaq_sim`,
  `minidaq_listmode`), the benchmarks, the fuzz targets and the exercises. They are
  controlled as tools: the [tool list](verification/tools.md) says why each is trusted.

## 2. Life cycle model

MiniDAQ is developed incrementally. Each increment (one book chapter, a few days of work)
adds or changes requirements, design, code and tests together, and ends with every
verification of section 6 passing on the main branch. A release groups several increments.
Within an increment the work is small changes, each reviewed and merged on its own.

This is compatible with IEC 62304, which does not prescribe a sequence of phases: each
activity's output must exist and be consistent before the release, not before the next
activity starts. AAMI TIR45 describes how agile practices map to the standard's activities.

| Activity | Output | Where |
|---|---|---|
| Planning | This plan | `docs/regulatory/sdp.md` |
| Requirements analysis | Software requirements, testable, with IDs | [srs.md](srs.md), checked by `tools/req_lint.py` |
| Architectural design | Architecture description, software items and classes, decision records | `docs/architecture/`, `docs/adr/` |
| Detailed design | Interface comments in the headers; the format specifications | `minidaq/include/`, `docs/formats/` |
| Unit implementation and verification | Code, unit tests, static analysis, the coding standard | `minidaq/src/`, `minidaq/tests/`, [coding-standard.md](../coding-standard.md) |
| Integration and integration testing | Service, protocol and pipeline tests with simulated and real ports | `test_acquisition_service.cpp`, `test_control_protocol.cpp`, `test_udp_detector.cpp`, `test_listmode_sink.cpp` |
| System testing | Measurements of the whole program against the performance requirements | `measurements/`, [performance budget](../performance-budget.md) |
| Release | Release record, known anomalies, archived release | section 8 |

## 3. Requirements and traceability

- Every software requirement is a row of [srs.md](srs.md) with a permanent ID, the software
  item that implements it, and its verification method. The test `docs.srs` checks the form
  of every requirement.
- A test names the requirements it verifies with a `REQ:` comment. The
  [trace matrix](trace-matrix.md) is generated from the SRS and these tags by
  `tools/trace_matrix.py`; the test `docs.trace` fails if a requirement verified by test has
  no test, if a test names an unknown requirement, or if the committed matrix is out of
  date. The trace from requirement to design is the item column of the SRS and the item's
  files in `software-items.json`.
- Requirements that implement risk controls are named by the controls of the
  [hazard analysis](risk/hazards.json), and the trace matrix lists the controls of each
  requirement. The [risk management plan](risk/risk-management-plan.md) describes the risk
  management activities; `tools/check_risk.py` (test `docs.risk`) checks the risk file
  against the SRS, the tests and the classification's preliminary hazards.
- A change to a requirement is a change like any other (section 5): the pull request changes
  the SRS, the tests and the code together.

## 4. Standards, methods and tools

- **Language and coding standard:** C++20 (C++23 tested), the
  [coding standard](../coding-standard.md) with its rule rationale.
- **Build:** CMake presets, dependencies pinned by commit or hash (`cmake/Dependencies.cmake`).
- **Static analysis:** clang-tidy 18 and cppcheck 2.13 with zero findings
  (`tools/static_analysis.sh`); compiler warnings are errors.
- **Dynamic analysis:** AddressSanitizer, UndefinedBehaviorSanitizer and ThreadSanitizer
  presets; libFuzzer targets for every parser.
- **Tests:** GoogleTest and Python `unittest`, run by CTest.
- **Version control and review:** git; the main branch only receives reviewed changes.
- **Tool confidence:** every tool whose output is in the product or is evidence is in the
  [tool list](verification/tools.md): its class (T3 makes part of the product, T2 can fail to
  reveal a defect, T1 neither), what a defect in it would do, the reasons for confidence and
  what shows it can report a failure. Off-the-shelf tools are trusted from their use, diverse
  redundancy and checks of their output; in-house tools are tested like code and shown to fail
  by `tools/gate_selftest.py` or their own tests. `tools/check_tools.py` checks the list, and the
  installed versions against it in every CI run. The SOUP list's section 2 names the pinned test
  frameworks.

## 5. Configuration management and change control

- **Configuration items:** everything in this repository, identified by the git commit;
  releases by an annotated tag `book-vX.Y.Z` and the version in `VERSION`. SOUP by the pins
  in `cmake/Dependencies.cmake`, mirrored in the [SOUP list](soup-list.md) and the SBOM
  (`tools/make_sbom.py`). The compilers and analyzers are recorded with their
  versions in the tool list, checked against each CI runner, and written into each release
  package (`BUILDINFO.json`).
- **Changes:** every change is reviewed before it is merged, against the checklist of the
  [change control procedure](changes/README.md): the requirements, the design documents, the
  tests and the trace still agree; the documentation tests (`docs.*`, `architecture.*`) make most
  of this mechanical. A change to a requirement, a risk control, a class, a SOUP item, an
  interface or a data format needs an approved change request first. MiniDAQ has one
  developer, so the review of each change is the author's own, recorded in the commit, and the
  review by a second person is the Part review at the end of each Part, recorded in the release
  notes. That is weaker than ISO 13485 and IEC 62304 expect of a team, and is accepted only for
  this teaching project (internal audit finding A-1, CAPA-0002); a team protects the main
  branch and requires a reviewer who did not write the change (assumption: confirm with team
  how the NeuroLF's reviews are recorded). A change that touches a risk control, the safety class of an item or a
  SOUP item also updates the risk file (Chapter 15) and, for SOUP, repeats the known-anomaly
  review.
- **What a real quality system adds:** a change control board for changes after release,
  the regulatory assessment of each change (Chapter 13, Exercise 13.2), and approval
  records with signatures.

## 6. Verification

| Check | When | Pass criterion |
|---|---|---|
| Build with warnings as errors | every change, every preset | no warning |
| Unit, integration, system and documentation tests (`ctest`; the system tests as the [system test plan](verification/stp.md) says) | every change: `debug`, `clang-release`, `gcc-cxx23`, `hardened`, `asan-ubsan`, `tsan` (`ci/run_all.sh`, GitHub Actions) | all pass, no sanitizer report |
| Static analysis | every change | zero findings |
| Tool versions | every change (`tools/check_tools.py --environment`) | every tool with a version check matches the tool list |
| Reproducible build | every change, `tools/repro_check.sh` (GitHub Actions) | two builds of the shipped programs from two checkouts in different directories give the same product archive |
| Gate self-test | when the tools, the CI or the regulatory files change, every week and for each release tag (`tools/gate_selftest.py`, workflow `gates`) | every gate passes on the unchanged commit and catches its planted fault for the planted reason |
| Performance A/B | every change to the code or the build (workflow `perf`, `tools/perf_ab.sh`) | the gated benchmarks of the change are not slower than those of its parent, both run interleaved on one runner |
| Exercise solutions | every change (part of `ctest`) | all pass |
| Property-based tests, wide search | each release, every property with 100 times its cases (`MINIDAQ_PROP_CASES=100`, `tools/release_checks.sh`) | all pass |
| Structural coverage | each release, the `coverage` preset and `tools/coverage.py` (`tools/release_checks.sh`) | the report per software item is recorded; no class B item's branch coverage is lower than in the previous release without a reason; every branch of a class B file changed since the previous release that the tests do not take both ways is reached by a new test or accepted with a reason in the release record's coverage review |
| Exercise starters | each new exercise and each release, `ctest -L starter` on a `Release` build (`tools/release_checks.sh`) | every starter fails at least one test, none hangs |
| System test report | each release, `tools/test_report.py` on the `release` build (`tools/release_checks.sh`) | every test case of the system test plan passes on the clean release commit; the report is signed by the tester |
| Soak | each release, `tools/soak.py`, 30 minutes at 1 M singles/s on the reference machine (`tools/release_checks.sh`) | the criteria of SRS-SYS-003 over 30 minutes: no loss, no fault, the run complete, resident memory growing by no more than 1 MiB per hour after a 10-minute warm-up (the 8-hour run belongs to the system test on the acquisition PC, SRS section 3) |
| Fuzzing | each release, 10 minutes per target from the seed corpus | no crash, coverage recorded in `measurements/` |
| Performance requirements and regression | each release, on the reference machine (`tools/release_checks.sh`) | SRS-PERF-020 and SRS-PERF-021 met; `tools/perf_gate.py` finds no row of the budget slower than the baseline, or the baseline and the budget were updated with a reason (CAPA-0004) |
| Stress run of the threaded tests | each release, `tools/stress_tests.sh` on the `tsan` build, 100 repetitions | no failure, result in `measurements/` (CAPA-0001) |
| Code review | every change; every Part | the author's review against the change control checklist; a Part review of all changes of the Part (section 5) |
| Change requests and CAPA | every change (`docs.changes`, `docs.capa`) | every request complete and consistent; every implemented one names its commits and tests |
| Document control | every change, against the last release (`tools/design_file.py --since`) | every controlled document that changed has a new version and history row |
| Release package | each release (`tools/release_bundle.py make` and `verify`; CI job `release-package` on the tag) | the product archive verifies; its SHA-256 is the same from the reference machine and from CI, or the difference is explained by a recorded tool version; the evidence archive names it |
| Risk management review | each release | the risk file is complete, every hazard is closed or its open status is justified for the release's intended use, the overall residual risk is acceptable (risk management plan, section 4) |

The checks of a release run in order on one clean commit with `tools/release_checks.sh OUT`,
which writes one file per check into `OUT` and exits with a failure when any check fails or
cannot run. Those files, copied to `measurements/release-X.Y.Z/`, are the evidence that the
release record cites (section 8). A check that is wired only into a workflow is not evidence until
the run that produced it is cited.

Unit acceptance criteria: a unit (a class or a function with its header) is accepted when its
tests pass under every preset, it has no static analysis finding, its interface is documented
in its header, and every requirement it implements is traced.

## 7. Problem resolution

- A problem found after a change has been merged (by a test, a measurement, fuzzing, a
  review or a user) is recorded in [problem-reports.json](problem-reports.json) with the item
  it concerns.
- Every report is evaluated for its relevance to safety, with the reason. An open report
  records the decision taken about it; a closed one names the change and the test that
  verifies it. `tools/anomalies.py` checks this (test `docs.anomalies`) and generates the
  [known anomalies](known-anomalies.md) that a release states.
- Problems found during development of a change, before it is merged, are fixed in the
  change and need no report.
- A real quality system links problem reports to complaints, CAPA and vigilance
  (Chapter 13, section on post-market surveillance; Chapter 16).

## 8. Release

A release is made when every check of section 6 passes on the commit to be released, and its
release record shows:

1. the version and the commit, with the tag `book-vX.Y.Z`;
2. the results of every verification of section 6 for that commit;
3. the known anomalies, generated from the problem reports, each evaluated;
4. the open hazards of the risk file, each with the justification for releasing with it for
   this release's intended use, and the evaluation of the overall residual risk;
5. the SOUP list's known-anomaly review dated for this minor version (test `docs.soup`);
6. how the release was built: the preset, the commands and the tool versions, as the product
   archive's `BUILDINFO.json` records them, and the check that a second build gives the same
   archive (`tools/repro_check.sh`);
7. where the release is archived: the product archive and the evidence archive with their
   SHA-256, the source zip with its git history, the book files and the SBOM, kept for the
   lifetime of the product plus the retention period of the quality system (assumption: confirm
   with team).

The release record is committed with the release, and that commit adds files the checks of
section 6 have not seen. The tag is set and the release is packaged only after CI on the release
commit itself is green (MDQ-PR-016).

The release record for each version is part of its release notes in `CHANGELOG.md`
and the release report. Exercise 14.5 builds a tool that checks such a record.

## 9. What class C would add

If the risk analysis (Chapter 15) classifies an item as C, this plan adds, for that item and
any item not segregated from it: a detailed design of each unit, documented before or with
the code and verified against the architecture; additional unit acceptance criteria (for
example boundary conditions, fault handling, initialization, timing and memory use, as the
standard lists them); and verification that the detailed design implements the architecture
without contradicting it. The rest of this plan already applies to all items.

## 10. Maintenance

After a release, changes follow the same process (sections 3 to 8). The SOUP list is
reviewed for new anomalies at each minor release and whenever a SOUP supplier announces a
security fix; field feedback becomes problem reports. A real quality system adds the
software maintenance plan's link to post-market surveillance and to the change assessment
of Chapter 13.

## 11. Changes to this plan

| Version | Change |
|---|---|
| 1 | First version (Chapter 14). |
| 2 | Risk management (Chapter 15): requirements traced to risk controls, the test `docs.risk`, and the risk file's review before release. |
| 3 | Chapter 16: change requests, CAPA and document control as verification activities; how changes are reviewed with one developer (internal audit finding A-1, CAPA-0002). |
| 4 | Release 0.3.0: the release checks are one script, `tools/release_checks.sh`, which fails when a check cannot run; the performance row includes the regression gate and the starters row a `Release` build (MDQ-PR-014, CAPA-0004). |
| 5 | Chapter 18: the wide search of the property-based tests and the structural coverage review of class B items as verification activities of each release; section 8: tag only after CI on the release commit is green (MDQ-PR-016). |
| 6 | Chapter 19: system tests of the shipped programs in every change's `ctest`, under the new system test plan; the system test report and the soak as checks of each release. |
| 7 | Chapter 20: the tool list and its checks replace the tool row of section 4; tool versions, the reproducible build, the gate self-test and the performance A/B comparison as checks of the pipeline; the release package and its evidence archive in sections 6 and 8. |
