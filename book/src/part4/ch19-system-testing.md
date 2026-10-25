# Integration, system and hardware-in-the-loop testing {#ch19}

::: box-why
A unit test shows that one piece of code meets its specification. A scanner fails in the places
between the pieces: two units that each do what their header says and together do something
neither specification allows, a client and a server that each pass their tests and disagree on
an exit status, a program that runs for ten minutes in CI and leaks for eight hours at a site.
IEC 62304 asks for integration testing and software system testing of class B and C software,
with test procedures, pass criteria and records, and a DAQ engineer writes many of those
system tests and collects their data. This chapter builds the levels above the unit tests:
system tests that run MiniDAQ's shipped programs as an operator runs them, a comparison with
golden data that is exact where the output must be reproducible and statistical where it is
random, a readout board played by a program that damages its stream on purpose, a soak test, and
the test plan and generated test report that turn all of it into evidence a reviewer can sign.
On the way, the first system test of the acquisition finds a defect that no unit test could see.
:::

**A day in the life.** You are adding the last system test before the 0.4 review: run the same
acquisition twice, with the same seed, through the real server, and check that the two runs wrote
the same records. You expect it to be a formality. The coincidence sorter has a reference model,
ten properties and a mutation score above 90%; the pipeline has its own tests; the writer has
been fuzzed. The test fails. The counts are equal, the spectra are equal, and the SHA-256 of the
records is not. You write the first differing record to the terminal: number 135,698 of 231,650,
a pair whose two singles have the same time stamp, with crystal A and crystal B swapped. By the
afternoon you know why. Each unit does exactly what its specification says, and the two
specifications together leave the order of two singles with equal times to chance. The fix is
five lines. The problem report, the new requirement, the property that would have found it and
the paragraph for the review take the rest of the day, and they are what the reviewer asks about.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Name the test levels of a DAQ from unit to hardware in the loop, say what each can find that
   the one below cannot, and choose the lowest level that shows a given defect.
2. Write system tests that run the shipped programs in their own processes, through their real
   interfaces, in parallel and without fixed sleeps, and that fail rather than skip when a
   program is missing.
3. Compare a run with golden data exactly where the output must be reproducible, and
   statistically where it is random: exact tests of two Poisson rates, chi-square tests of
   histograms, a stated significance level, negative controls and the power of a comparison.
4. Test a readout path with a simulated board that damages its stream on purpose, and account
   for every packet; record a stream and replay it as a test.
5. Design a soak test: what only time shows, how to sample it, and how to judge a trend against
   noise.
6. Write a system test plan and generate a test report from the run that it records, and explain
   what IEC 62304 expects of integration and system testing.

## Prerequisites and estimated time {.unnumbered}

Chapter 3 (the pipeline and its batches), Chapter 6 (the control API and the state machine),
Chapter 9 (the readout link and its sequence numbers), Chapter 10 (the coincidence sorter),
Chapter 17 (TLS and tokens) and Chapter 18 (unit tests, properties and coverage). The system
tests are in Python with the standard library only. Reading: about 3 hours. Exercises: 8 to 10
hours. Milestone: 5 hours. In the 10-week schedule at the front of the book, this chapter is in
week 7, with Chapters 20 to 23; if time is short, do Exercises 19.1 to 19.3 and leave the extras.

## Test levels

### The intuition

A defect can live in one function, between two functions, between two programs, or between the
software and the hardware it runs on. Each test level is a way to reach one of those places:

- A **unit test** runs one unit through its interface, with everything else replaced: the sorter
  with a vector of singles, the writer with a temporary directory. It is fast and exact, and it
  can only find what is inside the unit.
- An **integration test** runs several units together in one process: the pipeline with its
  stages and queues, the acquisition service with its ports, the control server with the service.
  It finds mistakes in how the units are put together: a stage that assumes the previous one
  sorted its output, a port called in an order its fake never saw.
- A **system test** runs the programs that ship, each in its own process, through the
  interfaces an operator and a board use: command-line options, signals, a TCP or TLS
  connection, UDP datagrams, files, exit status. It finds what lives between programs and in the
  code that no other level reaches: `main()`, option parsing, the start-up token, the shutdown on
  a signal.
- A **hardware-in-the-loop** (HIL) test replaces the simulated board by a real one, on a bench.
  It finds what the simulation leaves out: the real link's timing and loss under load, the
  board's firmware at start and stop, the network interface's buffers and interrupts.

The levels are not a ladder you climb once. They are a set of tools, and the rule for choosing
is: test a defect at the lowest level that can show it. A system test that fails tells you that
something is wrong somewhere in a million lines of behavior; a unit test that fails tells you
which line. When a system test finds a defect that a unit test or a property could show, add that
test too, so that the next regression is found in seconds instead of minutes. The levels above
the unit are there for the defects that the units cannot show.

### MiniDAQ's levels

MiniDAQ has had unit and integration tests since Chapter 1, in one GoogleTest binary
(`minidaq_unit_tests`); Chapter 18 measured them. This chapter adds the system tests in
`minidaq/tests/system/` and the soak, and writes the levels down in a system test plan
(`docs/regulatory/verification/stp.md`, section "Test protocols and reports" below):

