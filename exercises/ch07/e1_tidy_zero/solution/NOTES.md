# Exercise 7.1: notes on the solution

clang-tidy 18 with MiniDAQ's `.clang-tidy` reports 15 findings in the starter
(`python3 exercises/ch07/e1_tidy_zero/tests/tidy_clean.py starter`):

| Finding | Count | Real bug? |
|---|---|---|
| `cert-err34-c` on `atoi`, `atof` | 3 | Yes. `--port 7OO` gives port 7, `--port 65536` gives port 0 (any free port), `--rate fast` gives 0. |
| `cert-err33-c` on `fclose` | 2 | Yes in `close()`: on a full disk the data is lost at the flush inside `fclose`, and `close()` reported success. In the destructor there is nobody to report to, so `(void)` with a reason is the honest fix. |
| `cppcoreguidelines-owning-memory` | 3 | The design smell behind several others: a raw owning `FILE*`. |
| `cppcoreguidelines-prefer-member-initializer` | 1 | No, style. Gone with the `unique_ptr` member. |
| `cppcoreguidelines-special-member-functions` | 1 | Not yet a bug: copying was deleted, moving was not declared. A `unique_ptr` member makes the class move-only by itself (rule of zero). |
| `cppcoreguidelines-init-variables`, `bugprone-assignment-in-if-condition`, `clang-analyzer-deadcode.DeadStores` | 3 | One line, no bug, and `n` was never needed: the variable goes. Three checks, one finding. |
| `concurrency-mt-unsafe` on `strerror` | 1 | Yes in a multi-threaded program: `strerror` may return a buffer shared between threads. |
| `modernize-use-nodiscard` on `is_open` | 1 | No, but `[[nodiscard]]` on `write` and `close` (which the check does not suggest, because they are not `const`) is what makes their callers check the result. |

Three bugs are not reported at all:

- `fputs` and `fputc` return values are ignored. MiniDAQ's configuration removes
  them from `cert-err33-c` because the command-line tools use them for terminal
  output. Here they write a file, and the exclusion hides a real bug. Every
  suppression trades findings for noise; review has to cover what it hides.
- `write()` on a file that failed to open dereferences a null `FILE*`.
- A failed parse leaves the options half-applied.

The tests find all three. A static analyzer finds patterns; tests define
behavior. You need both.

The solution suppresses one check, twice, with a reason: `owning-memory` on
`fopen` and `fclose`, where the check cannot see that the `unique_ptr` and its
deleter are the owners.
