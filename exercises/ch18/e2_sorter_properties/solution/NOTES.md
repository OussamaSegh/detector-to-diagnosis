# Exercise 18.2: notes on the solution

Five properties: agreement with a reference sorter, every prompt inside `[0, window]`, no single
in two prompts, batch sizes do not matter, and the accounting identity. The generator draws
each time step from five kinds (the same time, exactly one window, within a window, up to five
windows, backwards) and each energy from four (each edge of the gate, inside, anywhere), so the
boundaries of the specification come up in most cases.

| Mutant | Mistake | Caught by |
|---|---|---|
| 1 | the window excludes its edge (`>=`) | the reference, with a partner exactly one window later |
| 2 | the window is measured from the last single (paralyzable) | the window property |
| 3 | the second single of a pair opens the next window | no single in two prompts; the window property; the accounting identity |
| 4 | the open window is dropped at the end of each batch | batches do not matter; the accounting identity |
| 5 | the gate excludes its upper edge | the reference, with an energy of exactly 585 keV |
| 6 | singles out of order are not dropped | the window property (a negative time difference); the reference |
| 7 | a lone single at the end of the run is not counted | the accounting identity |
| 8 | take_winner keeps the lowest summed energy | the reference |

Invariants (window, used once, batches, accounting) caught 2, 3, 4, 6 and 7 without knowing any
answer. Mutants 1, 5 and 8 produce output that satisfies every invariant: a stricter window and
a stricter gate find fewer prompts, all valid, and a wrong winner is still a valid pair. Only a
reference, an independent way to compute the answer, catches them. The reference is shorter
than the sorter because it may be slow: it sees the whole stream at once.

The starter's generator draws energies uniformly from 0 to 1000 keV, so a float equal to 585.0
is about one draw in a billion: mutant 5 survives any property with that generator. The fix was
in the generator, not in a property. The same holds for mutant 1 and time steps.

With the starter's generator and single property (`<= window`, no lower bound), only mutant 3
is caught in the 200 cases of a normal run (CTest shows `mutant_3` as passed: the run failed, as
it should). Mutant 2, the paralyzable window, survives them; with `MINIDAQ_PROP_CASES=50`
(10,000 cases) the same property finds it and shrinks the input to three singles: a window of
3317 ps and singles at 0, 1 and 3318 ps, where the third joins because it is within the window
of the second. A rare input needs either many cases or a generator that makes it common.