| Level | What it verifies | Where | Runs |
|---|---|---|---|
| Unit | one unit through its interface | `tests/unit/` | every change |
| Integration | units in one process: pipeline, service, control | `tests/unit/` | every change |
| System | the shipped programs through their real interfaces | `tests/system/` | every change |
| Soak | one long acquisition: memory, counters, latency | `tools/soak.py` | each release |
| HIL | the system with a real readout board | a bench | each product release |

The test directories are under `minidaq/`; the unit and integration tests carry the CTest label
`unit` and the system tests `system`, and every change runs them in all six presets. The
hardware-in-the-loop row is what a product would do (assumption: confirm with team).

The system tests run in every preset, sanitizers included: a use-after-free in the server's
shutdown path is found by `asan-ubsan` running the real server, not by a unit test that never
calls `main()`.

### Testing the programs as shipped

A system test starts real processes, so it has the problems of real processes: ports that are
taken, files left behind, programs that take a while to start and may not stop. MiniDAQ's harness,
`minidaq/tests/system/systest.py`, solves each once, so that the tests can be about behavior:

- **Free ports.** The server takes `--port 0`, binds a port the kernel chooses, and prints it in
  its banner (`control API on 127.0.0.1:PORT (`). The harness reads the banner. The UDP readout
  does the same, and the status reports its port. No two tests compete for a port, so they run
  in parallel with each other and with the unit tests.
- **Isolation.** Every test case gets its own temporary directory and its own runtime directory
  (`MINIDAQ_RUNTIME_DIR`) for the server's start-up token, and starts its own server. No test
  depends on another's leftovers, or on the order in which they run.
- **Waiting.** Every wait polls for a condition with a deadline; none sleeps for a fixed time
  (coding standard rule 5.5, CAPA-0001 of Chapter 16). Under the sanitizer presets the programs
  run several times slower, so one factor, `MINIDAQ_TEST_TIME_FACTOR` (10 there, 1 elsewhere),
  stretches every deadline. A deadline is the time after which waiting longer is pointless, not
  the time the test expects to need.
- **Missing programs fail.** The tests find the programs through `MINIDAQ_APPS`, which CTest sets
  to the build's directory. An early version skipped a test when a program was missing; a test
  run without `MINIDAQ_APPS` then passed with every test skipped. Now a missing program is a
  failure with a message that says what to set.

```{.python include="minidaq/tests/system/systest.py" snippet="harness"}
```

The harness also has a `Server` context manager that starts `minidaq_server`, reads its port and
stops it with a signal, returning the exit status and the output; a `Ctl` wrapper that runs
`minidaq_ctl` and parses its JSON; a small PKI made with `openssl` for the TLS tests; and a
reader of MDQ-L1 list-mode files. It uses only the Python standard library, so the test tools
add no SOUP.

::: box-mistakes
- **A sleep instead of a condition.** `time.sleep(2)` followed by an assertion passes on your
  machine and fails on a loaded CI runner, or wastes two seconds on every run when one would do.
  Poll for the condition with a deadline.
- **A test that skips for a missing program.** A skip is reported as success by most runners.
  If the program under test cannot be found, that is a broken test setup: fail.
- **Fixed ports and shared directories.** A test that binds port 7700 cannot run next to another
  that does, or next to a developer's own server. Let the kernel choose and read the choice back.
- **Testing only the debug build.** The release build is what ships, and its optimizer exposes
  undefined behavior that a debug build hides. Run the system tests in every preset, and record
  the report of the release build (section "Test protocols and reports").
- **Asserting on log text.** A test that greps for "acquisition started" breaks when someone
  rewords a message. Assert on the interfaces: status fields, exit codes, files.
:::

## The control client against the server

### Exit status, roles and shutdown

Chapter 18's coverage report showed two class B items without a single automated test: the
control client `minidaq_ctl` (6 of its 237 lines reached by the unit tests) and the server
program's `main()` (not run at all). Their parts are tested where they live, in `TlsStream`, the
token store and the protocol, but nothing tested how the programs put the parts together. That is
problem report MDQ-PR-015, and its decision was to release with it until this chapter.

Before writing a test, the behavior needs a requirement. The SRS (version 8) adds four, and the
coverage review below a fifth:

- **SRS-CTL-040**: the client authenticates before the command, prints the response, and exits
  with `0` if the command was accepted, `1` if the server refused it or the token, and `2` on a
  usage, token-file or connection error. A script that drives the DAQ depends on those numbers.
- **SRS-CTL-041**: given a CA file, the client sends nothing, neither token nor command, to a
  server whose certificate that CA did not sign or that is not certified for the address.
- **SRS-CTL-042**: `wait` polls the status until a state or a deadline, and exits with `1` at the
  deadline.
- **SRS-CTL-043**: the server refuses contradicting options, and on `SIGINT` or `SIGTERM` stops
  and drains a running acquisition, records the shutdown in the audit trail, removes its start-up
  token and exits with `0`.
- **SRS-CTL-044**: given `--config FILE`, the server configures the acquisition from the file at
  start-up, or exits with a nonzero status and the file's errors.

The tests in `test_control_system.py` follow the requirements. An operator configures and starts
a run with the client and waits for its end; the client exits with `1` for a refused command and
`2` for a server that is not there; an observer token reads the status and is refused `configure`
with `forbidden`. The shutdown test sends `SIGTERM` during a run and then reads the audit trail:
the stop by the signal comes before the end of the run, the shutdown is the last entry, and the
run's record says the run is complete. A unit test cannot check that order, because it lives in
three components and a signal handler.

### A client that must refuse an impostor

