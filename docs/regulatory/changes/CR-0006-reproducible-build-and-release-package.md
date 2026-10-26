# CR-0006: A reproducible shipped build, a release package with its evidence, and checks of the pipeline

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-25, by the software lead |
| Source | development plan section 8, items 6 and 7 (a release must be repeatable and archived); MDQ-PR-014 (a gate that never ran); MDQ-PR-020 (a test environment that was not specified) |
| Decision | approved, 2026-10-25, software lead |
| Commits | 447cc4a, b9234db, d1073fb, 7654434 |

## Description

The shipped build (preset `hardened`) gains debug information and maps the source and build
directories to relative paths (`MINIDAQ_REPRODUCIBLE`), so that two checkouts of one commit build
the same programs. `tools/release_bundle.py` packages a release as a product archive (the
programs without debug information, their debug files, the SBOM, `BUILDINFO.json`, a manifest)
and an evidence archive that names the product's SHA-256, and verifies both;
`tools/repro_check.sh` builds twice and compares. The pipeline gains checks of itself: the tool
list with the installed versions (`tools/check_tools.py`), the gate self-test
(`tools/gate_selftest.py`, workflow `gates`), and a performance comparison of each change with
its parent on the same CI runner (`tools/perf_ab.sh`, workflow `perf`), which replaces the
workflow that waited for a runner that did not exist. Two exercise tests find their fixtures
through a compile definition instead of `__FILE__`, which the mapped build makes relative.

## Reason

The development plan asks that the build of a release can be repeated; without a reproducible
build "repeated" cannot be checked, and the program a test ran cannot be shown to be the program
that ships. The pipeline's gates were trusted because they had passed: the perf gate never ran
for a whole Part (MDQ-PR-014) and nothing showed it. A gate must be shown to be able to fail.

## Impact analysis

### Requirements

None. The changes are to the build, the release process and the verification tools.

### Software items and safety class

No item's code changes. The programs of every item are built with `-g` and the path maps in the
`hardened` preset; the code generated is the same (GCC's debug information does not change code
generation), and the shipped programs are the package's, without debug information. The
hardening check reads the new programs (test `tools.hardening`).

### Risk

None. No risk control changes. The reproducibility check and the release verification add
evidence that the programs verified are the programs released.

### SOUP

None. The tools used (binutils `objcopy` and `readelf`, Python's `tarfile`) are in the tool list.

### Interfaces and data formats

None of MiniDAQ's interfaces or formats. The release package is a new format of the release
process, described in `tools/release_bundle.py`.

### Documents

Development plan version 7, SOUP list version 5 (section 2 refers to the tool list), system test
plan version 1 (tool list reference), the tool list (new), the design file (clause 4.1.6 and
transfer evidence).

### Regulatory

No change to the intended use or a safety-relevant function.

## Verification

tools.release_bundle (the package is deterministic, Bundle.test_packaging_twice_gives_the_same_bytes
and Bundle.test_the_archive_holds_no_time_and_no_owner; each of six kinds of damage is refused,
for example Bundle.test_swapped_debug_files_are_found_even_with_a_matching_manifest),
tools.perf_gate (Exercise 5.3's acceptance tests against `tools/perf_gate.py`), docs.tools (the
tool list), `tools/repro_check.sh` on the reference machine and in CI, the gate self-test
(`measurements/ch20/`), all six presets of `ci/run_all.sh`, static analysis.

## Decision

Approved by the software lead on 2026-10-25: the change makes the release repeatable and the
pipeline's gates testable, with no change to the code of any item.
