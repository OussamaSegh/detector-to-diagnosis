# Exercise 33.1: notes

The starter passes only the test of the sorter's own counters, which do add up. Of the twenty
off-by-one counters it catches the ten in the partition of the singles; it never notices a
coincidence lost on the way to the file, nor a multiple window of two singles.

Design choices:

- Every equation is written as sums on both sides, never as a difference, so that no unsigned
  subtraction can wrap and hide an error.
- The names are fixed strings in a fixed order. A report that lists "pair windows" today and
  "pairs" tomorrow cannot be compared between two runs, and the end-to-end report of Chapter 33
  is compared between releases.
- The equations for the written coincidences count the records by kind. A total alone would let
  a delayed coincidence written as a prompt pass.

By hand:

1. `multiple_windows` appears only in an inequality (`3 multiple_windows <= singles_in_multiples`)
   because a multiple window holds any number of singles from three up. No sum of the other
   counters determines it. To make it exact the sorter would count the singles in multiples by
   window size (windows of 3, of 4, of 5 or more), or count the candidate pairs it considered in
   multiples, which kill_all never does.
2. Under take_all_goods a multiple of n singles in fixed mode has n(n-1)/2 candidate pairs, each a
   prompt or rejected by geometry, so
   `prompts + geometry_rejected = pair_windows + pairs_in_multiples`. The sorter would need the
   counter `pairs_in_multiples` (the sum of n(n-1)/2 over its multiple windows).
3. The sorter's tests check the sorter. The off-by-one test checks the check: an equation that
   can never fail looks exactly like an equation that holds. Chapter 33's end-to-end test does
   the same for every counter of the chain
   (`Accounting.test_every_counter_off_by_one_fails_a_check`).
