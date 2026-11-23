1. `minidaq/tests/unit/test_config.cpp`, line 38 (the removed line `// REQ: SRS-CFG-001` in `TEST(Config, MinimalDocumentGetsDefaults)`): after this change, no test names SRS-CFG-001, a requirement verified by test (`docs/regulatory/srs.md` line 172, item config, method T). A repository-wide search turned up this tag as the only test that names it. The only other match is a string inside the gate self-test, `tools/gate_selftest.py` lines 76-77, which is a negative fixture that expects the error "SRS-CFG-001: verified by test, but no test names it", not a real test. So `tools/trace_matrix.py --check` should now fail with that error. The committed `docs/regulatory/trace-matrix.md` line 35 still lists Config.MinimalDocumentGetsDefaults as the test, so the `docs.trace` check would also report the matrix as out of date. Strictly, the change does not add or alter the requirement text; it removes the only test link to an existing requirement, which is why I placed it under 1. The test body itself is unchanged; only the trace link is lost. Fix: put the tag back, or name SRS-CFG-001 in another test.

There are no findings under 2, 3 or 4:
- 2: the change adds no test.
- 3: no risk control in `docs/regulatory/risk/hazards.json` names SRS-CFG-001 or this test. I searched every string field of the JSON for "CFG-001". So this removal weakens the verification of a requirement of the class B item `config` (hazard HZ-3), but not that of a named risk control.
- 4: the change touches no code under `minidaq/src/config/` or `minidaq/include/minidaq/config/`, nor any other class B item path.

What I read:
- `docs/regulatory/srs.md` (the SRS-CFG rows)
- `docs/regulatory/trace-matrix.md` (row of SRS-CFG-001)
- `docs/regulatory/risk/hazards.json` (searched for SRS-CFG-001 and the test name)
- `tools/trace_matrix.py` (tag format, and TEST_DIRS, which includes `tools/`)
- `tools/gate_selftest.py` lines 76-77
- `docs/architecture/software-items.json` (the config item is class B, hazard HZ-3)
- `minidaq/tests/unit/test_config.cpp` lines 30-50

What I could not check:
- I did not run `tools/trace_matrix.py --check` or the tests; the failure above is inferred from reading the tool.
- I did not read every hazard control in full, only searched it for SRS-CFG-001 and the test name. So a control that relies on SRS-CFG-001 without naming it would not have shown up.
