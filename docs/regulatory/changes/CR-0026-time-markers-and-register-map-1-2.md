# CR-0026: Time markers in the readout stream and register map 1.2

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-15, by the software lead |
| Source | problem report MDQ-PR-007; the open item of ICD-FEB version 2 on datagrams sent (residual of ADR 0018); roadmap 2.0.0, theme B |
| Decision | approved, 2026-11-15, under the software lead's standing delegation of 2026-11-15 |
| Commits | 19c4c84 |

## Description

The front-end boards of firmware 1.3 put time markers into their data stream, and MiniDAQ uses
them to close coincidence windows while a detector is silent. A marker is an MDQ-P1 word that no
single of the scanner can be: crystal 32767, energy code 2047, and a time that promises that no
later word of the same stream has an earlier time (MDQ-P1 revision 1.1). The same firmware counts
the datagrams each board sends, and the run's integrity verdict counts those that never reached
the software as a loss.

1. **Format.** `packed::marker`, `packed::is_marker`; the stream decoder counts markers, unwraps
   their time like a single's and reports the latest one with `take_marker()`. A marker is not an
   invalid single (SRS-FMT-013 amended, SRS-FMT-014).
2. **Sorter.** `CoincidenceSorter::advance(t)` closes every window that no single at or after
   `t` could join (SRS-SRT-014).
3. **Pipeline.** The decode stage passes the marker in `Batch::marker_ps`; with a calibration the
   sort stage moves it earlier by the largest time offset of the table, so that the promise
   still holds for corrected times, and releases the held singles below it; the pair stage calls
   `advance`. Markers are counted in `pipeline.markers()`, not as filtered words, which the
   integrity verdict would count as a loss (SRS-PIPE-013).
4. **Register map 1.2** (`hw/feb.toml`, firmware 1.3): `control.marker_enable` (bit 2),
   `datagrams_sent` (0x018, ro), `marker_interval` (0x01C, rw, microseconds, reset 100). The
   slow-control loop switches the markers on with the triggers and reads the count every cycle,
   only on firmware 1.3 or later (SRS-HW-016). The simulated board implements them.
5. **Integrity.** When every board reports its datagrams sent, the excess over the datagrams the
   link delivered or counted as lost is recorded as `/hardware/datagrams_unaccounted`, a loss
   (SRS-HW-017, risk control RC-30).
6. **Control API 2.5.** Each board in `hardware` gains `markers` and `datagrams_sent` (null
   without firmware 1.3); the decode stage gains `markers` (SRS-HW-007 extended).
7. **Simulation.** `sim::encode_with_markers` and `minidaq_send --marker-interval-us N` send
   markers on the simulated link.

## Reason

MDQ-PR-007: a sorter can judge a single only once a later single shows that its window is
closed, so when a source falls silent its last coincidences wait until more data comes or the
run ends. A run that pauses, a block that stops counting, or the live display at a low rate sees
coincidences late, by an amount without bound. A marker gives the sorter the later time it needs
without a single. The datagram counter closes the one loss that MiniDAQ could not yet see: the
datagrams dropped on the network after the last datagram that reached the software, which no
sequence gap reveals (ADR 0018, ICD-FEB section 8). Without the change both stay as recorded
residuals.

## Impact analysis

### Requirements

Added: SRS-FMT-014, SRS-PIPE-013, SRS-SRT-014, SRS-HW-016, SRS-HW-017. Changed: SRS-FMT-013 (a
marker is not an invalid crystal) and SRS-HW-007 (the boards' new fields). SRS version 29.
Verification repeated: every requirement of the items format, sorter, pipeline, hw and service
(the whole unit suite), and SRS-PIPE-010, whose reference must still match with markers in the
stream.

### Software items and safety class

Items format, sorter, pipeline, hw, service, sim and the app `minidaq_send`. No class changes:
the sorter and pipeline are class B as before, and the markers change no coincidence (the tests
compare the output with and without markers, in both window modes and with a calibration).

### Risk

Hazard H-01 (data lost without notice): RC-30 gains SRS-HW-017, a new protective measure for the
loss on the network after the last datagram; the estimate after the controls does not change, as
the residual was already "loss can no longer be silent" for every other path. A new failure mode
is a marker whose time is too late, which would make the sorter judge a window before a single
that belongs to it arrived: the single is counted as out of order (SRS-SRT-009), which the integrity
verdict counts as a loss and the service ends the run on (RC-07), so the loss is not silent. A
new row of the sorter's FMEA records it (`fmea-sorter.json`, function windowing). The firmware's side of the promise is an assumption of ICD-FEB version 3.

### SOUP

None.

### Interfaces and data formats

MDQ-P1 revision 1.1 (a word that was an invalid single is now a marker; a decoder of revision
1.0 still drops it and counts it as invalid). Register map 1.2 (additions only, firmware minor
version 1.3: section 3 of ICD-FEB). Control API 2.5 (new fields only, ADR 0013). The list-mode
file format and the run record's schema do not change: markers never reach the writer, and the
integrity verdict's losses are a list that already takes new pointers.

### Documents

The SRS, version 29; ICD-FEB, version 3; the register map, version 1.2 (generated); ADR 0033;
the risk file (RC-30); problem report MDQ-PR-007, closed; the trace matrix; Chapters 10, 23 and
24 and the architecture appendix; the CHANGELOG.

### Regulatory

None: the intended use does not change and no safety-relevant function is removed. The change is
an addition to a released interface and is recorded for the next release (1.3.0).

## Verification

Tests: `TimeMarker.IsAWordThatNoSingleOfTheScannerCanBe`,
`StreamDecoder.ReadsAMarkerAsAPromiseNotASingle`, `StreamDecoder.UnwrapsAMarkerLikeASingle`,
`CoincidenceSorter.AMarkerClosesTheWindowsBeforeIt`, `CoincidenceSorter.MarkersChangeNoCoincidence`,
`ReadoutLink.SendsAMarkerAtEveryIntervalBeforeTheDataAfterIt`,
`Pipeline.AMarkerDeliversTheLastCoincidencesWhileTheSourceIsSilent`,
`Pipeline.MarkersChangeNoCoincidence` (with a calibration whose offsets differ: without the shift
of the marker it fails with 246 singles out of order), `FakeBoard.HasTheRegistersOfMap12OnlyWithFirmware13`,
`SlowControl.SwitchesTheTimeMarkersOnWithTheTriggersAndReadsTheDatagramsSent`,
`RunIntegrity.DatagramsTheBoardsSentButTheLinkNeverSawAreALoss`; `docs.regmap`, `docs.trace`,
`docs.baseline`, `docs.changes`, `docs.risk`; the whole ctest.

## Decision

Approved on 2026-11-15 under the standing delegation that the software lead gave on 2026-11-15
for the work towards 2.0.0, after reading the impact analysis above; the code had been written and
tested before the decision, and nothing of it was merged before it.
