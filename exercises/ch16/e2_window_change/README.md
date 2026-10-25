# Exercise 16.2 (M): A change request for a 3 ns window

**Goal.** The physics lead wants the default coincidence window to go from 4 ns to 3 ns. Write the
change request, with an impact analysis that finds everything the change touches, and add two
rules to the change request checker.

**Time.** 90 minutes.

**Starter.** `starter/change.py` has the rules of `tools/check_changes.py` without git, and a
TODO for two more. `starter/CR-0010-coincidence-window-3ns.md` is the first draft that the
physics lead sent: short, confident, and wrong in several places.

**Acceptance** (`tests/test_window_change.py`, run by CTest as
`ch16/e2_window_change/<variant>/unittest`):
- `check()` also reports a change that lists commits before it is implemented, and a test named
  in the Verification section that does not exist (whatever the status). `tests/known.json`
  lists MiniDAQ's requirement IDs, risk file IDs and test names at tag `ch15`.
- The request passes the rules and is still `proposed`. It names SRS-CFG-001, SRS-SRT-001 and
  SRS-SRT-011 under Requirements; H-04, H-07, RC-12 and RC-16 under Risk; schema version 1.4
  under Interfaces and data formats; `minidaq/configs/default.json`, the architecture and the
  known anomalies under Documents; the tests that use the default window and the randoms
  measurement under Verification; and marks its physics assumption `assumption: confirm`.

Then answer in `NOTES.md`: the physics lead says "it is only a default, just change the
number". What do you answer, in a few sentences?

**Hints.** Search the repository for `4'000`, `4000`, `4 ns` and `104 ns`. Read the versioning
comment at the top of `minidaq/include/minidaq/config/acquisition_config.hpp`: what does an old
document that omits the window mean after the change? Requirements that do not exist yet have
no ID; describe them in words.
