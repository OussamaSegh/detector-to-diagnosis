# Exercise 19.4: notes on the solution

Five tests: the starter's example, two hand-worked examples (two candidates in one window; a tie
in descending crystal order), the metamorphic relation over 50 random streams and batch sizes 1
to 17, and the invariants (every pair in its window, in time order, two singles each).

| Mutant | Mistake | Caught by |
|---|---|---|
| 1 | a tie is put in crystal order only within its batch | the relation, with ties in the stream |
| 2 | every single is paired at the end of its batch, window open or not | the relation |
| 3 | the last, short batch is dropped | the relation, with a size that does not divide |
| 4 | the last single of a batch is the first of the next one again | the relation |
| 5 | the last candidate in a window is the partner, not the first | the hand-worked examples |

The metamorphic relation caught four mutants without one expected answer: the result with one
batch is the oracle for every other batching. Mutant 5 is consistent across batchings, so no
batching can show it; only an example with two candidates in one window, computed by hand from
the specification, does.

Mutant 1 is MDQ-PR-017 in small. With a generator whose time steps are never zero, the
metamorphic relation passes it (checked: with gaps from 1 instead of 0 and no forced ties, all
five tests pass against mutant 1). The generator forces a tie in 30% of steps, so ties straddle
boundaries in every stream. MiniDAQ's own properties did produce ties, but they fed the sorter
directly, without the sort stage and its batches, and their reference took ties in the same order
of arrival as the sorter, so the two agreed. The defect needed the batches of the sort stage, and
only the system test, through the real pipeline, had them.
