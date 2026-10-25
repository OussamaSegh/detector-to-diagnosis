# Exercise 15.3 (H): An FMEA of the coincidence sorter

**Goal.** Do a full failure modes and effects analysis of MiniDAQ's coincidence sorter,
against its code, and write the checker for the mechanical rules of an FMEA.

**Time.** 4 hours.

**Starter.** `starter/fmea.py` checks only that every field is present and every function has
a row. `starter/fmea-sorter.json` is a colleague's first three rows; each has a mistake.

**Acceptance** (`tests/test_fmea.py`, run by CTest as `ch15/e3_sorter_fmea/<variant>/unittest`):
- `problems()` reports an empty field, a function that is not one of the sorter's, a function
  without a failure mode (the order check and windowing need two), the same failure mode twice,
  a severity off the scale S1 to S4, an effect that names no hazard `H-nn`, a control that is
  not a requirement of `tests/sorter-requirements.md`, a new control (`NEW: ...`) that is not a
  requirement with "shall" of eight words or more, and an undetected failure (detection
  starting with "none") without a new control.
- `fmea-sorter.json` passes, has at least twelve rows, uses the accounting identity
  (SRS-SRT-009) as a control, and proposes at least one new requirement.

Then answer in `NOTES.md`: for one row, explain why an occurrence rating would not help, and
what you rated instead.

**Hints.** Work through `minidaq/src/processing/coincidence_sorter.cpp` function by function,
not from memory: for each comparison, ask what happens one picosecond or one keV either side;
for each loop, ask what happens with zero, one, two or many singles; for each choice between
candidates, ask what decides a tie. The hazards are those of `docs/regulatory/risk/hazards.json`.
