# Exercise 15.5 (E, extra): The risk matrix and the overall residual risk

**Goal.** Draw MiniDAQ's risk matrix before and after risk control from the risk file, and
compute what must be resolved or justified before the overall residual risk can be accepted.

**Time.** 45 minutes.

**Starter.** `starter/risk_matrix.py` always places hazards by their probability before
control, and `overall()` ignores open hazards and gives no reasons.

**Acceptance** (`tests/test_risk_matrix.py`, run by CTest as
`ch15/e5_residual_risk/<variant>/unittest`, on a copy of MiniDAQ's `hazards.json`):
- `matrix()` places every hazard in exactly one cell, by its probability before or after
  control as asked.
- `render()` draws severities S4 to S1 as rows and P1 to P5 as columns, and marks every cell
  the criterion does not accept with `*`.
- `overall()` is not acceptable while a hazard is open or a closed hazard's residual risk is
  above the criterion, and gives a reason for each; closed, acceptable hazards give none.

Then answer in `NOTES.md`: MiniDAQ 0.3 is released with H-08 open. Write the two or three
sentences that would justify that in a release record, or explain why they cannot be written.

**Hints.** The criterion is the plan's: severity index plus probability index at most 5. The
benefit-risk judgment is not mechanical; the tool lists what the judgment must address.
