# Unit and component testing in C++ {#ch18}

::: box-why
IEC 62304 asks for unit verification of class B and C software, against acceptance criteria that
the development plan sets, and MiniDAQ has had unit tests since its first commit. This chapter
asks the question that comes after "do we have tests?": how good are they? A reviewer, an auditor
or your own team lead will ask it in three forms. Which code do the tests run? That is coverage.
Would the tests notice a mistake? That is mutation testing. Do the tests check the cases nobody
thought of? That is property-based testing. You will learn to write tests that are worth keeping
(one behavior, a clear name, no sleeps, no hidden randomness), to design code so it can be tested
without hardware, to use fakes, decorators and mocks for the ports of Chapter 6, and to measure
and read statement, branch and MC/DC coverage. MiniDAQ gets a property-based testing harness with
ten properties, interaction tests with GoogleMock, a coverage report per software item, and a
mutation testing tool that finds the tests' blind spots in the coincidence sorter.
:::

**A day in the life.** The design review for MiniDAQ 0.4 is on Thursday, and the reviewer from the
quality team has sent her questions in advance. The third one reads: "The SRS says the sorter's
window is inclusive. Show me the test that would fail if someone changed `<=` to `<`." You search
the tests. `TheWindowIsInclusive` exists, and it checks a pair exactly one window apart: good.
Then you try the experiment for real: you change the operator, rebuild and run the sorter's twelve
tests, and they fail. You change a different comparison in the same file, the one that rejects a
delay above 1 ms, from `>` to `>=`, and all twelve pass. By Wednesday evening you have a tool that
makes such changes automatically, a list of the 28 it made that no example test noticed, and new
tests for the ones that mattered; one of them showed that the requirement itself never stated the
1 ms limit. On Thursday you show the reviewer the list, the tests, and the ten mutants that are
left with the reason each one cannot be detected. She asks for the same list for the sequence
tracker before the release.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Write unit tests that check one behavior each, through the public interface, with names that
   say what failed, and that give the same result on every run.
2. Design code for testability with seams and dependency injection, and choose between a fake, a
   stub, a decorator that injects faults and a mock for a hardware port.
3. Write property-based tests: choose properties (invariants, round trips, a reference model,
   metamorphic relations), write generators that reach the boundaries, and read a shrunk
   counterexample.
4. Measure statement, branch and MC/DC coverage with Clang, read the uncovered branches of a
   file, and explain what coverage does and does not prove.
5. Use mutation testing to find the mistakes a test suite would let through, and tell an
   equivalent mutant from a gap in the tests.
6. Document unit verification so that it counts as evidence: acceptance criteria, requirement
   tags, coverage and the review of what is not covered.

## Prerequisites and estimated time {.unnumbered}

Chapter 1 (GoogleTest and the presets), Chapter 6 (ports and adapters), Chapter 10 (the coincidence
sorter), Chapter 14 (unit verification in IEC 62304 and the trace matrix). Reading: about 3 hours.
Exercises: 7 to 9 hours. Milestone: 4 hours. In the 10-week schedule at the front of the book, this
chapter is in week 6, with Chapters 7, 16 and 17; if time is short, do Exercises 18.1 to 18.3 and
leave the extras.

## What a unit test is for

### The intuition

A unit test is a small program that runs a piece of your code on an input you chose and checks the
result against what the specification says. Its value is the failure it would report: a test that
cannot fail is worth nothing, and a test that fails for reasons nobody can read is worth little
more. So the questions to ask of a test are not "does it pass?" but "what mistake would make it
fail?" and "when it fails, will the message say what broke?"

In a regulated project a unit test has a second job: it is evidence. IEC 62304 clause 5.5 asks the
manufacturer of class B and C software to establish a unit verification process, to define
acceptance criteria for the software units, and to verify each unit against them (verify: the
clause numbering against your copy; 5.5.4 adds criteria for class C). The standard does not say
what the criteria are. MiniDAQ's development plan (`docs/regulatory/sdp.md`, section 6) does: a
unit is accepted when its tests pass under every preset, static analysis reports nothing, its
interface is documented in its header and every requirement it implements is traced. That makes
the tests' quality a question of process, not of taste: a weak test suite is a weak acceptance
criterion.

### Anatomy of a good test

MiniDAQ's 273 unit tests follow a few rules, and most problems with tests come from breaking one
of them.

- **One behavior per test.** `TheWindowIsInclusive` checks one sentence of the specification. A
  test that checks ten things fails for any of ten reasons, and the first failed assertion hides
  the others.
- **A name that states the behavior.** `CoincidenceSorter.ChunkingDoesNotChangeTheResult` is read
  in a CI log by someone who has never seen the code. `Test3` or `SorterWorks` tells them nothing.
