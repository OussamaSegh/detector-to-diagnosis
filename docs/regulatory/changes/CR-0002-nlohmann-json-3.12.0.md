# CR-0002: Upgrade nlohmann/json to 3.12.0

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-10-25, by the software lead |
| Source | problem report MDQ-PR-005 and the SOUP review of Chapter 14 |
| Decision | approved, 2026-10-25, software lead |
| Commits | none yet |

## Description

The SOUP item nlohmann/json moves from 3.11.3 to 3.12.0, the latest release: the pinned archive
and its SHA-256 in `cmake/Dependencies.cmake`, the minimum version of the system-package build,
the SOUP list with a new known-anomaly review, and the SBOM, which is generated from the pin.

## Reason

3.11.3 has the defect MDQ-PR-005 (an integer parsed as a floating-point number under a condition
of the C library). It is evaluated as not relevant to safety, but a known defect in SOUP that a
released version fixes is removed when the cost is low, and here it is a pin change. Without the
change, every release review of 0.3 and later carries the anomaly.

## Impact analysis

### Requirements

None changed. Verification repeated for the requirements of the items that use the library:
SRS-CFG-001 to SRS-CFG-012, SRS-CTL-020 to SRS-CTL-032 and SRS-OUT-009 to SRS-OUT-012, by the
complete test suite.

### Software items and safety class

Items that use the library: config, service, protocol, output, audit and server, all class B.
No code changes, no class or segregation changes; the library stays out of `minidaq_core`
(`tools/check_layers.py`).

### Risk

H-04 (settings other than intended) and H-05 (acquisition interrupted) depend on the parser; risk
controls RC-11 and RC-12 do not change and are verified again by their tests. The new review
found no defect of 3.12.0 that affects MiniDAQ. Estimates unchanged.

### SOUP

nlohmann/json 3.11.3 replaced by 3.12.0; known-anomaly review of 3.12.0 in the SOUP list,
section 4, which also corrects the 3.11.3 review's assumption about the trigger of MDQ-PR-005.
The license (MIT) is unchanged.

### Interfaces and data formats

None: the release notes state that no public API was removed or renamed, and MiniDAQ's JSON
output does not change (the control protocol and configuration tests compare it).

### Documents

SOUP list version 3; problem report MDQ-PR-005 closed, known anomalies regenerated; CHANGELOG.

### Regulatory

The intended use and the safety-relevant functions do not change. In a released product a SOUP
upgrade is a design change that the notified body's change procedure assesses; a patch release
of a parser with no interface change is unlikely to be significant (assumption: confirm with
regulatory affairs).

## Verification

Config.NumberOverflowIsAnErrorNotACrash, Config.TypesAndRangesAreCheckedAndAllErrorsReported,
ControlProtocol.VersioningAndMalformedInput and the rest of the suite in all six CI
presets; static analysis; the `fuzz_config` and `fuzz_protocol` smoke runs; the tests docs.soup,
docs.anomalies and tools.sbom.

## Decision

Approved by the software lead on 2026-10-25: the upgrade removes a known anomaly, changes no
interface, and its known-anomaly review found nothing that affects MiniDAQ.
