Trace review of the change to `minidaq/src/processing/coincidence_sorter.cpp`. The repository was read at the eval's base checkout.

**Findings, most serious first**

4. Changed behavior without a changed requirement: `minidaq/src/processing/coincidence_sorter.cpp`, line 51 (in `validate`).
   - Evidence: the check changes from `c.window <= Picoseconds{0}` to `c.window < Picoseconds{0}`, so the sorter now accepts a coincidence window of 0 ps.
   - Why it matters: SRS-SRT-007 (`docs/regulatory/srs.md` line 114), which the change leaves unchanged, says the sorter "shall reject a configuration with a window outside 1 to 1,000,000 ps". The new code breaks a requirement that is still in force.
   - Item class: the code belongs to the item `sorter`, which is class B and carries hazard HZ-1 (`docs/architecture/software-items.json`).
   - Other mismatch: the error message on line 52 still says "window must be in (0, 1 us]", which no longer matches the check.
   - Fix (one sentence): put back `<=`, or, if a 0 ps window is wanted, change SRS-SRT-007 and its tests and assess RC-17 together with the code.

3. Risk control without its verification: RC-17 (`docs/regulatory/risk/hazards.json` line 146).
   - Evidence: RC-17 says "Sorter configurations outside their valid ranges are rejected", names SRS-SRT-007 and SRS-CFG-011, and gives `CoincidenceSorter.RejectsBadConfigurations` as its evidence. This change weakens the control itself, because a 0 ps window is now accepted.
   - The existing verification contradicts the new code: `minidaq/tests/unit/test_coincidence_sorter.cpp` line 264 has `EXPECT_TRUE(bad([](SorterConfig& c) { c.window = Picoseconds{0}; }))`. With this change that assertion should fail. I reasoned this from the code; I did not run the test.
   - So the change brings no passing verification for RC-17 in its new form. The trace matrix (`docs/regulatory/trace-matrix.md` line 249) and the hazard file still claim RC-17 is verified.
   - Fix (one sentence): the sorter change must not merge while RC-17's evidence test fails or is weakened to match it.

No finding of type 1 or 2: the change adds or changes no requirement and adds no test.

**What I read**
- `docs/regulatory/srs.md` (the SRS-SRT rows)
- `docs/regulatory/trace-matrix.md` (the SRS-SRT-007 row)
- `docs/regulatory/risk/hazards.json` (RC-17)
- `docs/architecture/software-items.json`
- `minidaq/src/processing/coincidence_sorter.cpp`, lines 40-60
- `minidaq/tests/unit/test_coincidence_sorter.cpp`, lines 250-300
- `minidaq/src/config/acquisition_config.cpp` (grep for the window checks only)

I did not read `tools/trace_matrix.py` in full. I relied on the `// REQ:` tags I found with grep.

**What I could not check**
- I did not build the code or run the tests, so the failure of line 264 is inferred, not observed.
- I did not check whether the config reader (SRS-CFG-011, `acquisition_config.cpp`) rejects `window_ps = 0` before the sorter's `validate` is reached. If it does, the effect at system level may be hidden, but the sorter item's requirement is still broken.
- I did not check whether `docs/regulatory/risk/fmea-sorter.json` (which names SRS-SRT-007 at line 181) needs a matching update.
- I did not check what a 0 ps window does downstream (for example in the delay check `c.delay <= c.window`, or in pairing under SRS-SRT-001).
