# MiniDAQ software development plan

Version 2 (MiniDAQ 0.3.0-dev, Chapter 15). Status: draft for review.

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
  controlled as tools (Chapter 20).

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
- **Tool confidence:** each tool whose output is evidence is listed with its version
  ([SOUP list section 2](soup-list.md#2-items-used-only-to-develop-and-verify-minidaq)); how much
  validation a tool needs before its output is trusted is decided in Chapter 20.

## 5. Configuration management and change control

- **Configuration items:** everything in this repository, identified by the git commit;
  releases by an annotated tag `book-vX.Y.Z` and the version in `VERSION`. SOUP by the pins
  in `cmake/Dependencies.cmake`, mirrored in the [SOUP list](soup-list.md) and the SBOM
  (`tools/make_sbom.py`). The build machine's compilers and analyzers are recorded with
  their versions in the CI logs.
- **Changes:** every change is a pull request with a description of why, reviewed before it
  is merged. The reviewer checks that the requirements, the design documents, the tests and
  the trace still agree; the documentation tests (`docs.*`, `architecture.*`) make most of
  this mechanical. A change that touches a risk control, the safety class of an item or a
  SOUP item also updates the risk file (Chapter 15) and, for SOUP, repeats the known-anomaly
  review.
- **What a real quality system adds:** a change control board for changes after release,
  the regulatory assessment of each change (Chapter 13, Exercise 13.2), and approval
  records with signatures.

## 6. Verification

| Check | When | Pass criterion |
|---|---|---|
| Build with warnings as errors | every change, every preset | no warning |
| Unit, integration and documentation tests (`ctest`) | every change: `debug`, `clang-release`, `gcc-cxx23`, `hardened`, `asan-ubsan`, `tsan` (`ci/run_all.sh`, GitHub Actions) | all pass, no sanitizer report |
| Static analysis | every change | zero findings |
| Exercise solutions | every change (part of `ctest`) | all pass |
| Exercise starters | each new exercise, `ctest -L starter` | every starter fails at least one test, none hangs |
| Fuzzing | each release, 10 minutes per target from the seed corpus | no crash, coverage recorded in `measurements/` |
| Performance requirements | each release, on the reference machine | SRS-PERF-020 and SRS-PERF-021 met |
| Code review | every change | approved by a reviewer who did not write it |
| Risk management review | each release | the risk file is complete, every hazard is closed or its open status is justified for the release's intended use, the overall residual risk is acceptable (risk management plan, section 4) |

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
6. how the release was built: the preset and the commands, so the build can be repeated;
7. where the release is archived: the source zip with its git history, the book files and the
   SBOM, kept for the lifetime of the product plus the retention period of the quality system
   (assumption: confirm with team).

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