SRS-CTL-041 is part of a risk control (hazard H-08 of Chapter 15: an operator token handed to an
impostor). Testing it means building the impostor. The test starts a TLS server written in Python's
`ssl` module, with a certificate that the client must not accept, points the client at it with a
real token, and records every byte the impostor receives:

```{.python include="minidaq/tests/system/test_control_system.py" snippet="impostor"}
```

Two impostors are used: one whose certificate another CA signed, and one signed by the right CA
but certified for `10.0.0.7` instead of the address the client connected to. In both cases the
client exits with `2`, names the certificate in its error, and the impostor receives nothing.
The last assertion is the one that matters: a client that sent its token and then complained
about the certificate would pass the exit-status check and fail this one.

This is a **negative control**: a test that shows the check can fail. A test that only connects
to the right server shows that TLS works; it cannot show that the client checks anything. Every
safety-relevant check needs a test with input that it must refuse.

With these tests, the coverage report of the unit and system tests together reaches 81.9% of the
client's lines and 77.0% of its branches (from 2.5% and none), and 80.4% of the server program's
lines and 81.1% of its branches (from not run at all). The branches still not taken are failures
of the operating system, TLS failures after the handshake, variants of option parsing and a few
rare server paths; `measurements/ch19/README.md` reviews them group by group, and MDQ-PR-015 is
closed with those numbers. One group was not accepted: the server's `--config` option, which
configures the acquisition at start-up, had no requirement and no test. It got both
(SRS-CTL-044), which is what a coverage review is for.

## Golden data and reproducibility

### Exact comparison

**Golden data** is the recorded output of a run that was reviewed and accepted, against which
later runs are compared. For MiniDAQ, `minidaq/tests/system/golden/seed1.json` keeps what a
one-second acquisition with the synthetic source and seed 1 wrote: the number of prompt and
delayed coincidences, a SHA-256 of every record in order, and two histograms, of the energies
and of the time differences of the prompts. The digest is small enough to keep in the
repository and exact enough to show a change in any record:

```{.python include="minidaq/tests/system/test_acquisition_system.py" snippet="summary"}
```

An **exact comparison** is right where the output must be reproducible: the same configuration
and the same seed must give the same records (SRS-SYS-004). That is not a nicety. A regression
test against golden data can only tell a real change from noise if there is no noise; and a
problem seen at a site can only be investigated on a developer's machine if the same input gives
the same output there.

### The defect that two correct units made

The first run of the exact test failed. Two acquisitions with seed 1 wrote the same number of
prompts and delayed coincidences, the same spectra, and different records: equal up to record
135,698 of 231,650, a prompt with a time difference of 0, whose crystals A and B were swapped.
The investigation, recorded as problem report MDQ-PR-017, went like this.

The sort stage of the pipeline (Chapter 3) orders each batch by time, then crystal. That is its
specification, and its tests check it. Batches are cut by size and by time
(`max_batch_delay_us`), so where a batch ends depends on scheduling and changes from run to run.
Two singles with the same time stamp that fall into one batch come out in crystal order; two that
fall into two batches come out in the order they arrived. The coincidence sorter (Chapter 10)
takes singles in time order, and its specification says nothing about the order of equal times;
it took the first to arrive as single A. Both units met their specifications. Together, the
output depended on where the batch boundaries fell.

No unit test could have found it, and none had: the sort stage was correct for every batch, and
the sorter was correct for the order it was given. The properties of Chapter 18 fed the sorter
directly, without the sort stage and its batches, and their reference model took singles of
equal times in the same order of arrival as the sorter; their streams did contain ties, and the
two agreed on every one. Only a test of the two units together, through the real pipeline with
real scheduling, could show it, and only an exact comparison could see it: the swapped pair
changes no count and no histogram.

The fix makes the sorter's output a function of the singles alone. A single that arrives with the
same time as the singles before it is moved into crystal order, among the singles still in an
open window:

```{.cpp include="minidaq/src/processing/coincidence_sorter.cpp" snippet="insert"}
```

The rest of the change is what makes it stay fixed:

- a requirement, **SRS-SRT-013**: singles with equal times are taken in crystal order, whatever
  the order of arrival;
- a property at the unit level, `TheOrderOfTiesDoesNotMatter`, which permutes the singles of equal
  times and requires the same coincidences, with a generator that makes equal times common (about
  one step in thirteen); it fails without the fix;
- the reference model of the properties, which now orders ties the same way;
- a second exact system test with small batches and short batch delays
  (`batch_size` 257, `max_batch_delay_us` 50), which moves the boundaries everywhere;
- the evaluation: not safety relevant, because both orders describe the same coincidence (same
  line of response, energies and time, and a time difference of 0 has no sign), but a real
  defect, because reproducibility is a requirement.

Exercise 19.4 is this defect in small: a batcher and a pairer that are correct alone, five
seeded mistakes in how they work together, and the test that finds four of them without
knowing any answer.

### Statistical comparison

Another seed gives other records, so the exact comparison does not apply. What must hold is
that the run with seed 2 does not differ from the golden run by more than chance (SRS-SYS-005).
That is a statistical test, and it needs three decisions: what to compare, with which test, and
at which significance level.

MiniDAQ compares four things: the prompt rate, the delayed rate, the energy spectrum and the
spectrum of time differences.

```{.python include="minidaq/tests/system/test_acquisition_system.py" snippet="statistical"}
```

