# Chapter 18 measurements

Recorded 2026-10-25 on the book's machine (4 vCPU VM, Ubuntu 24.04, Clang 18, GCC 13).

| File | What | How |
|---|---|---|
| `coverage/summary.txt`, `summary.json` | Line, branch, MC/DC and function coverage per software item | `cmake --preset coverage && cmake --build --preset coverage`, then `tools/coverage.py build/coverage measurements/ch18/coverage --uncovered minidaq/src/processing/coincidence_sorter.cpp` |
| `coverage/report.txt` | llvm-cov's per-file report of the same run | written by `tools/coverage.py` |
| `coverage/ctest.txt` | The unit tests that produced the profiles (all passed) | written by `tools/coverage.py` |
| `mutation-sorter-examples.txt` | Mutants of the sorter against the example tests only | `tools/mutation_test.py minidaq/src/processing/coincidence_sorter.cpp --test '... --gtest_filter=CoincidenceSorter.*'` |
| `mutation-sorter-properties.txt` | The same with the properties | `--gtest_filter=CoincidenceSorter.*:Properties.*` |
| `mutation-sorter-final.txt` | The same after the tests written for the survivors | as above; 10 survivors, argued in `sorter-survivors.md` |
| `mutation-tracker-baseline.txt` | Mutants of the sequence tracker (`readout_packet.hpp`, lines 186 to 330) | run before the tracker property was strengthened (every packet that arrives is delivered once); the starting point of Exercise 18.5 |
| `mutation-tracker-final.txt` | The same with the solution of Exercise 18.5 | 0 survivors; a copy of `exercises/ch18/e5_kill_survivors/solution/mutation-report.txt` |
| `uniform-generator.md` | Exercise 18.2's properties with a uniform generator | four of eight seeded mistakes survive |

Notes:

- Coverage of the concurrent items (`pipeline`, `protocol`) varies by a few lines between runs of
  the same tests: the scheduler decides which branches of their threads run.
- The raw profiles (about 640 MB) and the merged profile stay in the build directory
  (`build/coverage/coverage-profiles/`, `coverage.profdata`); they can be made again.
- In the mutation reports a timeout (a mutant that makes a test loop) counts as killed. The tool
  kills the whole process group of a test that runs past its time limit.
- The 18.5 report records the SHA-256 of `readout_packet.hpp`. Any change to that header makes
  the exercise's solution check fail until the mutation run is repeated.
