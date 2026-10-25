# MiniDAQ software system test plan

Version 1 (MiniDAQ 0.4.0-dev, Chapter 19). Status: draft for review.

This plan says how MiniDAQ is tested as a whole: the programs that ship, run together as an
operator runs them. It covers the topics that IEC 62304 expects of software integration and
system testing for a teaching project; it is not a document of the manufacturer's quality management
system and does not reproduce the standard. Unit verification is in the
[development plan](../sdp.md), section 6; this plan adds the levels above it.

## 1. Scope

- **Under test:** `minidaq_server` and `minidaq_ctl`, built from one commit with one preset,
  with the libraries they link (`minidaq_core`, `minidaq_control`).
- **Test tools, not under test:** `minidaq_send` (plays a readout board: simulates singles,
  cuts them into MDQ-R1 packets, injects loss, delays and duplicates, and reports what it did),
  `minidaq_listmode` (checks the files), the harness `minidaq/tests/system/systest.py`, the
  statistics `minidaq/tests/system/stats.py`, `tools/soak.py` and `tools/test_report.py`.
  They are verified as tools: `stats.py` by `test_stats.py` against tabulated values and for
  calibration, the others by the negative controls of section 4; the [tool list](tools.md)
  records each with the reasons it is trusted.
- **Not in scope here:** the acquisition PC, the operating system tuning (Chapter 4) and a real
  readout board. Section 6 says what a bench with hardware adds.

## 2. Test levels

| Level | What it verifies | Where | Runs |
|---|---|---|---|
| Unit | one unit against its specification in its header, through its interface | `minidaq/tests/unit/`, label `unit` | every change, six presets |
| Integration | units put together in one process: the pipeline with its stages, the service with its ports, the control server with the service | `minidaq/tests/unit/` (for example `test_pipeline.cpp`, `test_acquisition_service.cpp`, `test_service_interactions.cpp`), label `unit` | every change, six presets |
| System | the shipped programs in their own processes, through their real interfaces: options, signals, TCP and TLS, UDP, files, exit status | `minidaq/tests/system/`, label `system` | every change, six presets |
| Soak | one long acquisition: memory, counters and latency over time | `tools/soak.py` | each release, 30 minutes on the reference machine |
| Hardware in the loop | the system with a real readout board instead of `minidaq_send` | a test bench (section 6) | each release of the product (assumption: confirm with team) |

A defect is tested at the lowest level that can show it. A system test that finds a defect
gets a unit test or a property as well, when one can show it, so that the next regression is
found in seconds instead of minutes (MDQ-PR-017 is the example).

## 3. Environment

- **Reference machine:** the book's 4-vCPU virtual machine, Ubuntu 24.04, GCC 13 and Clang 18.
  The system tests use loopback only and pick free ports (`--port 0`), so they run in parallel
  with each other and with other tests, and need no privileges.
- **Network stack:** `net.core.rmem_max` at least 4 MiB, as the acquisition PC is installed
  (ADR 0009). The readout tests check the receive buffer the server was granted and fail before
  they send if it is smaller; CI sets it on its runners (MDQ-PR-020).
- **Isolation:** each test case has its own temporary directory, its own runtime directory for
  the server's start-up token (`MINIDAQ_RUNTIME_DIR`) and its own server process.
- **Timing:** every wait has a deadline and polls for a condition (coding standard rule 5.5).
  Under the sanitizer presets the deadlines are multiplied by 10 (`MINIDAQ_TEST_TIME_FACTOR`).
- **Data:** the synthetic source with a fixed seed, and `minidaq_send` with a fixed seed. No
  patient data is used anywhere in testing.

## 4. Test cases