**Two rates.** Two Poisson counts `n1` in time `t1` and `n2` in time `t2` have the same rate if,
given their sum, `n1` is binomial with probability `t1 / (t1 + t2)`. The exact two-sided binomial
test of that is the conditional test of two Poisson means (Further reading). MiniDAQ computes it
exactly up to 200,000 counts, where an approximation would be poor, and by the normal
approximation above; the exact test is conservative (it rejects at most as often as the
significance level says):

```{.python include="minidaq/tests/system/stats.py" snippet="rates"}
```

**Two histograms.** Two histograms of counts come from the same distribution, whatever their
totals, if the counts of each bin are in proportion to the totals. The chi-square test of
homogeneity measures the departure from proportion; its statistic follows a chi-square
distribution with one degree of freedom less than the number of bins, as long as no bin expects
too few counts. Sparse bins, in the tails of a spectrum, are merged with their neighbors until
each expects at least five (Cochran's rule of thumb, Further reading):

```{.python include="minidaq/tests/system/stats.py" snippet="homogeneity"}
```

**The significance level.** A comparison fails when its p-value is below `0.001`. With four
comparisons per run, a correct build fails about 0.4% of the runs by chance, about one in 250.
The seeds are fixed, so a given commit either passes or fails every time; a chance failure
appears when a change of the output moves the run to another sample, which is when the output
has to be reviewed anyway. A level of `0.05` would make one correct change in five fail the
system test; `1e-6` would let real differences through. The level is a choice between false
alarms and missed differences, and it is written in the test plan, with the reason.

The statistics are in `minidaq/tests/system/stats.py`, in plain Python: the regularized
incomplete gamma function for the chi-square distribution, the exact binomial, and the merging.
A test tool that decides whether a release passes must itself be verified (Chapter 20 treats the
confidence a tool needs). `test_stats.py` checks the functions against tabulated quantiles of
the chi-square distribution and an exact binomial computed by hand, and checks that their
p-values are uniform when the null hypothesis holds: of many comparisons of two samples from one
distribution, about 5% must fall below 0.05, about 1% below 0.01.

### Can the comparison fail?

A statistical comparison that passes says that the difference was not larger than chance makes
likely. It does not say that there was no difference. Two checks keep it honest.

The first is a **negative control**: a run that is really different must fail. The test runs
seed 2 with an energy window 5 keV narrower on each side (440 to 580 keV instead of 435 to
585 keV), and requires the energy comparison to fail. If it passed, the comparison would be too
blind to trust.

The second is the **power** of each comparison: the smallest difference it finds with a stated
probability. The power falls with the counts. The golden run counts a few hundred thousand
prompts but only a few thousand delayed coincidences, so the prompt comparison sees a change of
about 1% and the delayed comparison only one of more than 10% (Exercise 19.2 computes both and
checks them by simulation). A pass of the delayed comparison is weak evidence, and the test plan
should say so, or the run should be longer.

### Changing golden data

Golden data is written only by `test_acquisition_system.py --update-golden`, after a change that
is meant to change what the DAQ writes, and the diff of the golden file is reviewed with that
change. The fix of MDQ-PR-017 was such a change: the order of equal-time pairs changed, so the
digest changed, while the counts and histograms stayed the same. The change request says why the
output changes, and the reviewer checks that only what should change did. A golden file updated
to make a test pass, without a reason, is a nonconformity: it turns the test into a record of
whatever the code does today.

::: box-mistakes
- **Golden data that is regenerated by CI.** A golden file written by the same run that is
  compared with it can never fail. Golden data is written by a person, on purpose, and reviewed.
- **An exact comparison of random output.** Comparing histograms bin by bin for equality, or a
  rate within "5%", fails at random or passes everything. Use a test whose error rate you know.
- **No negative control.** A comparison that has never been shown to fail may be unable to.
- **Reading a pass as "no difference".** A pass with few counts means little. Know the power.
- **Many comparisons at one level.** Twenty comparisons at `0.05` fail a correct build in two
  runs of three. Count the comparisons when you choose the level.
- **Bins that expect almost nothing.** The chi-square approximation breaks in sparse tails, and the
  test fails on noise. Merge sparse bins, or use fewer.
:::

## Replayed and simulated data

### A board that damages its stream on purpose

The UDP readout of Chapter 9 receives packets from a readout board. On the bench there is a
board; in CI there is `minidaq_send`, which simulates singles, cuts them into MDQ-R1 packets
with sequence numbers, and damages the stream on purpose: it drops a fraction of the packets,
delays some (sends them after packets with higher sequence numbers), and sends some twice. Then
it reports exactly what it did:

```
singles 223355 in 0.5 s of detector time (1e+06 Bq)
packets 1228 of up to 182 words, sequence 0 .. 1227
injected: lost 13, delayed 15, duplicated 13, both delayed and duplicated 0
sent 1228 datagrams, 1.81 MB in 0.500 s: 2456 packets/s, 28.9 Mbit/s, 0 send errors
```

The server's link counters must account for every packet. The sequence tracker gives a gap a
limited time and a limited number of packets to be filled (Chapter 9). A delayed packet that
arrives in time is put back in order and counted as reordered; one that arrives after its gap was
given up was counted as lost, and is dropped as stale when it comes, like a duplicate. So the
identities are:

```{.python include="minidaq/tests/system/test_readout_system.py" snippet="damaged"}
```

The test asserts that the stream actually contained all three kinds of damage (a run in which the
random draw injected no duplicate would check nothing about duplicates), and that the run is
marked incomplete with the loss counter named. Two more tests send a clean stream, which must
arrive complete, and a stream whose sequence numbers start 100 below 2^32, which must cross the
wrap without a loss or a resync. Exercise 19.1 writes the full set of accounting identities and
checks them against recorded runs.

The end of the `injected` line is there because the first version of this test was right by luck.
It passed with 1% of each kind of damage, and the same identities failed by two packets when
Exercise 19.1's recordings were made with 5%. A packet can be delayed and duplicated at once; the
sender then sends the copy on time and the original late, so the late one is a duplicate, never a
packet that came too late, and the identities counted it twice. At 1% the chance that one packet
draws both is one in ten thousand, and the run of seed 5 had none; at 5% it is one in four
hundred, and the run of seed 8 had two. The sender did not report the overlap, so no test could
account for it. Problem report MDQ-PR-018 records the defect in the test tool: `minidaq_send` now
reports the packets that were both, the identity subtracts them, and a second test runs with 5%
of each and requires at least one such packet. The lesson is the one of the negative control,
applied to the test data: a test is only as good as the cases its input contains, so make the
test assert that its input contains them.

The new test then found a defect in the shipped code. It passed on a quiet machine and failed in
one run of the coverage report, which runs all tests in parallel; with the four CPUs loaded on
purpose it failed eight times in eight, always with `packets_reordered` one or two too high. The
sequence tracker counted a packet as reordered as soon as it arrived after a higher sequence
number, before it checked whether the packet was a copy of one it already held; a late original
whose on-time copy was waiting behind an earlier gap was counted reordered and stale. Under load
the server reads larger batches, packets wait longer, and the case becomes common. The counter is
a diagnostic, not part of the integrity verdict, and nothing was lost or misordered, but a wrong
diagnostic sends a link investigation the wrong way. Problem report MDQ-PR-019 records it; the
tracker now counts a packet as reordered only when it is used, and a unit test,
`ALateCopyOfAHeldPacketIsNotReordered`, fails without the change. Two lessons: a system test
that is flaky under load is reporting something, so find it before you call it flaky; and run
system tests under load on purpose, because the timing of a quiet machine hides cases.

### Replaying recorded data

A simulation produces what its model knows. A recording produces what happened. MiniDAQ uses
both: `ReplaySource` (Chapter 11) replays a recorded stream of MDQ-P1 words at a fixed rate, so
that the throughput measurements see the energies and coincidence structure of a simulated
phantom rather than uniform words. At the packet level, a capture of what a board sent turns a
field problem into a test: the same datagrams, in the same order and with the same gaps, can be
sent to the DAQ again, as often as needed. Exercise 19.5 builds that tool, records a damaged
stream, and shows that two replays give identical runs.

A replay is only a test if the system's decisions depend on what it receives, not on when. Most
of MiniDAQ's do: the sequence numbers, time stamps and energies decide everything the sorter
does. One does not: the tracker gives up a gap after `max_hold_us` (1 ms by default), a time. A
delayed packet that arrives 0.9 ms after its gap opened is used in one replay and too late in the
next. A replay test sets the hold time long, so that the reorder window decides; a real link
keeps the short default, because a DAQ cannot hold data for a packet that may never come. Know
which of your system's decisions are made by the clock before you trust a replay to repeat.

## Soak tests

### What only time shows

Some defects need hours to show: memory that grows by a few kilobytes per run or per minute, a
32-bit counter that wraps after 4.3 billion events (about 72 minutes at a million singles per
second), a queue that grows one element per second, a latency that drifts as a structure
fragments, a file handle that is never closed. A test of one second sees none of them. A **soak
test** (also called an endurance test) runs the system at its working load for a long time and
watches what it does.

The design questions are what to sample, how often, and how to judge. MiniDAQ's soak,
`tools/soak.py`, runs one acquisition of the synthetic source at 1,000,000 singles/s through
`minidaq_server` and samples every 10 seconds the server's resident memory (`VmRSS` from
`/proc`), the sorter's input counter, the losses and faults of the status, and the p99 and
maximum of the end-to-end latency over the last interval. It writes every sample to
`samples.csv`, so the judgment can be checked and repeated.

