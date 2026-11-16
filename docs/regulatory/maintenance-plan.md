# MiniDAQ software maintenance plan

Version 4 (MiniDAQ 2.0.1). Status: approved for release 2.0.1, 2026-11-16, given by the author (software lead) in writing on 2026-11-16 at 23:53 UTC.

This plan says how MiniDAQ is maintained after a release: where feedback comes from, how it is
evaluated, which releases are supported and for how long, what a patch release may contain,
how SOUP is kept supported, and how the problem reports are analyzed for trends. It covers the
topics of the software maintenance plan of IEC 62304 (clause 6.1) for a teaching project; it is
not a document of any manufacturer's quality management system. In a real organization the
plan points to the quality system's procedures for complaints, post-market surveillance and
vigilance, which decide what a field problem means for patients and regulators; MiniDAQ has
none, so this plan marks where they come in. Chapter 40 explains it.

Changes after a release follow the same development process as before it (the
[software development plan](sdp.md), sections 3 to 8): a change request, the requirements, the
tests and the release checks. This plan adds what only exists after a release.

## 1. Feedback

Every source of feedback ends in a problem report in
[problem-reports.json](problem-reports.json) with the item it concerns (SDP section 7), or in a
recorded decision that it is not a problem of MiniDAQ:

| Source | How it arrives | Who records it |
|---|---|---|
| Complaints and service calls about a scanner | The quality system's complaint handling, which decides whether a complaint concerns the acquisition software (assumption: confirm with team) | The software team, from the complaint's record |
| The server's diagnostics from a site | The flight recorder, the crash report and `tools/postmortem.sh` (ADR 0016), sent with the service call | The software team, quoting them |
| Run records | The integrity verdict, the time base verdict and the audit trail of each run (Chapters 7, 15 and 38) | The physicist or service engineer who finds a run marked incomplete without a reason |
| SOUP | The known-anomaly reviews (section 5) and the vulnerability scan of the SBOM (CI job `vulnerability-scan`) | The software team |
| Reviews, audits and readers | Independent reviews of each release, internal audits, errata | The software team |

A report records how the problem was found ("found") and, from MDQ-PR-065 on, the released
versions that contain the defect ("affects", [] when no release did), so that the evaluation can
say which installed scanners have it. `tools/anomalies.py` (test `docs.anomalies`) checks both.

## 2. Evaluation of a problem

Each report is evaluated before anything is changed (IEC 62304 clause 6.2.1):

1. **Relevance to safety**, with its reason, against the hazards of the risk file. A problem
   relevant to safety is also given to the quality system the same day, which decides whether
   it is reportable to a regulator and whether the installed scanners need a field action
   (assumption: confirm with team; the software team does not decide vigilance).
2. **Affected releases**, by finding the change that introduced the defect and the first release
   whose tag contains it, and the releases that already contain its fix (Exercise 40.3). A
   problem found before any release had it is recorded with `affects: []`.
3. **The risk file**: a new sequence of events or a changed probability is a change to the risk
   file, made with the fix's change request.
4. **The decision**: fix it (in which kind of release, section 4), or release with it as a known
   anomaly with the decision recorded in the report.

## 3. Supported releases

A minor release is supported for 24 months after its release date (assumption: confirm with
team; a real product's support period is set by its manufacturer's service commitments and the
lifetime it declares). Supported means: a problem relevant to safety is fixed in a patch release
of that minor version, and its SOUP is kept under review (section 5). The end of a release's
support is announced in the release notes of the release that ends it, six months ahead.

A site on an unsupported release receives fixes only by upgrading. A major release (2.0.0) does
not end the support of the last minor release before it at once: 1.3 is supported until
2028-11-15.

## 4. Kinds of release

| Kind | May contain | May not contain |
|---|---|---|
| Patch (X.Y.Z+1) | Fixes of problem reports; SOUP updates within the same version line for a security or anomaly fix; documentation corrections | A new or changed requirement other than one the fix needs; a change of a data format, the control API or the configuration schema; a new SOUP item; a new feature |
| Minor (X.Y+1.0) | Compatible additions: new requirements, new fields in the formats, new commands (ADR 0003) | A change that makes an existing client, configuration or file fail |
| Major (X+1.0.0) | Breaking changes, each with a migration path and named in the release notes (CR-0029 and CR-0030 for 2.0.0) | A breaking change without a migration path |

A patch release is made from a maintenance branch, `release/X.Y`, that starts at the tag of
`X.Y.0`. A fix is made on the main branch first, then cherry-picked to each supported maintenance
branch with `git cherry-pick -x`, which records the original commit, and verified there by the
full release checks of that branch; the change request lists every branch it reached. A fix
that cannot be cherry-picked cleanly is written again for the branch and reviewed as a new
change. Every patch release has its release record and known anomalies, as any other.

While the main branch holds only changes that a patch release may contain since the tag of
`X.Y.0`, the patch release is made from the main branch itself, and `release/X.Y` is cut from the
tag of the last patch release when the first change for the next minor or major release reaches
the main branch. The release record of such a patch says so and lists the commits since the
previous tag, each with the kind of change it is (release 2.0.1 was the first).

## 5. SOUP over the years

At each minor release, and when a supplier announces a security fix, each SOUP item's known
anomalies are reviewed (SOUP list, section 4). Each item of the shipped software also records
when its supplier's support ends; an item whose support ends within the support period of
section 3, measured from its last review, records what MiniDAQ does about it (an upgrade, a
backport from another supplier, or the reasons it can be used as it is). `tools/check_soup.py`
(test `docs.soup`) checks both. An upgrade is a SOUP change with its own change request (SOUP
list, section 3).

## 6. Trends

At each minor release, `tools/pr_trends.py` (tool TL-50) analyzes the problem reports: how many
per release window and per 100 commits against a u-chart's upper control limit, how they were
found, their root causes' categories, and which ones reached a release. Its output is quoted in
the internal audit held for the release (SDP section 8, item 9). A window above its limit, a
root cause category with three or more reports in one window, or a problem that reached a
release by the same escape as an earlier one, is evaluated for a CAPA (Chapter 16); the
evaluation, CAPA or not, is recorded in the audit report.

## 7. Retirement

When a release's support ends, the release's archive (SDP section 8, item 8) is kept for the
retention period of the quality system. The readers of every data format that a supported or
retired release wrote are kept in the current release (MDQ-L1, the run record, the calibration
table), so that data from a retired release can still be read and verified.

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 40, CR-0033, ADR 0039). |
| 2 | Approved for release 2.0.0, given by the coordinator under the software lead's standing delegation of 2026-11-15; the content is that of version 1. |
| 3 | Section 4: a patch release is made from the main branch while it holds only changes a patch may contain; when `release/X.Y` is cut (release 2.0.1, roadmap 2.1.0 theme J). |
| 4 | Approved for release 2.0.1 by the author (software lead), in writing on 2026-11-16; the content is that of version 3. |
