# 0039. Maintain releases from the records the project already keeps

Date: 2026-11-16
Status: Accepted

## Context

MiniDAQ has released thirteen versions, 0.1.0 to 1.3.0, and its software development plan said
four lines about maintenance (SDP section 10). IEC 62304 asks for a software maintenance plan
(clause 6.1): how feedback is received and evaluated, how a modification is decided and made,
and how SOUP is managed after release. Three questions had no recorded answer:

- **Which releases does a problem affect?** The problem reports say when and how a problem was
  found, not which installed versions contain it. A service engineer asked "does my scanner
  have it?" had to read the git history.
- **How long is a release supported, and with what?** Nothing said whether 1.3 gets a patch
  after 2.0, what a patch may contain, or how a fix reaches an older line.
- **What happens when a SOUP item's supplier stops supporting it?** The SOUP list reviewed each
  item's known anomalies; it did not say when the supply of fixes would end. OpenSSL 3.0, which
  every shipped server uses, reached the end of its support by the OpenSSL project on
  2026-09-07, and no record noticed.

The problem reports also hold 73 entries, 54 with a root cause, and nobody had looked at them
together.

## Options

1. **A maintenance plan only**: a document that answers the questions in prose. Cheap; nothing
   checks that the records follow it.
2. **The plan, with the records it relies on checked**: the released versions in each problem
   report and the end of support in each SOUP item, both checked by the tests that already
   check those files, and a tool that analyzes the problem reports at each minor release.
3. **A field database**: installed base, versions per site, telemetry from scanners. The real
   thing for a manufacturer, and outside what a repository can hold or test.

## Decision

Option 2. The plan (`docs/regulatory/maintenance-plan.md`) answers the questions; the checks
make the answers hold for every record:

- `affects` in a problem report: the released versions that contain the defect, [] for none,
  required from MDQ-PR-065 (the first report after 1.0.0) and for every open report;
  `tools/anomalies.py` refuses a version that the CHANGELOG does not record as released, and the
  known anomalies list each open report's releases.
- `Support ends` for each shipped SOUP item, and an `End-of-support plan` when the end falls
  within the support period of 24 months from the item's last review; `tools/check_soup.py`.
- `tools/pr_trends.py` (TL-50): the reports per release window, counted in the first release
  whose tag contains the commit that recorded them, against the window's commits with a u-chart,
  by how they were found and by root cause; quoted by the internal audit at each minor release.

Patch releases come from maintenance branches `release/X.Y`, with fixes made on main first and
cherry-picked with `-x`.

## Consequences

### Positive

- "Does my release have it?" is answered by the report, and the known anomalies of every release
  say which releases share each one.
- A SOUP item cannot reach a release with an end of support that nobody noticed; OpenSSL 3.0's
  is now recorded, with the plan to rely on the distribution's maintenance until the move to
  3.5 with the next platform definition.
- The problem reports are read as a whole at each minor release, with a rule for when a pattern
  becomes a CAPA.

### Negative

- `affects` before MDQ-PR-065 is not filled in: the earlier reports were found during
  development, before 1.0.0, and their releases were teaching milestones. Trends of escapes start
  at 1.0.0.
- Commits are a rough measure of a window's size: the repository's history was recreated once,
  and a commit can hold a chapter or a typo. The u-chart's signal is a reason to look, not a
  verdict.
- Support periods and the 24 months are assumptions, to be replaced by the manufacturer's
  service commitments.