### Judging a trend

Resident memory is noisy: the allocator returns and takes pages, the kernel reclaims, a buffer
is touched for the first time. A soak that fails when the last sample is larger than the first
fails at random. MiniDAQ's soak leaves out a warm-up (10 minutes), fits a least-squares line
through the samples after it, and fails only if the slope exceeds the limit (1 MiB per hour) by
more than two standard errors:

```{.python include="tools/soak.py" snippet="slope"}
```

The two standard errors make the test tolerant of noise and sensitive to a steady trend: the
longer the run, the smaller the standard error, and the smaller the leak it can find. Exercise
19.3 extends the judgment to latency drift, counters that go down, stalls, losses and faults, and
asks what a single late allocation does to a straight line.

### MiniDAQ's soak

SRS-SYS-003 asks for 8 hours at 1,000,000 singles/s without a loss, a fault or memory growth
above 1 MiB per hour after the first 10 minutes. The release checks run 30 minutes on the book's
4-vCPU machine; the 8-hour run belongs to the system test on the acquisition PC, which the SRS
states as an assumption to confirm with the team. The 30-minute run of this chapter
(`measurements/ch19/soak/`):

| Quantity | Result |
|---|---|
| Singles in | 1,800,032,317 in 30.0 minutes (1,000,018/s) |
| Losses, faults | none; the run complete |
| Resident memory | 29.7 MiB at the start, 30.3 MiB at the end, 30.4 MiB at most |
| Trend after 10 minutes | -0.006 MiB/h, standard error 0.033 MiB/h (121 samples); limit 1 MiB/h |
| p99 latency per interval | median 1.33 ms; 5 of 181 intervals above 5 ms, at most 16.2 ms |
| Verdict | pass |

