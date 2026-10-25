# 0015. Property-based tests with a small in-house harness

Date: 2026-10-25
Status: Accepted

## Context

Chapter 18 adds property-based tests: statements such as "the sorter finds exactly what a
reference sorter finds" or "every packet number is delivered or declared lost", checked on
thousands of generated inputs. Example-based tests check the cases someone thought of; the
fuzzers of Chapter 7 search for crashes but check no result. A property test checks results on
inputs nobody chose, and when one fails it must shrink the input to a small counterexample, or
the failure is a stream of 80 singles that nobody can debug.

The tests are verification evidence (IEC 62304 clause 5.5), so the tool that runs them is part
of the evidence chain: it must give the same result on every run, its failures must be
reproducible from the report, and a defect in it can hide a defect in MiniDAQ (SOUP list,
section 2). It runs inside GoogleTest, which the project already uses.

## Options

1. **RapidCheck.** The established C++ library, with GoogleTest integration, many generators and
   shrinking of values. It has no releases, so it would be pinned by commit, and it is a new
   item of test SOUP whose behavior the project must review and follow.
2. **GoogleTest with random inputs.** Parameterized tests over a seeded random generator. No new
   code at all, but no shrinking: a failure shows the full random input.
3. **A small harness of MiniDAQ's own** (`minidaq/tests/support/property.hpp`). Generators draw
   numbers from a source that records every choice; shrinking edits the recorded choices
   (deletes blocks, lowers values) and replays them, the approach of Hypothesis, so no
   generator needs shrinking code of its own.

## Decision

Option 3. The harness is about 250 lines, reviewed with the code and tested by the unit tests
(`Properties.TheHarnessShrinksACounterexample` shows that a false property fails and shrinks).
Its rules for evidence:

- The seed of each test is fixed, a hash of the test's name, so every run of a commit checks the
  same inputs; `MINIDAQ_PROP_SEED` changes it for a wider search and `MINIDAQ_PROP_CASES`
  multiplies the number of cases.
- A failure reports the seed, the case, the shrunk input and its choices;
  `MINIDAQ_PROP_REPLAY` replays them, so a failure from CI is reproduced on a desk.
- A property returns a verdict instead of using GoogleTest's assertions, because shrinking runs
  it many times and only the final counterexample is a failure.

## Consequences

### Positive

- No new SOUP in the test chain; the harness changes only through the project's own review.
- Shrinking works for any generator, including ones that build a sorter configuration and a
  stream together.
- The same seed rule keeps the property tests as repeatable as the example-based ones.

### Negative

- Fewer ready-made generators than RapidCheck, and shrinking that finds a locally minimal
  counterexample (no single deletion or lowering still fails), not always the smallest one.
- The project maintains the harness. A team that already uses RapidCheck should weigh that
  against adding it as test SOUP with a pinned commit and a review record.
- A fixed seed explores the same inputs on every run; the wider search with another seed or more
  cases has to be run deliberately, before a release (`tools/release_checks.sh`).
