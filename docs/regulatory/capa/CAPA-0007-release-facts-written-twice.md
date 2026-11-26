# CAPA-0007: Facts of the release checks written in several places

| Field | Value |
|---|---|
| Status | closed |
| Opened | 2026-11-24, at the internal audit before release 2.2.0 |
| Source | MDQ-PR-081, MDQ-PR-087 and MDQ-PR-089 |
| Owner | software lead |
| Effectiveness check | release 2.3.0 |

## Problem

Three problem reports in two releases found a release record that stated something other than
what the release checks did: the skeleton named the hardened preset as the shipped binaries
after CR-0029 made them the product preset (MDQ-PR-081, review of 2.0.1); the skeleton named a
soak of 30 minutes after CR-0035 made it 100 (MDQ-PR-087, writing the record of 2.1.0); and the
record of 2.1.0 kept the row of 30 minutes next to evidence of 100 (MDQ-PR-089, review of 2.1.0).

## Investigation

`tools/pr_trends.py` at the audit: the three reports have the causes "a change of what ships
updated one record, not its generator" (process), "a duration written twice, changed in one
place only" (tool) and "the record check did not compare the table with its evidence" (process).
Each fact was searched for in the repository's scripts and tools:

- the soak's length: `tools/release_checks.sh` (the command and its check line) and
  `tools/release_record.py` (the row and its label);
- the six presets: `ci/run_all.sh`, `tools/release_record.py` and the release check of
  Exercise 14.5 (`REQUIRED_CHECKS`), which `tools/test_release_record.py` already compares;
- the fuzz targets: `tools/release_checks.sh` and `fuzz/CMakeLists.txt`;
- the fuzz seconds: `tools/release_checks.sh` and the record's instructions in
  `tools/release_record.py`.

A test compared the soak's two copies since MDQ-PR-087; nothing compared the fuzz targets or
seconds, which have not yet drifted. The documents (the SDP, the system test plan) state the
same facts in prose, and are controlled and reviewed with each change request that moves them.

## Root cause

A fact of the release checks was written in each script and tool that used it. A change request
that moved the fact changed the places its author found, and the checks compared at most two of
them.

## Correction

MDQ-PR-081, MDQ-PR-087 and MDQ-PR-089 are fixed (the skeleton names the product preset and the
soak's current length; the 2.1.0 record's row is corrected; `release_record.py check` compares a
record's table with its own evidence, MDQ-PR-090).

## Corrective action

`tools/release_facts.json` holds the presets, the soak's length, the fuzz seconds and the fuzz
targets. `tools/release_checks.sh`, `ci/run_all.sh` and `tools/release_record.py` read them from
it. `tools/test_release_record.py`
(`test_the_scripts_read_the_release_facts_and_keep_no_copy`) fails when a script writes one of
them again, and checks that every fuzz target is one the fuzz preset builds.

## Preventive action

The release check of Exercise 14.5 (`exercises/ch14/e5_release_check/`) keeps its own list, as
an exercise must stand on its own; `test_the_current_rules_ask_for_the_current_presets` in
`tools/test_release_record.py` compares it with the shared presets. The SDP
(`docs/regulatory/sdp.md`) and the system test plan state the facts in prose; their change goes
with the change request that changes `tools/release_facts.json`, as for CR-0035.

## Verification of the actions

`tools/test_release_record.py` passes, and fails with `--minutes 100` written back in
`tools/release_checks.sh` (checked). `bash -n` passes on both scripts, and the facts the scripts
read are those they wrote before: six presets, 100 minutes, 600 s, nine targets. The release
checks of 2.2.0 run from the shared file. No requirement or risk control changes.

## Effectiveness check

Criterion: the release checks of 2.2.0 and 2.3.0 run from `tools/release_facts.json`, their
records pass `release_record.py check` with no row edited by hand, and no problem report until
release 2.3.0 has the cause "a fact of the release checks changed in one place and not another".
Due: release 2.3.0.
Result: **effective** (2026-11-26, release record of 2.3.0). Each part holds:

- The release checks of 2.2.0 (on 5647d2e) and of 2.3.0 (on 1926017) read the presets, the soak's
  length and blocks, the fuzz seconds and the fuzz targets from `tools/release_facts.json`;
  CR-0038 added the soak's blocks to the same file, and no script writes a copy
  (`test_the_scripts_read_the_release_facts_and_keep_no_copy` passes on both commits).
- The records of 2.2.0 and 2.3.0 pass `release_record.py check`. Their rows are the skeleton's,
  except the rows each record's section Deviation names as `fail (deviation)`, which the check
  accepts only when named (MDQ-PR-098); no row was edited to agree with the evidence.
- No problem report from MDQ-PR-090 to MDQ-PR-106 has the cause "a fact of the release checks
  changed in one place and not another" (`tools/pr_trends.py` and the reports' root causes, read
  at the internal audit of 2026-11-26 and again for the record).

## Closure

Closed on 2026-11-26 with the release record of 2.3.0, on the result above, which the
coordinator approved with the release under the author's standing delegation.
