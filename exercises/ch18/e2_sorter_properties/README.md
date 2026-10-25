# Exercise 18.2 (M): Properties of a coincidence sorter

**Goal.** Write property-based tests of a fixed-window coincidence sorter with MiniDAQ's
harness (`minidaq/tests/support/property.hpp`), strong enough that each of eight plausible
mistakes in the sorter breaks at least one of your properties. Among them: every prompt is
inside the window, and in a fixed window each single is used at most once.

**Time.** 2 hours.

**Starter.** `starter/test_sorter_properties.cpp` has a generator and one property. The subject
is `tests/subject.hpp`: its comment is the specification, and `EX_MUTANT` selects one of eight
seeded mistakes. Read the specification, not the mutants.

**Acceptance** (run as `ch18/e2_sorter_properties/<variant>/...`):
- `original`: every property holds for the correct sorter.
- `mutant_1` to `mutant_8`: each mutant fails at least one property.

Then answer in `NOTES.md`: which mutants did invariant properties (ones that need no expected
answer) catch, which needed a reference implementation, and which needed a change to the
generator rather than a new property?

**Hints.** A property such as "no prompt is wider than the window" holds for a sorter that finds
nothing at all. The sorter is a pure function of its input whatever the batch sizes: that is a
property too. Count on the generator to find only what it can produce: how often does a uniform
random energy equal exactly 585 keV?
