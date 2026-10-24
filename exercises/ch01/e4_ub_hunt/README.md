# Exercise 1.4 (H): Five seeded undefined-behavior bugs

**Goal.** `starter/ub_snippet.cpp` contains five functions from an imaginary DAQ
utility library. Each one has exactly one undefined-behavior bug. Find and fix all five
**using the sanitizers only**: do not read the code looking for bugs until a sanitizer
has pointed you at a line. Then write one sentence per bug in `FINDINGS.md`: the UB
class (lifetime, bounds, overflow, alignment/aliasing, uninitialized or invalid shift),
the sanitizer that caught it, and the fix.

**Time.** 90 minutes.

**How.**
```bash
cmake --preset asan-ubsan -DMINIDAQ_BUILD_STARTERS=ON
cmake --build --preset asan-ubsan --target ch01_e4_ub_hunt_starter
ctest --preset asan-ubsan -R e4_ub_hunt/starter
```
In a plain Release build most of these tests *pass*. That is the point of the exercise:
UB often looks like working code until the optimizer, the input or the platform changes.

**Acceptance.** All tests in `tests/test_ub.cpp` pass under `asan-ubsan` with no
sanitizer report, and `FINDINGS.md` names all five bugs. One bug is only visible to
UBSan with `-fsanitize=shift` and one only to ASan, so you need both.
