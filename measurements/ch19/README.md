# Chapter 19 measurements

Recorded 2026-10-25 on the book's machine (4 vCPU VM, Ubuntu 24.04, Clang 18, GCC 13).

| File | What | How |
|---|---|---|
| `soak/` | The 30-minute soak at 1,000,000 singles/s (SRS-SYS-003), with its deviation | `tools/soak.py build/release/minidaq/apps measurements/ch19/soak --minutes 30`; see `soak/README.md` |
| `coverage/summary.txt`, `summary.json`, `report.txt`, `ctest.txt` | Coverage per software item of the unit and system tests together | `cmake --preset coverage && cmake --build --preset coverage`, then `tools/coverage.py build/coverage measurements/ch19/coverage` |
| `system-test-report.md`, `.log` | The system test report of the `release` build of the Chapter 19 commit | `tools/test_report.py build/release measurements/ch19/system-test-report.md` |

## Coverage review of `ctl` and `server` (closes MDQ-PR-015)

Before Chapter 19, the unit tests reached 6 of the 237 lines of `minidaq_ctl` and none of its
branches, and did not run `minidaq_server` at all (`measurements/ch18/coverage/`). With the
system tests:

| Item | Lines | Branches | MC/DC | Functions |
|---|---|---|---|---|
| `ctl` | 81.9% (194/237) | 77.0% (97/126) | 50.0% (7/14) | 100.0% (11/11) |
| `server` | 80.4% (123/153) | 81.1% (73/90) | 50.0% (10/20) | 100.0% (1/1) |

The composition that MDQ-PR-015 named is now tested: the client verifies the server's certificate
before it sends its token (two impostor servers receive no byte), refuses a missing token file,
and reports a closed or absent server with the exit status `2`.

The branches not taken both ways (`tools/coverage.py ... --uncovered minidaq/apps/<file>.cpp`)
fall into four groups, each accepted for this release with its reason:

- **Failures of the operating system** that a test cannot cause without fault injection below
  the program: `socket()`, `send()` and `recv()` errors, `sigwait()` on an invalid set (client
  lines 54, 88, 125, 142; server line 175), and random numbers unavailable for a token (client
  171). Their code is one message and the exit status `2`.
- **Failures of TLS set-up and I/O** after the handshake (client lines 118 to 135, 221; server
  110): a TLS context that cannot be created, a connection closed in the middle of a record. The
  handshake failures that matter for hazard H-08 are tested.
- **Option parsing variants**: an option given without its value, `--help`, `--port` out of range
  in the client, the `wait` deadline argument left out or invalid (client lines 194 to 216,
  256 to 261; server lines 52 to 68 for each option without a value). Each is a usage message and
  the exit status `2`, the same code that the tested usage errors take.
- **Rare server paths**: a token store that fails to load after its checks, an audit trail that
  cannot be opened or written, a start-up token that cannot be written, and the configuration
  given at start-up that the service then refuses (server lines 92 to 101, 129, 147, 161, 189).

Line numbers are those of the measured commit; they move with the code.
