# Exercise 7.1 (M): Get a legacy file to zero findings

**Goal.** `starter/legacy_tool.cpp` parses a command line and writes records to
a file. It works on the happy path. Run clang-tidy with MiniDAQ's curated
configuration over it, triage every finding (real bug, latent bug, or style),
and fix them until clang-tidy reports nothing, without a suppression you
cannot justify in one sentence. Then make the behavior tests pass: they find
bugs that clang-tidy does not.

**Time.** 2 hours.

**Run.**

```
python3 exercises/ch07/e1_tidy_zero/tests/tidy_clean.py starter    # the findings
ctest --preset debug -L starter -R ch07/e1                         # the behavior
```

(Configure with `-DMINIDAQ_BUILD_STARTERS=ON` for the second command.)

**Acceptance.**
- `tidy_clean.py starter` reports 0 findings (CTest `ch07/e1_tidy_zero/<variant>/clang-tidy`).
- `tests/test_legacy_tool.cpp` passes: strict option parsing (`7OO`, `65536`, `inf`
  and negative values rejected, all-or-nothing), a full disk reported by `close()`
  (`/dev/full`), no crash when the file did not open.
- Each remaining `NOLINT` names one check and gives a reason.

**Hints.** `minidaq/core/parse_number.hpp` exists. Which finding hides two
others on the same line? Which bug is in a function that clang-tidy was told
not to check, and why was it told that?
