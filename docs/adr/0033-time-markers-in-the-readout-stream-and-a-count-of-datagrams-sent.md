# 0033. Time markers in the readout stream as words no single can be, and a count of the datagrams each board sent

Date: 2026-11-15
Status: Accepted

## Context

A coincidence sorter judges a single only once a later single shows that the single's window is
closed (ADR 0010). When a detector falls silent, its last singles wait in the sorter, and with a
calibration in the sort stage's hold buffer, until more data comes or the run ends (problem
report MDQ-PR-007). Nothing is lost, but the delay has no bound: a pause, a block that stops
counting or a low-rate live display sees its coincidences late. The sorter needs a later time,
and only the board knows that no earlier word will come.

The second gap is at the end of a run. MiniDAQ counts every datagram that a sequence gap reveals
and every datagram its socket dropped (ADR 0018), but a datagram lost on the network after the
last one that reached the software leaves no gap. Only the board knows how many it sent
(ICD-FEB version 2, open items).

## Options

1. **A host timer.** The sort stage closes windows when the clock of the host has moved on by
   more than the window. No firmware change; but the host's clock says nothing about the board's
   time stamps, and a word delayed in a switch or a socket would then arrive after its window was
   judged: a promise the host cannot keep.
2. **A new datagram type** carrying the time, in MDQ-R version 2. Clean on the wire, but a
   breaking change of the data format: every receiver must change at once (major version).
3. **A marker word inside MDQ-P1**: a word whose crystal ID (32767) is outside every scanner
   (MiniDAQ's has 18,432 crystals) and whose energy code is saturated (2047), carrying a time.
   A receiver that does not know it drops it as an invalid single, as it already does; a
   receiver that knows it takes it as a promise from the board, in the board's own time.
4. **For the count of datagrams**: the sequence number of the last datagram, sent in a
   final datagram (lost like any other); or a register the slow-control loop reads every cycle.

## Decision

- **Option 3**, MDQ-P1 revision 1.1, with register map 1.2 for firmware 1.3: `marker_enable`
  in `control`, `marker_interval` in microseconds (100 by default). The marker travels the
  pipeline as `Batch::marker_ps`, not as a single, so no stage after the decoder can mistake it
  for one, and it is counted apart from the filtered words, which the integrity verdict counts as
  a loss. The sort stage moves it earlier by the largest time offset of the calibration, because
  the promise holds for the board's raw times and the calibration moves singles by up to that
  much; it then also releases the held singles below it. The sorter's new `advance` closes the
  windows a single at the promised time could not join, nothing more: the same coincidences and
  counters as without markers, in both window modes, which the tests check.
- **A register, `datagrams_sent`** (option 4, the second), reset when the triggers go on and read
  every cycle; the integrity verdict counts the datagrams the boards sent beyond those the link
  delivered or counted as lost, but only when every board reports a count, so that a mix with
  older firmware falls back to what was checked before.
- Both only with firmware 1.3 or later: the slow-control loop reads the minor version it already
  checks (ADR 0019) and touches neither register on older firmware. Control API 2.5 shows both.

## Consequences

### Positive

- A silent detector's last coincidences come out within the marker interval plus the window,
  not at the end of the run (`Pipeline.AMarkerDeliversTheLastCoincidencesWhileTheSourceIsSilent`).
- The loss on the network after the last datagram can no longer be silent: RC-30 covers it.
- Old firmware and old decoders keep working: the change adds registers, a field bit and a word
  that was already invalid.

### Negative

- The sorter now trusts the board's promise. A firmware that sends a marker before a word with
  an earlier time makes that word out of order; it is counted and ends the run in a fault
  (RC-07), so the error is loud, but the run is lost. ICD-FEB version 3 states the promise as an
  assumption the firmware team must confirm.
- A marker takes a word of the link at every interval: at 100 us, 10,000 words (80 kB) per
  second per board, 0.06% of a 1 Gbit/s link. On a slower link the interval is raised in the
  slow-control settings; the latency bound grows with it.
- The simulated board counts its datagrams from its FIFO model, not from the simulated link, so
  a simulated board must report firmware 1.2 when the UDP detector is used (ICD-FEB, open items).
