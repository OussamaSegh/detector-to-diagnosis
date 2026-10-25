# Exercise 14.1 (M): Classify MiniDAQ's software items

**Goal.** Assign an IEC 62304 safety class to each MiniDAQ component (simulator, sorter,
writer, control API, audit log, client) with a justification, and write the checker that
catches the mechanical mistakes of a classification.

**Time.** 1.5 hours.

**Starter.** `starter/classes.py` checks only that each shipped item has a class at least as
high as its worst hazard implies. `starter/minidaq-items.json` is a first attempt by a
colleague: it has several mistakes of the kinds the chapter describes.

**Acceptance** (`tests/test_classes.py`, run by CTest as
`ch14/e1_item_classes/<variant>/unittest`):
- `problems()` reports an item whose class is below what its worst hazard implies, an unknown
  hazard, a shipped item without a class or rationale, and an item that is not shipped but
  has a class or does not say why it is not shipped.
- `problems()` reports an item whose class is lower than another item's in the same process
  (nothing segregates them), but accepts a lower class in a separate process.
- `problems()` reports a system class that is not the class of its highest item.
- `minidaq-items.json` passes `problems()`, classifies every component as shipped, gives the
  sorter, the writer and the control API at least one hazard and a class above A, gives every
  item a rationale of at least 12 words, and an item without a hazard of its own says what its
  class rests on (its process, or segregation).

Then answer in `NOTES.md`: a colleague proposes moving the audit log into its own process so
that it can be class A. What would the team gain, what would it cost, and what would the
segregation argument have to show?

**Hints.** The severities are after risk controls outside the software (image review, quality
control); they are the team's judgment, recorded with their reason. MiniDAQ's own
classification is `docs/architecture/software-items.json`, checked by `tools/check_items.py`.
