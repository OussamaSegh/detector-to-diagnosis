# Exercise 19.4 (M, extra): The test that finds an integration defect

**Goal.** Write tests of two units put together, a batcher and a pairer, that each of five seeded
mistakes fails. Each unit alone is correct for one batch; the mistakes are in how they work
together across batch boundaries, and in one rule that no batching can show. This is the shape of
MiniDAQ's defect MDQ-PR-017 (Chapter 19): ties in time ordered differently when they straddled a
batch boundary.

**Time.** 2 hours.

**Starter.** `starter/test_batching.cpp` has one hand-worked example. The subject is
`tests/subject.hpp`; its first comment is the specification, and `EX_MUTANT` selects a mistake.
Read the specification, not the mutants.

**Acceptance** (run as `ch19/e4_batching_test/<variant>/...`):
- `original`: your tests pass for the subject as specified.
- `mutant_1` to `mutant_5`: each mutant fails at least one of your tests.

Then answer in `NOTES.md`: which mutants did a metamorphic relation (the same stream in other
batches gives the same pairs) catch, and which needed an expected answer? What did your stream
generator need to contain for each?

**Hints.** The specification says the result is the same for every batch size: that is a test
you can write without knowing any answer. Boundaries are where batches end; a batch size that
does not divide the stream's length leaves a short last batch. Count on the generator to produce
only what it can: how often does a uniform random time equal the previous single's?
