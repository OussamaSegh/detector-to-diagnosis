# CAPA-0003: Input values at the limits of their types

| Field | Value |
|---|---|
| Status | implemented |
| Opened | 2026-10-25, by the software lead |
| Source | MDQ-PR-001, MDQ-PR-002 |
| Owner | software lead |
| Effectiveness check | release 0.5.0 |

## Problem

Two defects of the same kind reached the main branch and were found by fuzzing, not by unit
tests: the configuration reader crashed on `6e688`, a number outside the range of `double`
(MDQ-PR-001), and the sequence tracker counted a jump of exactly 2^31 as two billion lost
packets (MDQ-PR-002). Both inputs are at the limit of their type.

## Investigation

Every function that reads input from outside the process was listed from `fuzz/README.md`: seven
fuzz targets cover the stream decoder, the raw format, the configuration reader, the control
protocol, the packet parser and sequence tracker, the sorter and merger, and the list-mode
reader. For each, the unit tests were read for values at the limits of each field's type and
valid range. Typical values were tested everywhere; limits were tested where a requirement
named them (the range checks of SRS-CFG-004), and nowhere else. The two defects were the limits
that no requirement named: the range of `double` behind a JSON number, and the distance of
exactly half the sequence space, where serial-number arithmetic is undefined.

## Root cause

Unit tests were written from the requirements' examples, and no rule asked for the limits of the
type that carries an input, so a limit appeared in a test only when a requirement happened to name
it. Fuzzing found both, but by chance: `6e688` in a 20-second smoke run, and the jump of 2^31 after
about 240,000 executions of a 2-minute run, from seeds that hold typical values (`fuzz/README.md`).

## Correction

Both defects are fixed and tested: `Config.NumberOverflowIsAnErrorNotACrash` and
`SequenceTracker.AJumpBeyondTheMaximumGapIsARestart`; both crash inputs are in the seed corpus.

## Corrective action

A rule for `docs/coding-standard.md`: a function that reads external input has unit tests at the
limits of every field, for its type (minimum, maximum, and for floating point infinity, NaN and
out-of-range text) and for its valid range (each limit and one past it). The review checklist in
`docs/regulatory/changes/README.md` gains the question "does every new input field have tests at
its limits?".

## Preventive action

The seed corpora in `fuzz/corpus/` get one seed per field at each limit of its type, so that
the 60-second smoke runs of every CI push start from the limits instead of reaching them by
chance; the fuzz targets themselves are in `fuzz/`.

## Verification of the actions

The new tests and seeds pass in all six CI presets and in the fuzz smoke runs; no requirement
changes, because the tests check behavior the requirements already demand.

## Effectiveness check

Criterion: the 10-minute campaigns of all 7 fuzz targets at releases 0.4.0 and 0.5.0 find 0
defects at a limit of a type, and every input function added before 0.5.0 has a limit test
(review of its tests).
Due: release 0.5.0.
Result: filled in at the check.

## Closure

Not closed: the effectiveness check is due at release 0.5.0.
