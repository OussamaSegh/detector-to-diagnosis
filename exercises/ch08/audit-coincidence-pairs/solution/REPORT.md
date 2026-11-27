# Audit report: the agent's find_pairs (Exercise 8.6)

The change is not mergeable. It has two defects, both of which MiniDAQ's sorter once had.

## Defect 1: every pair is counted twice (MDQ-PR-004)

Each single opens a window on both sides, so the pair (a, b) is found in a's window and again
in b's. The specification says each pair of singles is one coincidence, counted once.

- *Test:* `test_n_separated_annihilations_give_n_pairs` (100 decays give 200 pairs) and
  `test_chance_pairs_of_independent_detectors_match_two_tau_s1_s2`: about 4,000 chance pairs
  where 2 tau S1 S2 predicts 2,000, more than forty standard deviations away.
- *Effect on a scan:* every prompt is duplicated. The sinogram has twice the counts, with the
  noise of half of them, and nothing looks wrong: the image is only scaled. The randoms
  estimate from a delayed window is doubled the same way, so even the randoms fraction looks
  right. Duplicated prompts bias the counts and the image quantitatively without any visible
  sign (the evaluation of MDQ-PR-004).
- *Correction:* resolve only (opener, later single) pairs: look forward from each single.

The agent's own tests could not see it: each of them has exactly one pair, and the transcript
calls the symmetric window a feature.

## Defect 2: the order of singles with equal times is the order they arrived in (MDQ-PR-017, MDQ-PR-027)

The sort key is the time alone. Python's sort is stable, so singles with equal times stay in
the order they were given, and the result depends on it: for two singles at the same time,
which one is `first` changes with the input order. The specification asks for the order by
crystal, then energy, and the same list for any order of the input.

- *Test:* `test_the_result_does_not_depend_on_the_order_of_singles_with_equal_times` and
  `test_a_pair_with_equal_times_starts_with_the_lower_crystal`.
- *Effect:* two runs of the same data, read in batches of another size or from two links
  merged in another order, give different records (MDQ-PR-017); the coincidence's first and
  second single, and so its line of response orientation and time difference sign, depend
  on the arrival order (MDQ-PR-027).
- *Correction:* sort by (time, crystal, energy).

## Verdict

Request changes. Ask for the two corrections and for tests that state the physics: N separated
decays give N pairs, and chance pairs follow 2 tau S1 S2. The claim "the sort makes the output
deterministic" in the transcript is the kind of statement to check, not to accept: a sort is
deterministic only for keys that are unique.
