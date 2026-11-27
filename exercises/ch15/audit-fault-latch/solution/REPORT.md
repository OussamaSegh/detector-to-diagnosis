# Audit report: the agent's fault latch, RC-27 (Exercise 15.6)

The control does not do what the risk file would say it does. One of the causes it names never
latches, and one of its messages is false. Both are MiniDAQ's own defects, found in the
release coverage review of 0.5.0.

## Defect 1: a board that refuses every write never latches (MDQ-PR-044)

The counter is reset by every cycle whose reads succeed, before the write of the same cycle
is counted. A board that answers reads and refuses its setpoint goes 0, 1, 0, 1: the count
never reaches 3. Its bias stays where it was, not at the setpoint the calibration assumes, and
nothing latches.

- *Test:* `Audit.ABoardThatRefusesEveryWriteLatchesAfterThreeCycles`, and
  `FailuresOfReadsAndWritesInTurnAreOneRunOfFailedCycles`.
- *Part of RC-27 left undone:* "a supply that cannot hold or reach its setpoint". The
  hazardous situation of H-10 stays open: a scan with a bias the calibration does not match,
  so energies and times are wrong without a fault. In MiniDAQ the acquisition could not start
  and nothing said why.
- *Correction:* a cycle fails if any access fails; only a cycle with every access successful
  resets the count.

The agent's test `AGoodReadResetsTheCount` encodes the defect as a requirement: it is a test
of the code as written, not of the specification.

## Defect 2: the board's own trip is reported as a reading above the limit (MDQ-PR-043)

Both causes share one message, "bias current X uA is above the limit Y uA". When only the
board's comparator tripped, the reading of the cycle is below the limit, and the message is
false: "bias current 120 uA is above the limit 500 uA".

- *Test:* `Audit.TheBoardsOwnTripLatchesAndDoesNotClaimAReadingAboveTheLimit`.
- *Part of RC-27 left undone:* the latch is right, the bias is switched off; but the record
  the operator and the investigator read is wrong. A message that contradicts its own numbers
  sends the investigation to the software's reading instead of the board, and teaches the
  operator to distrust the console.
- *Correction:* its own text: "the board switched its bias off for overcurrent", with the
  reading and the limit.

## Verdict on the claim

"Every cause latches, cite these tests as verification" is false. A control's verification
must have one test per cause the control names, written from the control's text: here a
board refusing writes had none. Request changes, and do not update the risk file until the
tests above pass.
