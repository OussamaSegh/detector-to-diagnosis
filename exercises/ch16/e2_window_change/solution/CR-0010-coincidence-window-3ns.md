# CR-0010: Default coincidence window of 3 ns

| Field | Value |
|---|---|
| Status | proposed |
| Requested | 2026-10-25, by the physics lead |
| Source | improvement: fewer randoms at high activity |
| Decision | pending |
| Commits | none yet |

## Description

The default of `/pipeline/coincidence_window_ps` becomes 3,000 ps instead of 4,000 ps, for
configuration documents of a new schema version 1.4. Documents of versions 1.0 to 1.3 keep the
4,000 ps default, and a document that sets the window explicitly keeps its value. The sorter's
own default (`SorterConfig::window`) follows the configuration.

## Reason

Randoms grow in proportion to the window: a 3 ns window should remove about a quarter of them
(estimate from the proportionality, to be measured) and improve the noise-equivalent count rate
at high activity. The window must still contain every true pair: the largest time-of-flight
difference in a 150 mm radius ring is 2 x 150 mm / c, about 1.0 ns, and three standard
deviations of a 300 ps FWHM timing resolution add about 0.4 ns, so 3 ns keeps a margin
(assumption: confirm the NeuroLF's timing resolution and field of view with the team). If the
change is not made, the randoms correction keeps its larger variance.

## Impact analysis

### Requirements

New: a requirement that the configuration reader gives the window the default 4,000 ps for schema
versions before 1.4 and 3,000 ps from 1.4 (ID assigned when the SRS changes). Changed: SRS-CFG-001
("its documented default" becomes the default of the document's schema version). Verification
repeated: SRS-SRT-001, SRS-SRT-007, SRS-SRT-010 and SRS-SRT-011, whose tests use the default
window, and SRS-OUT-012, which stores the effective configuration.

### Software items and safety class

Changed: config (schema version 1.4 and the version-dependent default) and the sorter's default.
Both class B; no class or segregation changes.

### Risk

H-04, settings other than intended: a default that changes under an existing document is exactly
this hazard, which is why old schema versions keep 4 ns; RC-11 and RC-12 still hold, and RC-12
records the window that a run used. H-07, wrong coincidence selection: a window too narrow for the
real timing resolution or field of view loses trues without any counter showing it; RC-16 must be
repeated at 3 ns, and the margin above rests on an assumption until the scanner's timing
resolution is measured. Probabilities after control are unchanged if both hold.

### SOUP

None.

### Interfaces and data formats

The configuration schema gains version 1.4, in `acquisition_config.hpp` (`supported_minor`) and
in `docs/architecture/acquisition-config.schema.json`. The list-mode format MDQ-L1 does not
change: its metadata already records `coincidence_window_ps`, so data of both windows stay
interpretable, and reconstruction must not combine runs with different windows without
correcting for them. The control API does not change.

### Documents

`minidaq/configs/default.json`, which sets 4000 explicitly and so would keep 4 ns: it moves to
schema 1.4 and 3000, or the shipped configuration never sees the change.
`docs/architecture/architecture.md` and `docs/regulatory/known-anomalies.md` (MDQ-PR-007: the
sorter holds 103 ns of singles instead of 104 ns); the SRS; the configuration schema;
`measurements/ch10/validation.txt` regenerated; the CHANGELOG; and the book's Chapter 10, which
states the 4 ns default.

### Regulatory

The intended use does not change. The change alters a default acquisition parameter that affects
image quantitation; in a released product it would be assessed against the notified body's change
procedure and FDA's software-change guidance, likely as a change that needs verification but no
new submission (assumption: confirm with regulatory affairs).

## Verification

CoincidenceSorter.TheWindowIsInclusive (to set its window explicitly, since it puts two singles
exactly 4,000 ps apart), CoincidenceSorter.RejectsBadConfigurations,
CoincidenceSorter.MatchesTheSimulatorsGroundTruth and
CoincidenceSorter.TheDelayedWindowEstimateDependsOnTheMultiplesPolicy at the new default;
Config.MinimalDocumentGetsDefaults (a 1.3 document no longer equals the default configuration),
Config.SchemaVersionRules and Config.ShippedConfigurationsAreValid, plus a new test that a 1.3
document without the key gets 4,000 ps and a 1.4 document 3,000 ps; the randoms measurement
`measurements/ch10/validation.txt` repeated at 3 ns; all six CI presets and static analysis.

## Decision

Pending: the software lead and the risk manager decide after the timing resolution of the scanner
is confirmed.
