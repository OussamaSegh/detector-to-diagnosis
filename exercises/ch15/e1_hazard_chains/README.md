# Exercise 15.1 (M): Ten hazard chains for MiniDAQ

**Goal.** Write ten hazard chains for MiniDAQ, from hazard through a sequence of events and a
hazardous situation to harm, rate each before risk control, and write the checker that
catches the mechanical mistakes of a chain document.

**Time.** 2 hours.

**Starter.** `starter/chains.py` uses the wrong acceptability criterion and checks only that
every field is present. `starter/hazards.json` has a colleague's first three chains; one of
them is not a chain, and one is rated wrongly.

**Acceptance** (`tests/test_chains.py`, run by CTest as
`ch15/e1_hazard_chains/<variant>/unittest`):
- `acceptable()` applies the criterion of MiniDAQ's risk management plan: severity index plus
  probability index at most 5.
- `problems()` reports an empty field, a duplicate ID, an unknown category, a chain whose
  hazard, hazardous situation and harm are not three different statements, a severity or
  probability off its scale, and an `acceptable` that is not the boolean the criterion gives.
- `hazards.json` has at least ten chains without problems, covers the categories data loss,
  timing, file integrity, identification and quantitation, has at least one risk that is not
  acceptable before control, and says in at least eight words how each sequence happens.

Then answer in `NOTES.md`: which of your chains would a hardware engineer rate differently,
and why does that not change the software's rating?

**Hints.** The criteria are in `docs/regulatory/risk/hazards.json`. Rate the probability of
harm with the software's failure taken as certain: what happens after the failure decides it.
MiniDAQ holds no patient identity; think about what "identification" can still mean for it.