The test cases are the methods of the test classes below. Each names the requirements it
verifies in a `# REQ:` comment; the [trace matrix](../trace-matrix.md) lists them per
requirement, and the [test report](#8-records) lists them per execution.

| File, class | Verifies | Pass criterion |
|---|---|---|
| `test_control_system.py` ClientAndServer | an acquisition run by an operator with the client; the client's exit status; `wait`; a wrong token | as stated in each assertion; exit status `0`, `1` or `2` as SRS-CTL-040 defines |
| `test_control_system.py` Roles | the observer and operator roles from a token file | the observer reads the status and is refused `configure` with `forbidden` |
| `test_control_system.py` Tls | TLS with the right CA; two impostor servers, one signed by another CA, one certified for another address | the impostor servers receive no byte of application data; the client exits with `2` |
| `test_control_system.py` Shutdown, Startup | a signal during a run; refused options | the run is drained and recorded before the shutdown; exit status `0`; invalid options refused |
| `test_acquisition_system.py` Accounting | every coincidence counted is in the files; the run record | equal counts in status, run record and files; files verify |
| `test_acquisition_system.py` GoldenExact | seed 1 against the golden records, also with small batches and short batch delays | identical SHA-256 of the records |
| `test_acquisition_system.py` GoldenStatistical | seed 2 against the golden run; a negative control with a narrower energy window | p-value above `0.001` for each comparison; the negative control below it |
| `test_readout_system.py` Readout | a clean stream, a damaged stream, a sequence wrap | every packet accounted for exactly; a damaged run reported incomplete |
| `test_stats.py` | the statistics the comparisons use | tabulated values; p-values uniform under the null hypothesis |

Negative controls are part of the plan, not extras: a comparison that cannot fail proves
nothing. The impostor servers, the narrower energy window and `test_stats.py`'s power tests
show that the checks can fail.

## 5. Golden data and statistical comparison

- **Golden data** is `minidaq/tests/system/golden/seed1.json`: the counts, the SHA-256 of every
  record and two histograms of the run of seed 1. It is written only by
  `test_acquisition_system.py --update-golden`, after a change that is meant to change what the
  DAQ writes, and the diff is reviewed with that change (its change request says why the
  output changes). A golden file updated to make a test pass, without a reason, is a
  nonconformity.
- **Exact comparison** (records equal) is used where the output must be reproducible: the same
  seed and configuration must give the same records (SRS-SYS-004).
- **Statistical comparison** is used where the output is random: another seed must not differ
  from the golden run by more than chance (SRS-SYS-005). Rates are compared with an exact test
  of two Poisson counts (conditional binomial), histograms with a chi-square test of
  homogeneity, sparse bins merged until each expects at least 5 counts.
- **Significance level:** `0.001` per comparison. With four comparisons per run, a correct
  build fails about 0.4% of runs by chance, about once in 250 runs; the seeds are fixed, so a
  given commit either passes or fails every time, and a chance failure shows when a change of
  the output moves the run, which is when it must be reviewed anyway. The level is a choice
  between false alarms and missed differences; the negative control shows which differences it
  finds.

## 6. Hardware in the loop

A bench replaces `minidaq_send` by a readout board (or a board's development kit) on a
dedicated network interface of the acquisition PC, with a pulser or a source for known input
(assumption: confirm with team the bench NeuroLF uses). The system tests of `test_readout_system.py`
are written against what the sender reports; on the bench, the board's own counters (packets
sent, sequence numbers) take that place. What only a bench shows: the real link's loss and
timing under load, the board's firmware behavior at start and stop, and the interface's
receive buffers and interrupts. Bench tests are slower and the bench is shared, so they run per
release and per change of the readout, not per commit.

## 7. Entry and exit criteria

- **Entry:** the commit builds without warnings in every preset and its unit tests pass.
- **Exit:** every system test case passes in all six presets (GitHub Actions and
  `ci/run_all.sh`); the soak of SRS-SYS-003 passes; the test report of the release build shows
  no failure. A failing test case is either fixed before the release or recorded as a problem
  report with its evaluation and the decision to release with it.

## 8. Records

- For each release, `tools/test_report.py build/release measurements/release-X.Y.Z/system-test-report.md`
  writes the test report: commit, build, machine, each test case with its requirements, result
  and duration, deviations, and the signatures of tester and reviewer.
- The soak's samples and summary are kept in `measurements/release-X.Y.Z/soak/`.
- The release record (development plan, section 8) cites both.

## 9. Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 19). |