- **Arrange, act, assert.** Build the input, call the code once, check the result. When the
  arrange part grows long, it is a helper (MiniDAQ's tests have `at()`, `plain()`, `run()`), not a
  copy in every test.
- **Through the public interface.** A test of a private detail breaks when the detail changes,
  although the behavior did not; then people learn to update tests without reading them.
- **Repeatable.** The same commit gives the same result on every machine and every run: no
  unseeded randomness, no dependence on the order of tests, no wall-clock waits. CAPA-0001 in
  Chapter 16 was about the last one: every wait in a test now waits for a condition, with a long
  deadline (`eventually()`), and the test `tests.waits` checks that every `sleep_for` in a test
  says why.
- **Fast.** All of MiniDAQ's unit tests run in about a minute in the `debug` build in one
  process, and in a fraction of that with `ctest -j4`; most of the time goes to the few tests that
  run the service or a long simulation. So they run on every build. A test that needs minutes
  belongs to a slower label.

The assertion matters as much as the call. `EXPECT_EQ(round_trip(t), t)` compares whole
sequences, so a failure prints every value that came back wrong; a loop with `EXPECT_TRUE(ok)`
prints "false". GoogleTest's matchers (`ElementsAre`, `Field`, `HasSubstr`, from GoogleMock) and
the streaming of a message into an assertion (`<< "every word read is counted"`) are there to
make the failure explain itself.

### Table-driven tests

Many behaviors are one rule applied to many inputs: every malformed header field must be rejected
with its own error. Writing one test per input is tedious and writing a loop inside one test hides
which input failed. GoogleTest's value-parameterized tests give each row of a table its own test
and its own name:

```{.cpp include="minidaq/tests/unit/test_readout_packet.cpp" snippet="table"}
```

A failure is reported as `ReadoutPacketHeaders/MalformedHeader.IsRejected/flags_0x80`, which says
exactly which row broke. The table also makes gaps visible: the older test
`RejectsEveryMalformedField` checked one undefined flag bit, and the table checks all seven. The
control protocol's `EveryFieldOfEveryTypeIsAnswered` from Chapter 17 is a table of another shape,
1,760 requests generated from five fields, eleven values and four kinds of client.

::: box-mistakes
**Tests that do not test.**

- **A test without an assertion that can fail.** It covers code and checks nothing. Run your new
  test once against a deliberately broken implementation (or let mutation testing do it, later in
  this chapter) before you trust it.
- **Testing the implementation.** A test that checks which private function was called, or the
  exact contents of an internal buffer, fails on every refactoring and teaches people to "fix the
  test".
- **Sleeping instead of waiting.** `sleep_for(100ms)` before an assertion is too short on a busy
  runner and too long everywhere else. Wait for the condition (`eventually()`).
- **Unseeded randomness.** A test that draws a new random input on each run passes today and fails
  next month for a reason nobody can reproduce. Seed it, print the seed, or use a property harness
  that does both.
- **One test, ten behaviors.** When it fails, you debug the test before you debug the code.
- **A test that violates the code's precondition.** The unwrapper assumes less than half a wrap
  between words; a test that steps by two thirds of a wrap fails on correct code (Exercise 18.1's
  notes show the case).
:::

## Designing for testability

### Seams and dependency injection

Michael Feathers calls a *seam* a place where you can change what a program does without editing
it there. MiniDAQ's seams are the ports of Chapter 6: the acquisition service knows a
`DetectorPort` and a `CoincidenceSinkPort` and receives factories for them in its
`ServiceOptions`. The application passes the real adapters (`with_default_adapters()`); a test
passes its own. That is dependency injection, and it is what lets the service's tests run without
a detector, a network or a disk.

The same idea works below the service. The list-mode sink does not call `write(2)` and `fsync(2)`
directly but through a `FileOps` interface, so `test_listmode_sink.cpp` can make the disk full on
the third block or fail the rename at the end of a run, faults that are hard to make on a real
file system. The sequence tracker takes the time as a parameter (`offer(p, now_ns, ...)`) instead
of reading a clock, so a test can let a gap age by exactly a millisecond. A clock, a random
generator, a file system and a device are the four dependencies that make code hard to test; pass
each one in.

How do you unit test code that talks to an FPGA? The same way. The code that knows the registers
and the commands sits behind an interface (Chapter 22 builds it for the readout board), the logic
above it is tested against a fake device that behaves like the documented one, and a smaller set
of tests runs against the real board on a bench (Chapter 19). The fake and the real device must
agree, so the same contract tests run against both whenever the bench is available: a fake that
drifts from the hardware is a source of false confidence.

### Test doubles: fakes, stubs, mocks and decorators

Gerard Meszaros named the kinds of stand-in a test can use, and the names help in a review:

- A **stub** returns canned answers: a detector whose `fault()` always says "link down".
- A **fake** is a working, simplified implementation: `ScriptedDetector` in the service tests
  generates synthetic words and can be told to fail; `FakeOps` keeps files in memory.
- A **mock** records the calls it receives and checks them against expectations set before the
  test runs.
- A **spy** records the calls for the test to inspect afterwards.

MiniDAQ adds one more kind in Exercise 18.4: a **decorator** that wraps a real port and injects
only the failure (a fault after N words, a dropped word every n-th word, a stall). The words still
come from the simulated detector and flow through the real pipeline, so the test checks the
behavior around a realistic stream, and the failure is exactly where the test wants it.

Most of MiniDAQ's tests use fakes, because most of what matters is state: counters, the state of
the run, the integrity verdict. A mock earns its place when the interaction is the behavior. The
service must call the sink's `close()` exactly once, after the last `write()`, at the end of a
clean run, because `close()` is what makes the data durable and stores the run record. No counter
shows the order of two calls, so a mock checks it:

```{.cpp include="minidaq/tests/unit/test_service_interactions.cpp" snippet="mock"}
```

```{.cpp include="minidaq/tests/unit/test_service_interactions.cpp" snippet="sequence"}
```

`InSequence` makes the two expectations ordered: once `close()` has been called, the `write()`
expectation is retired, and a later `write()` fails the test as an unexpected call (a three-line
experiment confirms it before you rely on it). `NiceMock` lets the calls the test does not care
about, such as `describe()`, pass silently. Writing these tests showed that the order was
something the service did and no requirement stated, so the SRS gained SRS-CTL-035, and its
third test checks the other half: after a fault the sink is never closed, and its files keep the
`.part` names that say they are not known to be complete (Chapter 12).

::: box-mistakes
**Doubles that lie.**

- **Mocking everything.** A test with five mocks and twenty expectations checks that the code
  makes the calls it makes. Use a mock for an interaction that is itself required, and a fake
  for the rest.
- **Over-specified expectations.** `Times(3)` for a call whose count does not matter breaks the
  test when the batching changes. Say `AnyNumber()` unless the number is the point.
- **A fake that drifts from the real thing.** A fake detector that never reorders packets makes
  every reordering bug invisible. Run the same contract tests against the fake and the real
  adapter, and add each real-device surprise to the fake.
- **Mocking types you do not own.** A mock of a library's interface encodes your guess of how the
  library behaves. Wrap the library in an adapter of your own and test the adapter against the
  real library.
:::

## Property-based tests

### The intuition

An example-based test checks one input whose answer you worked out. A property-based test states
something that must be true for every input of a kind, generates many inputs, and checks it on
each. The idea comes from QuickCheck, by Koen Claessen and John Hughes (2000), and its value is in
the inputs nobody chose: the stream where two singles have the same time, the batch boundary that
falls inside a window, the sequence number one below the wrap of the counter.

Generated inputs are large and ugly, so a property harness does a second thing: when a property
fails, it *shrinks* the input to a small one that still fails. A failure that reads "80 singles,
window 4,317 ps, cuts at 12, 40 and 77" is a debugging session; one that reads "window 3,317 ps,
singles at 0, 1 and 3,318 ps" is a diagnosis.

### MiniDAQ's harness

MiniDAQ uses a harness of its own, about 250 lines in `minidaq/tests/support/property.hpp`,
rather than the RapidCheck library: ADR 0015 records why (no new SOUP in the evidence chain, and
a harness small enough to review). Generators draw numbers from a `Source`, which records every
choice:

```{.cpp include="minidaq/tests/support/property.hpp" snippet="source"}
```

The choice recorded is the offset from the lower bound, so a smaller choice always means a value
closer to it. Shrinking then needs no knowledge of the generator: the harness deletes blocks of
recorded choices and lowers each one by bisection, replays the generator on the edited sequence,
and keeps every edit after which the property still fails. A shorter sequence makes shorter
lists; smaller choices make smaller numbers and earlier options. This is the approach of the
Python library Hypothesis; RapidCheck shrinks values instead, with a shrinker per type.

```{.cpp include="minidaq/tests/support/property.hpp" snippet="check"}
```

Three rules make the property tests evidence rather than a lottery. The seed is fixed per test (a
hash of its name), so every run of a commit checks the same inputs. `MINIDAQ_PROP_SEED` and
`MINIDAQ_PROP_CASES` widen the search on purpose: the release checks run every property with 100
times the cases. And a failure prints the seed, the shrunk input and its choices, and
`MINIDAQ_PROP_REPLAY` replays them, so a failure in CI is reproduced on a desk.

### Choosing properties

The hard part is not the harness but the property. Four kinds cover most of MiniDAQ's code:

1. **Invariants**: something every output satisfies, whatever the input. Every prompt's time
   difference is in `[0, window]`; the sorter's counters account for every single; the tracker
   delivers in increasing sequence order.
2. **Round trips**: an encoder and a decoder undo each other. `PackAndUnpackAreInverse` checks
   that for every crystal, energy code and time code; `TheUnwrapperRestoresEveryTime` checks that
   unwrapping the codes of a stream gives back its times.
3. **A reference model**: a second, simpler implementation of the same specification, which may
   be slow because it sees the whole input at once. `TheSorterFindsWhatTheReferenceFinds` compares
   the streaming sorter with a forty-line reference written from the comments of
   `coincidence_sorter.hpp`.
4. **Metamorphic relations**: two runs whose results must relate in a known way, even if neither
   result is known. Cutting the input into batches must not change the coincidences
   (`BatchSizesDoNotMatter`), which is SRS-SRT-008 stated as a property.

The reference model deserves care. It must not share code with what it checks, or one bug is in
both; MiniDAQ's reference shares only the geometry test `good()`, which has its own tests. And it
must be simpler, not a copy: the streaming sorter manages a buffer, a horizon, a compaction and a
delayed window that moves forward with the openers, while the reference filters the whole stream
and cuts it into windows with two loops.

```{.cpp include="minidaq/tests/unit/test_properties.cpp" snippet="sorter_model"}
```

### Generators reach only what they produce

A property finds a defect only if the generator produces an input that shows it. A time drawn
uniformly from a microsecond almost never lands exactly one window after another single, and a
uniform float energy is essentially never exactly 585.0 keV, so a sorter whose window or energy
gate excludes its edge passes every property with such a generator. MiniDAQ's sorter generator
therefore draws each time step from four kinds (half a window, two windows, across the delayed
window, backwards) and most energies from inside the gate. Exercise 18.2 shows the difference.
With uniform time steps and uniform energies, four of its eight seeded mistakes survive every
property: the two that need an exact edge, and the two that need three singles inside one
window, which uniform steps produce too rarely. With a generator that produces the boundaries of
the specification and crowded windows, none does (`measurements/ch18/uniform-generator.md`).

The tracker's generator makes a different point. A property must be true for every input the
generator produces, so the generator encodes the precondition. The tracker restores order only
for packets displaced by less than its reorder window, and a run of stale packets longer than the
window is, by design, a restart of the source; so the generator displaces packets by less than the
window and keeps duplicates fewer than the window. Outside those limits the tracker's behavior is
specified differently, and needs its own properties.

### What the properties found

All ten properties pass, at 200 cases each on every run and at 20,000 cases each in a longer
search, so they found no defect in MiniDAQ's code. That is a typical result for code that already
has careful example-based tests: the properties are a net under them, and their main value comes
with the next change, when the reference model and the metamorphic relations check the new code on
inputs its author did not think of. They also make claims cheap to check. A natural question about
the tracker is whether a lossy link can make it drop a packet that did arrive: a gap is declared
lost when the window fills, so could a late packet find its number already given up? Five lines
added to the tracker property ("every packet that arrives is delivered once, unless it is a
duplicate") answer it for every link the generator makes: it holds at 200,000 cases, because a
packet displaced by less than the window always arrives before any packet a full window ahead of
it, and the property's hold time is longer than the run. The check is now part of the property,
and the claim is now a tested one.

The harness tests itself, too: `TheHarnessShrinksACounterexample` checks that a false property
("no list sums to more than 1000") fails and shrinks to a list whose sum is exactly 1001. That is a
*local* minimum: no single deletion or lowering still fails. Shrinking does not promise the
smallest counterexample, only one where every remaining part matters.

::: box-mistakes
**Properties that prove little.**

- **A property that the empty answer satisfies.** "Every prompt is inside the window" holds for a
  sorter that finds nothing. Pair invariants with a reference or a count.
- **The reference is the code.** A reference that calls the function under test, or copies it,
  agrees with every bug.
- **A generator that misses the boundaries.** Draw exact edges on purpose: equal times, exactly
  one window apart, energies on the gate, sequence numbers next to the wrap.
- **A new seed on every run.** A property that fails one day in thirty is a flaky test. Fix the
  seed and widen the search deliberately.
- **Properties instead of examples.** Keep the hand-made example for each rule of the
  specification: it documents the rule, and its failure message is the clearest.
:::

## Coverage

### Statement, branch and MC/DC

Coverage measures which parts of the code the tests executed. The measures differ in what counts
as a part, and the differences matter for the sorter's energy gate:

```cpp
if (!(e >= cfg_.energy_low_kev && e <= cfg_.energy_high_kev)) {
```

- **Statement (line) coverage**: the line ran. One single in the gate is enough.
- **Branch (decision) coverage**: the decision was taken both ways, true and false. A single in the
  gate and one outside it are enough, but not one below and one above: the test can be complete
  for branch coverage without ever checking the upper bound.
- **Condition coverage**: each condition (`e >= low`, `e <= high`) was both true and false.
- **MC/DC (modified condition/decision coverage)**: each condition was shown to affect the decision
  on its own, with the other conditions held fixed. For `a && b` that takes three tests: (true,
  true), (false, true) and (true, false). It is required for the most critical software in
  aviation (DO-178C, level A) and recommended for the highest safety level in automotive (ISO
  26262-6, ASIL D) (verify: the tables of the editions you work with).

Clang measures all of these from the source: `-fprofile-instr-generate -fcoverage-mapping`
instruments the code, and Clang 18 adds `-fcoverage-mcdc` for MC/DC (verify: Clang 18 limits a
decision to six conditions for MC/DC; later versions raise it). MiniDAQ's `coverage` preset uses
them, and `tools/coverage.py` runs the unit tests, merges the profiles of every process they start
(the Python tests start the applications), and reports each software item of
`docs/architecture/software-items.json`:

```text
item       class lines              branches           MC/DC conditions   functions
-----------------------------------------------------------------------------------
core       B      94.7%   252/266    71.2%    57/80    100.0%     5/5      98.7%    74/75   
format     B      96.8%   584/603    87.3%   234/268    60.5%    23/38     94.4%    68/72   
pipeline   B      98.3%   580/590    91.3%   157/172   100.0%    22/22     97.2%    70/72   
metrics    B      98.9%   179/181    90.7%    49/54     50.0%     2/4     100.0%    18/18   
rt         B      86.7%   176/203    74.6%    94/126    46.7%    14/30     93.8%    15/16   
processing B      88.7%   283/319    78.1%   114/146    26.3%     5/19    100.0%    32/32   
sorter     B     100.0%   220/220    91.9%   147/160    94.9%    37/39    100.0%    20/20   
merger     B     100.0%   124/124    92.9%    52/56     68.8%    11/16    100.0%    13/13   
sim        B      94.8%   605/638    87.0%   247/284    67.9%    36/53     92.6%    63/68   
config     B      99.4%   313/315    74.5%   152/204    91.7%    11/12    100.0%    22/22   
service    B      95.7%   471/492    86.2%   200/232    56.1%    23/41    100.0%    49/49   
protocol   B      94.2%   437/464    83.6%   204/244    58.2%    32/55     96.3%    26/27   
access     B      81.1%   330/407    67.8%   145/214    17.9%     7/39     97.2%    35/36   
readout    B      93.3%   196/210    71.7%    43/60      0.0%     0/5      92.3%    24/26   
output     B      83.5%   380/455    67.5%   139/206    40.6%    13/32    100.0%    37/37   
audit      B      87.9%    29/33     50.0%     7/14     25.0%     1/4     100.0%     8/8    
server     B     not run by any test
ctl        B       2.5%     6/237     0.0%     0/126     0.0%     0/14      9.1%     1/11   
tools      -      52.6%   421/801    39.5%   177/448    10.7%     8/75     71.0%    22/31   
-----------------------------------------------------------------------------------
all               85.2%  5586/6558   71.7%  2218/3094   49.7%   250/503    94.3%   597/633  
```

Test code, exercises, fuzz targets and benchmarks are excluded: the question is how much of the
code that ships the tests run.

### Reading the uncovered branches

A number hides more than it shows. `tools/coverage.py build/coverage OUT --uncovered FILE` lists
each line of a file with a branch the tests took only one way. For the coincidence sorter at tag
`ch18` (later chapters change the file, so its line numbers move):

```text
$ tools/coverage.py build/coverage OUT --uncovered minidaq/src/processing/coincidence_sorter.cpp
  153: if (first_ > 4096 && first_ * 2 > buf_.size()) {
       column 24: branch never false
       column 24: condition never shown to decide alone (MC/DC)
  174: while (e < buf_.size() && buf_[e].time - t <= cfg_.delay + cfg_.window) {
       column 31: branch never false
       column 31: condition never shown to decide alone (MC/DC)
```

Two of the file's 138 branches were taken only one way, and each needs a different answer.

Line 153 decides when the buffer of singles is compacted. Its second condition (more than half
of the buffer is spent) was true every time the first was: in the tests, as in a scanner, a
window closes long before 4,096 singles pile up behind it. A test could reach the false branch
with thousands of singles at one time, but nothing it could check through the public interface
would change, because compaction moves data and never changes a result. That is the same
argument as for the six surviving mutants of this line, and the review records it once for both.

Line 174 is more interesting: its second condition can never be false. A window closes only when
a single later than its horizon (`delay + window`) arrives, and that single has not joined the
buffer yet, so every single in the buffer is inside the delayed window and the loop always ends at
the end of the buffer. The condition is dead by design. You have two honest options: remove it
and state the invariant in a comment and an assertion, or keep it as a guard that makes the loop
correct by itself, with the reason in the review. MiniDAQ keeps it, because the horizon is
computed in the constructor, a hundred lines away, and a change there would make the condition
necessary again without anyone noticing. Either choice is fine; leaving it unexplained is not.

The report also found something to delete. `CoincidenceSorter::config()` was the sorter's only
function that no test called, and no code called it either. It was removed, and the sorter's
line coverage went from 99.5% to 100% and its function coverage from 95.2% to 100%. Code that
nobody calls is code that nobody tests, and the cheapest way to cover it is to remove it. The
header's 11 untaken branches
are in the defaulted `operator==` of `SorterStats`: every comparison in the tests was of equal
statistics, so no field was ever found to differ. That is a fact about the tests (a failing
comparison would still print both sides), and the review accepts it.

Read the other rows the same way. Two items stand out, and they are the two programs an operator
runs. `server`, the `main()` of `minidaq_server` that reads the options, builds the security
settings and handles the shutdown signal, has no row of numbers at all: no test starts the program,
so no profile holds any of its code. An early version of `tools/coverage.py` left such an item out
of the table, which hid the largest gap of all; now it says so. `ctl`, the operator's client, has 6
of 237 lines, because no unit test starts it either. Its parts (the TLS context, the stream, the
secret file reader, the protocol) are tested where they live, but how the client puts them together,
including that it checks the server's certificate before it sends the token, is not. It is a class B
item that controls a hazard, so the gap is recorded, with the server's, as problem report
MDQ-PR-015, and Chapter 19's system tests close it by running the client against the server.

Coverage of the concurrent items also moves a little from run to run: between two runs that differed
only in the sorter's header, `pipeline` went from 98.0% to 98.3% of its lines, most likely because
which branches of its threads run depends on the scheduler. Compare such items by their uncovered
lines, not by the last digit.

### What coverage proves, and what it does not

Coverage is a measure of what the tests did not do. An uncovered branch is a fact: no test reached
it, so no test checked it. A covered branch is not the opposite fact. A test without an assertion
covers as much as a test with one, and a branch covered by a test that checks the wrong thing is
covered. That is why 100% line coverage is not proof of correctness: it says every line ran, not
that any result was checked, nor that the inputs that matter (the edge of a window, a wrap of a
counter, two threads at once) were among those that ran it.

What auditors expect follows from that. IEC 62304 asks for no coverage number. The FDA's *General
Principles of Software Validation* (2002) lists structural coverage measures (statement, decision,
condition, multi-condition, loop, path and data flow coverage) as part of the developer's testing
and expects the rigor to follow the risk (verify: section 5.2.5 of the guidance). What a reviewer
of a class B item usually wants to see is a coverage report from the released commit, a stated
target, and a review of what is not covered: each uncovered branch either reached by a new test or
accepted with a reason. MiniDAQ's development plan (version 5) states its rule as a ratchet: no
class B item may lose coverage from one release to the next, and every uncovered branch in a
class B file that changed since the previous release is reviewed before the release (assumption:
confirm with team the coverage targets of your scanner's own development plan).

### Mutation testing

Mutation testing asks the question coverage cannot: would the tests notice if this code were
wrong? A tool makes one small change to the code (a *mutant*: `<` for `<=`, `&&` for `||`, `+` for
`-`, a condition negated), rebuilds, and runs the tests. If a test fails, the mutant is *killed*.
If all pass, it *survived*: either it is *equivalent* to the original (no input can tell them
apart), or it is a mistake the tests would let through. The idea is from Richard DeMillo, Richard
Lipton and Frederick Sayward (1978); Google runs it on code review at scale and reports surviving
mutants to the author as review comments.

`tools/mutation_test.py` is a small mutation tool for one file: it finds binary operators by the
spaces around them (as clang-format writes them, which keeps template brackets and `<<` out),
skips comments and string literals, and applies four kinds of change:

```{.python include="tools/mutation_test.py" snippet="operators"}
```

On the coincidence sorter it made 171 mutants, of which 7 do not compile and are not counted. With
only the sorter's twelve example-based tests (`CoincidenceSorter.*`), 135 were killed, 1 made a test
run past the time limit (which counts as killed: the tests noticed), and 28 survived, a *mutation
score* of 82.9%. With the property tests added, 139 were killed, 4 timed out and 21 survived
(87.2%). Each mutant is a rebuild and a test run of a few seconds in the `release` build, so the
two runs took 13 and 21 minutes on the book's machine (`measurements/ch18/`).

The survivors fall into two groups, and telling them apart is the work. Eleven were gaps, each a
mistake the tests would have let through:

- **Limits that nobody tested exactly.** Five mutants turn a limit of the configuration from
  inclusive to exclusive: a window of exactly 1 µs, a delay of exactly 1 ms, a lower energy of 0,
  an energy window of one value, a sector difference of exactly 12. Each needs one test on the
  limit. One of them showed more than a missing test: SRS-SRT-007 listed every limit but the
  delay's, so the code enforced a rule that no requirement stated. The SRS now states it.
- **A geometry checked from one side.** `sa > sb ? sa - sb : sb - sa` with the first `-` turned into
  `+` survives because every test of the sector cut had the lower sector first; the field-of-view
  cross product with `-` turned into `+` survives because every test LOR had one crystal on an axis,
  where the two products are equal. A test that swaps the singles and one that rotates the LOR
  around the ring kill both.
- **The delayed window's multiples.** SRS-SRT-006 says the delayed window uses the same multiples
  policy as the prompt window, but only two of the four policies were tested there; the properties
  caught some mistakes in the others and missed four. `DelayedMultiplesFollowThePolicy` kills them.

```{.cpp include="minidaq/tests/unit/test_coincidence_sorter.cpp" snippet="limits"}
```

Ten survivors are equivalent, or as good as equivalent, and stay with a reason recorded next to the
report:

- `sa > sb` written as `sa >= sb`: when the sectors are equal both branches give 0.
- Six mutants of the condition that compacts the buffer
  (`first_ > 4096 && first_ * 2 > buf_.size()`) and two of the index adjustment in `compact()`:
  they change when the buffer is compacted, or make the sorter rescan a few singles, and never
  which coincidences it finds. They are visible only in time and memory, which the benchmarks and
  the budget check, not the unit tests.
- `cross * cross > fov_r2_ * len2` written with `>=`: only a line exactly on the field-of-view
  boundary, in double arithmetic, tells them apart, and no configuration can aim at that reliably.

With the three new tests the sorter's mutants were run once more: 150 killed, 4 timeouts, and the
ten equivalent survivors above (93.9%). That last run is
the evidence a reviewer wants: not the score, but the list of what survives and why.

Mutation testing is slow, one build and one test run per mutant, so it is a tool for a file under
review rather than a gate on every commit; a commercial or LLVM-based tool (Mull, for example)
mutates the compiled code instead and needs no rebuild of the source per mutant.

::: box-mistakes
**Coverage targets that backfire.**

- **A target on the whole code base.** "85% line coverage" is met by testing the easy code twice
  and the hard code never. Set targets per item, by class, and review the uncovered branches.
- **Tests written for the number.** A test that calls a function to cover it and checks nothing
  raises coverage and lowers the value of the suite. Mutation testing finds such tests.
- **Excluding code to meet the target.** An exclusion marker in the source is a decision; it
  needs a reason that a reviewer accepts, like any other.
- **Coverage from a different build.** The report must come from the commit that is released,
  built the way it is tested. A report from last month's branch is not evidence.
:::

## Test documentation

### Tests that are evidence

A test result becomes verification evidence when three questions have answers: which requirement
does it verify, what is its acceptance criterion, and which commit did it run on. MiniDAQ answers
the first with the `// REQ:` tag inside each test, which `tools/trace_matrix.py` collects into the
traceability matrix (Chapter 14); a property test carries the tags of the requirements it states.
The second is in the test itself, as assertions, and in the development plan, as the unit
acceptance criteria. The third is the release record: the CI run and the evidence files of
`tools/release_checks.sh`, from one commit.

For a class B item the development plan (version 5) now adds two documents to that evidence: the
coverage report of the release commit (`tools/coverage.py`), and the review of the uncovered
branches of each class B item, which states for each one whether a test was added or why it is
accepted. The property tests run with 100 times their cases in the release checks. Mutation
testing is not required for every change; it is the reviewer's tool for code that implements a
risk control, where "would the tests notice a mistake here" is the review question.

### What a test case record needs

Some teams keep a written test specification for each unit test in addition to the code, with an
ID, the requirement, the steps and the expected result. For automated unit tests the code is a
more exact specification than any prose: the name states the behavior, the arrange part is the
input, the assertions are the expected result. What the code does not show is the requirement and
the reason for the test's existence, so those are the two things to keep next to it (the `REQ`
tag and, where it is not obvious, a comment). Ask what your team's procedure requires before you
write either.

::: box-regulated
What the regulated setting adds to this chapter's examples:

- The unit verification process, the acceptance criteria and any coverage targets are in the
  software development plan, and a change to them is a change to a controlled document.
- The test results of the released commit, the coverage report and the review of the uncovered
  code are kept in the design history file with the release; a test that was skipped or disabled
  is listed with the reason.
- Test tools that produce evidence (the test framework, the coverage tool, a property harness, a
  mutation tool) are listed with their versions, and the confidence they need is assessed
  (Chapter 20).
- A test changed in the same commit as the code it tests is reviewed with particular care: a
  weakened assertion can hide a defect as well as a missing test.
- For class C units, IEC 62304 asks for additional acceptance criteria (boundary conditions, fault
  handling, initialization, timing and memory use, among others), and coverage of those cases is
  what a reviewer looks for.
:::

::: box-askteam
1. What does your scanner's development plan state as unit acceptance criteria, and is there a
   coverage target per class?
2. Which coverage tool produces the evidence, and from which build and preset?
3. How are uncovered branches reviewed, and where is that review recorded?
4. Are property-based or mutation tests used anywhere in the team today, and is either tool
   assessed as a test tool?
5. Which hardware interfaces have fakes, and how are the fakes kept in step with the boards?
:::

## Exercises {.unnumbered}

**Exercise 18.1 (E): Fifteen tests for the timestamp rollover.** *Goal:* write at least fifteen
unit tests of the time unwrapper from its specification, so that each of seven plausible mistakes
in it fails at least one test. *Starter:* `exercises/ch18/e1_unwrap_tests/` (two tests and a list
of the behaviors they leave out; the subject is a copy of `TimeUnwrapper` with seven seeded
mutants selected by `EX_MUTANT`). *Acceptance:* `original` passes, `mutant_1` to `mutant_7` each
fail (CTest expects them to), and `at_least_15_tests` passes. Then answer in `NOTES.md` which
mutants survived your first attempt and what kind of test was missing for each. *Time:* 60
minutes.

**Exercise 18.2 (M): Properties of a coincidence sorter.** *Goal:* write property-based tests of a
fixed-window sorter with MiniDAQ's harness, among them that every prompt is inside the window and
that each single is used at most once, strong enough that each of eight seeded mistakes breaks a
property. *Starter:* `exercises/ch18/e2_sorter_properties/` (a uniform generator and one
property; the subject's comment is its specification). *Acceptance:* `original` passes and
`mutant_1` to `mutant_8` each fail. Then answer in `NOTES.md` which mutants invariants caught,
which needed a reference, and which needed a better generator. *Time:* 2 hours.

**Exercise 18.3 (M): Branch coverage of the sinogram.** *Goal:* write unit tests of the sinogram
histogrammer from its header that take at least 90% of the branches of `sinogram.cpp` both ways,
and account for every branch still open. *Starter:* `exercises/ch18/e3_branch_coverage/` (two
tests, 41% of the branches, and an empty `review.json`). *Acceptance:* in the `coverage` build with
starters on, `ch18/e3_branch_coverage/<variant>/coverage` passes: `tests/check_coverage.py` runs
your tests alone, measures the file with `llvm-cov`, and requires 90% of its branches and a
`review.json` that accepts exactly the branches still open, each with its line, column, the code
as it is now and a reason. Then answer in `NOTES.md` what kind of test the starter was missing for
most branches, and why the branch you accepted is not a gap. *Time:* 90 minutes.

**Exercise 18.4 (M, extra): A detector that fails on purpose.** *Goal:* write a `DetectorPort`
decorator that injects a fault after N words, drops every n-th word and stalls, and use it to show
that the service ends the run in a fault and that a dropped word makes the run incomplete.
*Starter:* `exercises/ch18/e4_fault_injection/` (passes everything through, injects nothing).
*Acceptance:* `tests/test_fault_injection.cpp` passes: the fault lands at exactly N words
whatever the read sizes, the inner port is not read after it and its own faults are never
hidden; drops are counted across reads in a counter that the integrity verdict sees; stalls
consume nothing; and with the real service the run ends in `fault` or, with drops, is not
complete. Then answer in `NOTES.md` when a decorator beats a fake and when a mock beats both.
*Time:* 90 minutes.

**Exercise 18.5 (H, extra): Kill the survivors.** *Goal:* run `tools/mutation_test.py` on the
sequence tracker (the template code of `readout_packet.hpp`) with MiniDAQ's tracker tests and
yours, write a test for every survivor a test can kill, and argue for each one left that it is
equivalent. *Starter:* `exercises/ch18/e5_kill_survivors/` (a harness, one test, an empty
`survivors.json`, and the command for the run in its README). *Acceptance:* your tests pass, and
`ch18/e5_kill_survivors/<variant>/survivors` passes: `tests/check_survivors.py` reads your recorded
report, checks that it is of the header as it is now (the report records the file's SHA-256), and
that `survivors.json` lists exactly the mutants that survived, each with a reason. Then answer in
`NOTES.md` which survivors were gaps and which were equivalent, and how you convinced yourself of
each equivalence. *Time:* 3 hours.

## MiniDAQ milestone: a unit test suite with properties, coverage and requirement tags {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ's unit tests include property-based tests of the decoder, the unwrapper, the
sorter, the tracker and the merger; interaction tests of the service and its sink; a coverage
report per software item from the `coverage` preset with a reviewed list of the sorter's
uncovered branches; a mutation testing tool and its result for the sorter; and a development plan
that makes coverage and its review part of unit verification. **Start:** tag `ch17`. **End:** tag
`ch18`.
:::

1. Add `minidaq/tests/support/property.hpp` with its self-test, ADR 0015, and
   `test_properties.cpp` with properties tagged to the requirements they state.
2. Add `test_service_interactions.cpp` with GoogleMock, SRS-CTL-035, and the table-driven header
   test.
3. Switch the `coverage` preset to Clang source-based coverage with MC/DC; add `tools/coverage.py`
   and record the report in `measurements/ch18/`.
4. Add `tools/mutation_test.py`; run it on the sorter with and without the properties, add tests
   for the survivors that are not equivalent, and record the reasons for the equivalent ones and
   the tracker's baseline in `measurements/ch18/`.
5. Update the development plan to version 5 (the coverage ratchet and review for class B, the wider
   property search in the release checks) and `tools/release_checks.sh`.
6. Add Exercises 18.1 to 18.5, with the CMake support for exercises checked against seeded mutants.

**Definition of done.** `ci/run_all.sh` is green on all six presets and static analysis reports
nothing; the property tests pass with `MINIDAQ_PROP_CASES=100`; `tools/coverage.py` reports every
shipped item; every surviving mutant of the sorter has a test or a reason; every starter of the
chapter fails. Tag `ch18`.

## Check yourself {.unnumbered}

1. Why is 100% line coverage not proof of correctness? Give an example from the sorter's energy
   gate.
2. How do you unit test code that talks to an FPGA?
3. What does MC/DC require for `a && b`, and why is branch coverage weaker?
4. What is the difference between a fake, a stub and a mock? Which would you use to check that
   `close()` comes after the last `write()`, and why?
5. Name four kinds of property and give a MiniDAQ example of each.
6. Why must a reference model not share code with the implementation it checks?
7. Why does MiniDAQ's harness fix the seed per test? How do you search more widely, and when?
8. What does a shrunk counterexample promise, and what does it not?
9. A mutant survives. How do you decide whether it is equivalent or a gap in the tests?
10. What does IEC 62304 require for unit verification of a class B unit, and what does it leave to
    the development plan?
11. A colleague's change raises the sorter's line coverage from 92% to 97% with one new test.
    What do you check in the review?

## Summary {.unnumbered}

- Unit tests are evidence of unit verification (IEC 62304 clause 5.5); the development plan sets
  their acceptance criteria, so the suite's quality is a matter of process.
- A good test checks one behavior through the public interface, names it, gives the same result on
  every run, and fails with a message that says what broke; table-driven tests give each row its
  own name.
- Seams and dependency injection let every hardware dependency be replaced in a test; fakes suit
  state, mocks suit required interactions, and a decorator can inject faults into a real stream.
- Property-based tests check invariants, round trips, reference models and metamorphic relations
  on generated inputs and shrink failures to small counterexamples; generators must produce the
  boundaries, and the seed is fixed so the tests stay repeatable.
- Coverage (statement, branch, MC/DC) shows what the tests did not run; it does not show that
  anything was checked. Review the uncovered branches by item and class.
- Mutation testing shows which mistakes the tests would let through; a surviving mutant is either
  equivalent or a missing test.
- MiniDAQ now has ten properties and a self-test of their harness, interaction tests, a coverage
  report per item, a mutation tool and a development plan that makes coverage review part of unit
  verification.

## Further reading {.unnumbered}

- GoogleTest and GoogleMock documentation, *GoogleTest User's Guide* and *gMock for Dummies*,
  google.github.io/googletest. The reference for parameterized tests, matchers and sequences.
- Michael Feathers, *Working Effectively with Legacy Code*, Prentice Hall, 2004. Seams, and how to
  get untested code under test.
- Gerard Meszaros, *xUnit Test Patterns: Refactoring Test Code*, Addison-Wesley, 2007. The names of
  test doubles and of test smells.
- Martin Fowler, "Mocks Aren't Stubs", martinfowler.com, 2007. State versus interaction testing.
- Koen Claessen and John Hughes, "QuickCheck: A Lightweight Tool for Random Testing of Haskell
  Programs", ICFP 2000. Where property-based testing started.
- David R. MacIver, Zac Hatfield-Dodds and others, "Hypothesis: A new approach to property-based
  testing", *Journal of Open Source Software* 4(43), 2019. Shrinking on the choice sequence.
- RapidCheck, github.com/emil-e/rapidcheck. The established C++ property-based testing library.
- Richard A. DeMillo, Richard J. Lipton and Frederick G. Sayward, "Hints on Test Data Selection:
  Help for the Practicing Programmer", *IEEE Computer* 11(4), 1978. The origin of mutation
  testing.
- Goran Petrović and Marko Ivanković, "State of Mutation Testing at Google", ICSE-SEIP 2018.
  Mutation testing in code review at scale.
- John Joseph Chilenski and Steven P. Miller, "Applicability of modified condition/decision
  coverage to software testing", *Software Engineering Journal* 9(5), 1994. MC/DC defined.
- Clang documentation, "Source-based Code Coverage", clang.llvm.org/docs. Flags, `llvm-cov` and
  MC/DC.
- FDA, *General Principles of Software Validation; Final Guidance for Industry and FDA Staff*,
  2002. Structural coverage in the developer's testing.