The latency outliers have a likely cause outside the server: the machine was compiling and
testing this chapter's exercises during the run. The measurement's README records that as a
deviation. It does not change the verdict, because the soak does not judge latency, but it is
the kind of fact that a report must state rather than leave for a reviewer to find.

A soak test is one sample of a long run. It does not show that the server never leaks; it shows
that it did not leak measurably in this run, at this rate, with this configuration. What it
exercises is decided by the configuration: a soak that writes no files cannot find a file
handle leak in the writer. MiniDAQ's soak writes nothing (`output` is `none`) so that the disk
does not decide the rate; the writer's own long run is the throughput measurement of Chapter 12.
State the configuration with the result.

## Hardware in the loop

Everything so far runs on one machine with a simulated board. A **hardware-in-the-loop** bench
replaces `minidaq_send` by a readout board, or a board's development kit, on a dedicated network
interface of the acquisition PC, with a pulser or a radioactive source for known input
(assumption: confirm with team which bench the NeuroLF uses). The system tests of
`test_readout_system.py` are written against what the sender reports; on a bench, the board's
own counters (packets sent, sequence numbers) take its place, and the same identities must hold.

What only a bench shows:

- the real link's loss and timing under load, with the real network interface, its interrupt
  coalescing and its receive rings (Part V tunes them);
- the firmware's behavior at start and stop, after a reset, and when the DAQ is slower than the
  board;
- timing: a pulser at a known rate gives a known count, and two channels fed by one pulser give
  a known time difference, which checks the whole chain of time stamps;
- electrical and environmental conditions that software cannot simulate.

A bench is slow to set up and shared, so HIL tests run per release and per change of the readout
path, not per commit. Two practices make them affordable. Keep the system tests the same at both
levels, with the board or the simulator behind one interface, so that a bench run is the CI run
with another sender. And record what the bench sends: a capture from the bench (Exercise 19.5)
becomes a replay test that runs on every commit.

## Test protocols and reports

### The system test plan

IEC 62304 asks for software integration testing and software system testing (clauses 5.6 and
5.7) with tests that cover the requirements, documented procedures and pass criteria, and records
of the results; for class B and C the results are evaluated and the anomalies go into problem
resolution. MiniDAQ's development plan (version 6) adds the system tests to every change's
`ctest` and adds two checks to each release: the system test report and the soak.

What is tested above the unit level is written in a document of its own, the **system test plan**
(`docs/regulatory/verification/stp.md`, a controlled document listed in the design file under
clause 7.3.6). It says, in nine short sections:

1. what is under test (`minidaq_server` and `minidaq_ctl` from one commit and preset) and what is
   a test tool (`minidaq_send`, the harness, the statistics, the soak and report tools), and how
   the tools are verified;
2. the test levels, with the rule that a defect is tested at the lowest level that can show it;
3. the environment: the reference machine, loopback, free ports, isolation, deadlines;
4. the test cases, by file and class, with what each verifies and its pass criterion;
5. the golden data, how it may change, and the statistical method with its significance level;
6. what a hardware-in-the-loop bench adds;
7. entry and exit criteria: what must hold before system testing starts and before a release;
8. the records: the test report and the soak, per release;
9. its own change history.

The test cases themselves are code. The test plan does not repeat them; it points to them and states
the pass criteria in words a reviewer can check against the code. Each test method names its
requirements in a `# REQ:` comment, and `tools/trace_matrix.py` collects them, so the trace
matrix lists the system tests next to the unit tests of each requirement.

### A test report made by the run

A test report typed from memory, or assembled by hand from CI logs, is not evidence: nobody can
tell which run it describes. MiniDAQ's report is written by the run it reports.
`tools/test_report.py BUILD OUT.md` runs every system test module with a recording test result
and writes:

- the identification: version, commit (and whether the working tree had uncommitted changes,
  which makes the report invalid as evidence), build type, compiler, sanitizers, machine, date
  and tester;
- one row per test case with its requirements (read from its `# REQ:` comment), its result and
  its duration;
- the deviations, with the failure message of each failed case;
- the conclusion and a table for the signatures of tester and reviewer.

It exits with `1` if a case failed, so a release cannot cite a failing report. The report of the
release build of this chapter is `measurements/ch19/system-test-report.md`:

«STR_SUMMARY»

The signatures are left empty for a person. In a quality system the review of a test report is a
record of its own: someone other than the author reads the deviations, checks that the report is
of the right commit, and signs. The tool makes the report; it does not make the review.

::: box-regulated
What the regulated setting adds to this chapter's examples:

- Integration and system testing are activities of the development plan, with their own plan
  (procedures and pass criteria), and their results are records kept with the release.
- Every requirement of the SRS is verified by a test, a measurement or an inspection; a system
  requirement (`SRS-SYS-*`) is verified at the system level, and the trace matrix shows where.
