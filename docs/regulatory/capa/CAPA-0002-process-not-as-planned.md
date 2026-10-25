# CAPA-0002: Changes not reviewed and documents not controlled as planned

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-10-25, by the software lead (internal audit findings A-1 and A-2) |
| Source | internal audit 2026-10-25, findings A-1 and A-2 |
| Owner | software lead |
| Effectiveness check | release 0.4.0 |

## Problem

The SDP required a pull request reviewed by someone other than its author for every change; every
change went to the main branch directly, reviewed only by its author and, at the end of each Part,
by the Part review (A-1). Seven of the ten controlled documents recorded no changes, and two had no
version at all (A-2).

## Investigation

The audit read the git history of all controlled documents and the commits of Chapters 1 to 15.
Every commit is the author's, pushed to `main`; the Part reviews of Parts I and II are in the
CHANGELOG and found real defects (wrong cross-references, worked examples). Of the ten controlled
documents, the seven written before Chapter 14 had no history table, and the performance budget
changed in four chapters without a version; the SDP, the SRS and the risk management plan, written
for the standards, had theirs. A third process gap of the same kind is CAPA-0001's: problems fixed
without problem reports.

## Root cause

The SDP of Chapter 14 described the process of a team, written before anyone checked it against how
the project actually works: one developer, committing to `main`. Nothing compared the plan with the
practice, and the document rules had no check, so they were applied to the documents written for the
standards and forgotten for the engineering documents that came before. A plan that nobody can
follow is not followed.

## Correction

Every controlled document has a version and a history table (Chapter 16), reconstructed from git
where needed, with the gaps stated in the history rows.

## Corrective action

The SDP, version 3, states the review that MiniDAQ actually does: the author's review of each
change against the checklist in `docs/regulatory/changes/README.md`, a second person's review at
the end of each Part, and why that is weaker than the standards expect of a team
(`docs/regulatory/sdp.md`, section 5). Document control is checked by `tools/design_file.py`:
`docs.design_file` on every change, and `--since` the last release tag in `ci/run_all.sh` and in
the `document-control` job of `.github/workflows/ci.yml`.

## Preventive action

The internal audit compares plan and practice once per Part from now on, before the Part
review, and its report is a controlled record in `docs/regulatory/qms/`. A new procedure gets a
check in `tools/` when it is written, as the change control (`tools/check_changes.py`) and CAPA
(`tools/check_capa.py`) procedures of Chapter 16 did.

## Verification of the actions

The tests docs.design_file, docs.changes and docs.capa pass; `tools/design_file.py --since
book-v0.2.0` passes; the SDP's other requirements are unchanged.

## Effectiveness check

Criterion: the internal audit of Part IV finds no controlled document changed without a new
version, and every change since this CAPA either reviewed against the checklist (the commit says
so) or covered by a change request.
Due: release 0.4.0.
Result: filled in at the check.

## Closure

Not closed: the effectiveness check is due at release 0.4.0.
