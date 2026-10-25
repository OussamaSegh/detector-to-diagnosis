# Exercise 20.3 (M): Test the gate, then test the test

**Goal.** Write a self-test for a small gate, in the style of `tools/gate_selftest.py`: a
correct tree it must accept, faults it must catch, and a verdict that tells "caught" from "not
caught", "failed for another reason" and "fails on correct code". Then find out whether your
self-test would notice a broken gate: the acceptance tests run it against seven broken versions
of the gate, and each must leave at least one of your faults not caught.

**Time.** 60 minutes.

**Starter.** `starter/selftest.py`: the correct tree, the `Fault` record, and empty `FAULTS`,
`verdict()` and `run()`. The gate is `tests/gate.py` (read its promise; do not change it); the
broken versions are in `tests/mutants.py` (read them only after your first attempt).

**Tasks.**
1. `verdict(clean, problems, expect)`, with the four outcomes above.
2. `run(check, faults)`: for each fault, a fresh correct tree, the control, the fault, the
   verdict.
3. `FAULTS`: at least four faults, each with the pattern the gate's report must match.

**Acceptance** (`ch20/e3_gate_selftest/<variant>/unittest`): the real gate catches every fault
for its reason; the verdicts; no broken gate passes your self-test.

Then answer in `NOTES.md`: which broken gate did your first set of faults not notice, and what
does that say about choosing the faults of `tools/gate_selftest.py`?
