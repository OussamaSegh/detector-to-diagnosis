# MiniDAQ risk management plan

Version 2 (MiniDAQ 0.4.0-dev, release 0.4.0). Status: draft for review.

This plan describes how risk is managed for MiniDAQ's software, following the structure that
ISO 14971:2019 expects of a risk management plan, for a teaching project. It is not a document
of any manufacturer's quality management system and does not reproduce the standard. In a real
product, the software's risk management is part of the risk management of the whole scanner:
the hazards below are the scanner's hazards to which the software can contribute, and the
criteria are the manufacturer's (assumption: confirm with team how your scanner's risk file is
organized and where the software's part of it lives).

## 1. Scope

MiniDAQ's software as described in the [intended-use statement](../intended-use.md), in every
phase of its life cycle: development, release, use at the scanner and maintenance. The
hardware of the scanner, the reconstruction software and the clinical workflow are outside
the scope; their controls appear here only where MiniDAQ's risk relies on them (section 4 of
the [software item classification](../../architecture/architecture.md#4-software-items-and-layers)).

## 2. Responsibilities

| Role | Responsibility |
|---|---|
| Software lead | Owns this plan and the risk file; approves every change to them. |
| Developer of a change | Updates the hazard analysis, the FMEA and the requirements that a change affects, in the same change. |
| Reviewer of a change | Checks that the risk file still describes the software after the change. |
| Clinical expert | Confirms severities and the clinical assumptions of the probabilities (assumption: confirm with team who fills this role). |
| Management | Approves the overall residual risk before a release. |

## 3. Risk acceptability criteria

The scales and the criterion are in [hazards.json](hazards.json), section `criteria`, so that
`tools/check_risk.py` applies exactly the criterion that this plan states:

- Severity S1 (negligible) to S4 (critical); probability of harm P1 (improbable) to
  P5 (frequent), per site and year of use.
- A risk is acceptable if the severity index plus the probability index is at most 5. Every
  risk is reduced as far as possible, acceptable or not.
- The probability that the software fails is taken as 1. A probability of harm comes from what
  happens after the failure: the controls that detect it, the clinical workflow, and controls
  outside the software.
- The criteria are MiniDAQ's teaching choices (assumption: confirm with team); a manufacturer
  derives them from its risk management policy.

**Overall residual risk.** Acceptable when every hazard is closed, no hazard's residual risk
depends on a control that is not verified, and the benefit of the scanner (diagnosis without
the alternatives' delay or dose) outweighs the combined residual risks, as judged by the
software lead and the clinical expert and recorded in the release record.

## 4. Activities

| Activity | Method | Output |
|---|---|---|
| Hazard identification | Top-down, from the intended use and the scanner's hazards; the preliminary hazards of the software classification are refined into hazards with sequences of events. | [hazards.json](hazards.json) |
| Analysis of software failure modes | Bottom-up FMEA of the class B items with the most complex logic, the sorter first. | [fmea-sorter.json](fmea-sorter.json) |
| Analysis of combined causes | Fault tree of the top event "incomplete data treated as complete". | [fault-tree-data-loss.dot](fault-tree-data-loss.dot) |
| Risk control | Controls by inherent safety by design, protective measures, then information for safety, in this order of priority. Each design control is a requirement of the [SRS](../srs.md). | `controls` in hazards.json |
| Verification of implementation | Every requirement that implements a control is verified (trace matrix). | [trace-matrix.md](../trace-matrix.md) |
| Verification of effectiveness | A test that shows the hazardous situation is detected or prevented, or an inspection or analysis that is recorded. | `effectiveness` in hazards.json |
| Mechanical checks | `tools/check_risk.py`, run as the test `docs.risk` on every change. | CI |
| Review before release | The risk file is complete, every hazard is closed or its release with an open hazard is justified, the overall residual risk is acceptable. | Release record ([SDP](../sdp.md)) |
| Production and post-production | Problem reports from use are evaluated for new hazards and for probabilities that are higher than assumed (clause 9 of IEC 62304, Chapter 16). | [problem-reports.json](../problem-reports.json) |

## 5. What the checks do not do

`tools/check_risk.py` checks the form and the links of the risk file: scales, the
acceptability rule, the existence and verification of every control, and that the
classification's hazards agree with the analysis. It cannot tell whether a hazard is missing,
whether a severity is right, or whether a test really shows that a control is effective. Those
are the reviews of section 4.

## 6. Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 15). |
| 2 | Editorial, recorded at the release checks of 0.4.0 (MDQ-PR-030): the text names no manufacturer (the book is generic, commit e50a79e); the content is unchanged. |
