# CR-0001: Integrity verdict for every run

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-10-25, by the software lead |
| Source | risk analysis of hazard H-01 (Chapter 15) |
| Decision | approved, 2026-10-25, software lead and risk manager |
| Commits | 809c211, 0179b3f, 2470b4b |

Recorded after the implementation, when change control was introduced in Chapter 16; the
analysis below is the one the Chapter 15 work followed.

## Description

The acquisition service judges every run complete or incomplete from all of its loss counters
and its fault, reports the verdict in its status (and so in the run record stored next to the
list-mode files), and writes the nonzero loss counters into the audit trail when a run ends
without a fault but with a loss. The decoder's invalid words count as a loss.

## Reason

Hazard H-01, coincidence data lost without notice, was not acceptable (S2, P4): every loss was
counted, but in more than a dozen counters in five parts of the status, and no consumer of the
data could be expected to know which of them mean loss.

## Impact analysis

### Requirements

New: SRS-CTL-030, SRS-CTL-031, SRS-OUT-011, SRS-OUT-012 and SRS-FMT-013. Repeated
verification: SRS-OUT-009 and SRS-OUT-010, whose test now also checks the verdict in the run
record.

### Software items and safety class

Changed: service (new unit run_integrity, called from the status), output (the run record carries
the verdict). Both are class B in the server process; no class or segregation changes.

### Risk

H-01: new risk controls RC-01 and RC-02; RC-03 gains SRS-FMT-013. The probability of harm after
control becomes P2. New cause considered: a verdict that is too strict is ignored, which weakens
RC-05; MiniDAQ reports the counters and leaves the clinical judgment to reconstruction.

### SOUP

None: the verdict uses nlohmann/json, already listed and reviewed.

### Interfaces and data formats

The status gains the field `integrity`, which the control protocol returns unchanged; clients
ignore unknown fields (SRS-CTL-022), so the change is compatible. The run record gains the same
field; the list-mode format MDQ-L1 does not change.

### Documents

SRS version 2; intended-use statement version 2 (the instruction to check the verdict, RC-05);
risk management plan version 1 and the hazard analysis (new); trace matrix regenerated.

### Regulatory

The intended use does not change. The change adds a protective measure to a safety-relevant
function; in a released product it would be assessed against the notified body's change
procedure and FDA's software-change guidance, and it is unlikely to need a new submission because
it adds detection without changing the acquisition (assumption: confirm with regulatory affairs).

## Verification

RunIntegrity.EveryLossCounterMakesTheRunIncomplete, RunIntegrity.AFaultMakesTheRunIncompleteWithoutALossCounter,
AcquisitionService.ALossMakesTheRunIncomplete, ListModeSink.WritesRealFilesThroughTheService,
StreamDecoder.DecodesAndCountsInvalidCrystals; the tests docs.risk and docs.trace; all six CI
presets and static analysis at tag ch15.

## Decision

Approved by the software lead and the risk manager on 2026-10-25: the change closes H-01 with an
acceptable residual risk and changes no interface incompatibly.
