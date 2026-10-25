# MiniDAQ gate self-test

Commit `27a2b53902cd`, 2026-10-25 21:17 UTC, written by `tools/gate_selftest.py`. Each gate
ran on the unchanged checkout (control) and then with one planted fault.

| Fault | Gate | Planted | Control | With the fault | Verdict |
|---|---|---|---|---|---|
| `warning` | build: warnings are errors | an unused function in a library source | pass | fail | caught |
| `unit` | unit tests | the slicing-by-8 CRC reads byte 6 twice instead of bytes 6 and 7 | pass | fail | caught |
| `system` | system tests | the client exits with 0 when the server refuses its token | pass | fail | caught |
| `tidy` | static analysis: clang-tidy | a pointer initialized with 0 | pass | fail | caught |
| `cppcheck` | static analysis: cppcheck | an array read one past its end | pass | fail | caught |
| `layers` | architecture: layers | the core includes the application layer | pass | fail | caught |
| `trace` | trace matrix | a test loses the tag of the only requirement it verifies | pass | fail | caught |
| `srs` | requirements in testable form | a requirement that cannot be verified | pass | fail | caught |
| `soup` | SOUP list | a dependency pin changed without the SOUP list | pass | fail | caught |
| `document` | document control | a controlled document changed without a new version | pass | fail | caught |
| `waits` | test waits (CAPA-0001) | a test that sleeps without a reason | pass | fail | caught |
| `hardening` | hardening of the shipped programs | a program linked without PIE and BIND_NOW | pass | fail | caught |
| `perf` | performance regression gate | the pipeline benchmark 20% slower | pass | fail | caught |
| `asan` | AddressSanitizer | a heap read one past the end | pass | fail | caught |
| `tsan` | ThreadSanitizer | two threads increment one int | pass | fail | caught |

15 of 15 faults caught for the planted reason.
