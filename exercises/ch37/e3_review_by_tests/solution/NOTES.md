# Exercise 37.3: notes

The starter's two tests pass on all eight versions, so the seven mutant tests of the starter
fail (CTest expects each mutant to be caught). Each mutant is a fluent, plausible line:

1. `<` for `<=`: a pair exactly at the window's edge is lost. A sorter that loses edge pairs
   loses a fraction of true coincidences that grows with the timing resolution.
2. The wrap forgotten: a pair across the counter's wrap, about once a second at 1.1 s per period,
   is never coincident. A rate that dips once a second, invisible in a one-minute test.
3. One way around only: the result depends on the order of the arguments. Pairs arrive in either
   order from two boards; half of the coincidences of one board pair vanish.
4. Inputs masked instead of refused: a corrupt timestamp with high bits set pairs with a real
   single. That is a fabricated coincidence, the worst kind.
5. A 32-bit distance: two singles 4.3 ms apart, a multiple of 2^32 ps plus a little, are
   coincident. Rare, random, and impossible to find by looking at images.
6. The period off by one: a pair one picosecond apart across the wrap is at distance 0. Only a
   window of 0 shows it, which is why the edge tests use windows of 0 and 1.
7. The window's limit missing: a window of half the circle or more makes everything coincident.
   A configuration error turns into data instead of a refusal.

Design choices:

- One test per clause of the requirement, named after the clause, each with the values on both
  sides of its edge. The mutants were not looked at to write them; every one is caught because
  every clause has its edge tested.
- The constants come from the subject (`kPeriod`), and the values are written so a reader sees the
  edge: `10'000 + W` and `10'000 + W + 1`.
- To the questions: a reader notices 1, maybe 2 and 7; 3 to 6 read as reasonable code. An
  assistant's own tests are written by the same reasoning as its code, from the same reading of
  the requirement, so they share its blind spots: they show the code does what its author
  thought, which the review is there to question. Tests 3, 5 and 6 come from the requirement's
  words ("independent of their order", "40-bit", "shorter way around"); without the requirement
  in front of you, you test what the code seems to do.