- A test that failed and was fixed, or that fails and is accepted, goes into problem resolution
  with its evaluation; the release states the open ones (MiniDAQ's known anomalies).
- Golden data and its updates are controlled: who may change it, and the review of the diff.
- Test tools that decide whether a release passes (the harness, the statistics, the soak, the
  report generator) are verified for that use (Chapter 20).
- System testing of the scanner goes on beyond the software: the software system test is one
  input to the verification of the device and to its validation in the use environment
  (ISO 13485 clause 7.3.7), which MiniDAQ alone cannot do.
- Regression: after a change, the development plan says which tests are repeated. With automated
  system tests in every change, the answer can be "all of them", which is the simplest argument to
  make.
:::

::: box-askteam
1. Which test levels does the NeuroLF's development plan define, and where is the boundary
   between integration and system testing drawn?
2. Is there a hardware-in-the-loop bench for the DAQ, what is on it (board, pulser, source), and
   how is time on it scheduled?
3. How are golden data and reference acquisitions kept, and who may change them?
4. Which statistical methods and significance levels does the team use for comparing
   acquisitions, and are they written down?
5. How long do the soak tests run, on which machine, and with which configuration? Does the
   system requirement state a duration?
6. What does a test report look like, who signs it, and where is it kept?
7. Are field captures (recorded detector data) available for replay, and under what data
   protection rules?
:::

## Exercises {.unnumbered}

**Exercise 19.1 (E): Account for every packet.** *Goal:* write the accounting identities of a
damaged readout stream: what `minidaq_send` reports it did, against what the server's link
counters say happened. *Starter:* `exercises/ch19/e1_link_accounting/` (checks one identity of
eight; `tests/recorded.json` holds four real runs). *Acceptance:* every recorded run passes, and
each corrupted counter is named by the identity it breaks. Then answer in `NOTES.md` why a
delayed packet can appear in two counters, and which identity would break if the server dropped
a datagram it had received. *Time:* 45 minutes.

**Exercise 19.2 (M): What the golden comparison can see.** *Goal:* compute the smallest change of
a rate that MiniDAQ's comparison with golden data finds with 90% power, check it by simulation,
and report it for the golden run. *Starter:* `exercises/ch19/e2_golden_power/` (a formula that
ignores the power, a simulation to write). *Acceptance:* `tests/test_power.py` passes: a
hand-computed case, calibration at no difference, agreement of formula and simulation within 3
percentage points, and the report of `golden/seed1.json`. Then answer in `NOTES.md` what the
report says about the delayed comparison and how you would make it see a 5% change. *Time:* 90
minutes.

**Exercise 19.3 (M): Reading a soak test.** *Goal:* turn the samples of a soak run into a verdict:
memory growth and latency drift after the warm-up, judged against noise; counters that go down;
stalls; losses; faults; and runs too short to judge. *Starter:* `exercises/ch19/e3_soak_analysis/`
(reads `samples.csv`, checks only losses). *Acceptance:* `tests/test_soak_analysis.py` passes:
steady and noisy runs pass, and each kind of problem is found and named. Then answer in
`NOTES.md` what a single late allocation does to your verdict, and what would tell a step from a
leak. *Time:* 90 minutes.

**Exercise 19.4 (M, extra): The test that finds an integration defect.** *Goal:* write tests of a
batcher and a pairer put together that each of five seeded mistakes fails; four are in how the
units work across batch boundaries. *Starter:* `exercises/ch19/e4_batching_test/` (one
hand-worked example; the subject's comment is its specification). *Acceptance:* `original`
passes and `mutant_1` to `mutant_5` each fail. Then answer in `NOTES.md` which mutants a
metamorphic relation caught, which needed an expected answer, and what your stream generator
needed for each. *Time:* 2 hours.

**Exercise 19.5 (H, extra): Record a readout link and replay it.** *Goal:* write a tool that
records the datagrams a board sends and replays them with the recorded timing, and show with it
that two replays of a damaged stream into `minidaq_server` give identical runs. *Starter:*
`exercises/ch19/e5_udp_replay/` (the command line and the capture format; recording, reading and
replaying are to do). *Acceptance:* `tests/test_udp_replay.py` passes: the format, refusal of
damaged captures, timing at speeds 0, 1 and 2, a complete recording of `minidaq_send`, and two
replays with equal link counters, sorter counters and records. Then answer in `NOTES.md` what a
replay reproduces and when two replays would differ. *Time:* 3 hours.

## MiniDAQ milestone: system tests, golden data, a soak and a signed report {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ's shipped programs are tested as an operator runs them: the client against the
server with TLS impostors, acquisitions against golden data exactly and statistically, the
readout link with a damaged stream, and a 30-minute soak; a system test plan and a test report
generated by the run make the evidence; the integration defect the tests found is fixed and
recorded. **Start:** tag `ch18`. **End:** tag `ch19`.
:::

1. Add the harness `minidaq/tests/system/systest.py` and the statistics `stats.py` with their
   tests; register the system tests in CTest with the label `system` and the time factor for the
   sanitizer presets.
2. Add the control, acquisition and readout system tests, tagged with SRS version 8's new
   requirements (SRS-CTL-040 to 044, SRS-SYS-001 to 005).
3. Record the golden run of seed 1. When the exact comparison fails, find the cause, fix it with
   a requirement (SRS-SRT-013), a property and a problem report (MDQ-PR-017), and record the
   golden run again with a reviewed diff.
4. Add `tools/soak.py`, run it for 30 minutes at 1,000,000 singles/s, and record the result in
   `measurements/ch19/soak/`.
5. Write the system test plan, add `tools/test_report.py`, and record the report of the release
   build in `measurements/ch19/`.
6. Rerun the coverage report with the system tests, record it, and close MDQ-PR-015 with the
   coverage of `ctl` and `server`.
7. Write the change request for the corrections (CR-0005), with its impact analysis.
8. Update the development plan to version 6 (system tests in every change; the report and the
   soak in each release), `tools/release_checks.sh`, and the design file.
9. Add Exercises 19.1 to 19.5.

**Definition of done.** `ci/run_all.sh` is green on all six presets, with the system tests, and
static analysis reports nothing; the system test report of the release build has no failure and
names the clean commit; the soak passes; MDQ-PR-015, MDQ-PR-017, MDQ-PR-018 and MDQ-PR-019 are
closed with their evidence; every starter of the chapter fails. Tag `ch19`.

## Check yourself {.unnumbered}

1. Name the test levels of a DAQ and one defect that each finds and the level below cannot.
2. A system test fails. What do you do once you have found the cause, besides fixing it?
3. Why does MiniDAQ's harness fail, rather than skip, when a program is missing?
4. How does a system test wait for a server to start without a fixed sleep, and how does it
   find the server's port?
5. What is a negative control? Give the two that MiniDAQ's system tests use.
6. When is an exact comparison with golden data right, and when a statistical one?
7. Explain MDQ-PR-017: why did each unit meet its specification, why did no unit test find it,
   and what was added besides the fix?
8. How do you test that two Poisson counts have the same rate? Why is the exact test
   conservative?
9. Four comparisons at a significance level of `0.001`: how often does a correct build fail?
   What would twenty comparisons at `0.05` do?
10. A comparison with a few thousand counts passes. What can you conclude, and what not?
11. What does a soak test find that a one-second test cannot? How do you tell a leak from noise?
12. A replay of a recorded stream gives a different run each time. Where do you look first?
13. What does a hardware-in-the-loop bench add to the system tests, and why does it run less
    often?
14. What makes a test report evidence? Who signs it, and what does the signature mean?

## Summary {.unnumbered}

- Test levels reach different places: units, units together, programs together, the system with
  its hardware. Test each defect at the lowest level that can show it, and add a lower-level test
  when a higher one finds a defect.
- System tests run the shipped programs through their real interfaces: free ports, isolation,
  deadlines instead of sleeps, a time factor for the sanitizers, and failure when a program is
  missing.
- The control client is tested against the real server and against TLS impostors that must
  receive nothing; that closed MDQ-PR-015, the coverage gap of Chapter 18.
- Golden data is compared exactly where output must be reproducible; the exact test found
  MDQ-PR-017, a defect between two correct units that no unit test could see.
- Random output is compared statistically: exact tests of Poisson rates, chi-square tests of
  histograms with sparse bins merged, a stated significance level, a negative control, and a
  known power.
- A simulated board damages its stream on purpose, and every packet is accounted for; a recorded
  stream replayed into the DAQ is a test only if the DAQ's decisions depend on order, not on time.
- A soak test watches memory, counters and latency over a long run, and judges trends against
  noise with a fitted slope and its standard error.
- A system test plan states levels, cases, pass criteria and records; the test report is
  generated by the run it reports, and a person signs its review.

## Further reading {.unnumbered}

- IEC 62304:2006+A1:2015, *Medical device software: Software life cycle processes*, clauses 5.6
  (software integration and integration testing) and 5.7 (software system testing).
- FDA, *General Principles of Software Validation; Final Guidance for Industry and FDA Staff*,
  2002. Section 5.2.5 on testing by the developer, from unit to system level.
- Glenford J. Myers, Corey Sandler and Tom Badgett, *The Art of Software Testing*, 3rd edition,
  Wiley, 2011. Test levels, and system testing as a search for the ways a program fails its
  objectives.
- Steve Freeman and Nat Pryce, *Growing Object-Oriented Software, Guided by Tests*,
  Addison-Wesley, 2009. End-to-end tests that start the real system, and how to keep them fast
  and reliable.
- Martin Fowler, "TestPyramid", martinfowler.com, 2012. Why most tests belong at the lower
  levels.
- Tsong Yueh Chen and others, "Metamorphic Testing: A Review of Challenges and Opportunities",
  *ACM Computing Surveys* 51(1), 2018. Testing without an oracle, as Exercise 19.4 does with
  batch sizes.
- K. Krishnamoorthy and Jessica Thomson, "A more powerful test for comparing two Poisson means",
  *Journal of Statistical Planning and Inference* 119(1), 2004. The conditional test used here,
  its conservativeness, and an alternative.
- William G. Cochran, "Some Methods for Strengthening the Common χ² Tests", *Biometrics* 10(4),
  1954. Where the rule of at least five expected counts per cell comes from, and when it can be
  relaxed.
- Michael T. Nygard, *Release It! Design and Deploy Production-Ready Software*, 2nd edition,
  Pragmatic Bookshelf, 2018. The failures that appear only after long running, and the patterns
  that contain them.
- Python documentation, `unittest`, `subprocess` and `ssl` modules, docs.python.org. The
  standard library the system tests are built on.
