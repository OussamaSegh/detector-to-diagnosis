# Audit report: the agent's count checks (Exercise 33.5)

Not mergeable. One check leaves out a counter, the other counts a single the run never
recorded. Both are MiniDAQ's own defects, found while writing and reviewing Part VIII.

## Defect 1: the partition leaves out the out-of-order singles (MDQ-PR-059)

The sorter's report has six counters, and the agent's sum has four terms besides
`singles_in`: `out_of_order` is missing. A good run with one single out of time order fails
the check as a lost single, and an `out_of_order` counter that is wrong passes it, since no
equation contains it.

- *Test:* `test_a_run_with_out_of_order_singles_adds_up`, and the `out_of_order` case of
  `test_every_counter_off_by_one_is_a_problem`.
- *Why three runs passed:* none of them had a single out of order, so the missing term was
  zero. A check that passes on the data it was written with says nothing about the term it
  leaves out. MiniDAQ's own test of the equations built its counters without `out_of_order`,
  and could not see the gap either.
- *Correction:* five terms.

## Defect 2: the single generated at the end is counted as recorded (MDQ-PR-055)

`generate_until(end)` keeps the first single at or after the end for the next call; it was
generated, not recorded. The agent counts every generated single, so the expected count is
one too high: a good run fails the comparison with the singles `minidaq_send` sent, and a check
"fixed" by allowing a difference of one would then let a run that lost a single pass.

- *Test:* `test_the_single_the_simulator_generated_at_or_past_the_end_is_not_recorded` and
  `test_recorded_singles_match_what_the_sender_sent`.
- *Effect:* MiniDAQ's simulator printed the same number as "recorded singles", one more than
  its list mode, its sorter report and its count rates used, over three seeds.
- *Correction:* count the times before `end_ps`.

## Verdict

Request changes. A count check needs a test for each term with that term non-zero and off by
one, and a test at the boundary of the run: the agent's tests had neither.
