# CAPA-0008: Machine paths in committed evidence

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-11-26, at the internal audit before release 2.3.0 |
| Source | MDQ-PR-101, MDQ-PR-103 and MDQ-PR-106 |
| Owner | software lead |
| Effectiveness check | release 3.0.0 |

## Problem

The repository is public, and the privacy rule (`CLAUDE.md`) forbids an absolute path of the
machine in anything committed. Two problem reports in two days found evidence that named one:
the acceptance report (MDQ-PR-101, review of 2.2.0) and the A/B soak's block summaries
(MDQ-PR-103, CR-0038's first run). Each corrected its own generator.

## Investigation

The audit of 2026-11-26 searched every tracked file under `measurements/` and `docs/` for a
home directory (under `home`, `Users` or `root` at the top of the file system) or an agent's scratch directory
(`/tmp/claude-N/...`): 668 lines in 184 files, in the evidence of every release from 0.3.0 to
2.2.0 and of several chapters (MDQ-PR-106). The writers are the programs the release checks
run, each printing the directories it was given: CTest ("Test project ..."), Google
Benchmark's executable paths, the performance suite, the end-to-end run and its provenance,
coverage and property runs. No document under `docs/` named one. A temporary directory such as
`/tmp/tmp.XXXX` names neither the machine nor its user and is left as it is.

## Root cause

The rule applies to every committed file, but only the agent files were checked for it
(`tools/check_agent_files.py`, TL-52). Evidence has many writers, most of them programs the
project does not own, so correcting each writer when someone noticed it could not keep the
paths out.

## Correction

`tools/evidence_paths.py fix` rewrote the 184 files: a home directory as `~`, a scratch
directory as `$SCRATCH`, the rest of each path kept, and each file's lines and line endings
unchanged (667 lines changed, as many added as removed). No measured value changes. The
history of the repository keeps the old text; the paths name no person, so it is not
rewritten.

## Corrective action

The paths are removed where all evidence passes, not in each writer: `tools/evidence_paths.py`
(TL-53) fixes a folder of evidence, and its check runs over every tracked file under
`measurements/` and `docs/` in the unit suite (`docs.evidence_paths` in
`minidaq/tests/CMakeLists.txt`), so a commit that adds such a path fails before a push
(SDP section 5).

## Preventive action

The release-checks skill (`.claude/skills/release-checks/SKILL.md`, version 2) runs the fix on
a release's evidence when it is copied into `measurements/`, before the record is drafted, and
the least-privilege policy (`tools/agent_files_policy.json`) allows the skill that command.

## Verification of the actions

`tools/test_evidence_paths.py` (test `tools.evidence_paths`): the rewrite of each kind of
path, temporary and relative paths kept, the check reading tracked evidence only, binary files
and line endings left alone, and the command's exit status. `docs.evidence_paths` reported 668
problems on the tree before the fix and none after. No requirement or risk control changes;
the evidence's values are unchanged.

## Effectiveness check

Criterion: the evidence of releases 2.3.0 and 3.0.0 is committed with `docs.evidence_paths`
passing and without a hand edit for a path, and no problem report until release 3.0.0 has the
cause "evidence names a path of the machine".
Due: release 3.0.0.
Result: filled in at the check.

## Closure

Open until the effectiveness check.
