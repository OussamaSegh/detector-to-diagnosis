# Exercise 10.2 (M): Multiples policies

**Goal.** Implement the four multiples policies of MiniDAQ's sorter (kill all, take all
goods, take the winner of goods, keep if only one is good) as one function that resolves
one window. Then use `minidaq_sim` to see what each policy does to the trues and randoms
as the activity rises, and write down which one you would choose for a brain scanner and
why.

**Time.** 2.5 hours.

**Starter.** `starter/policies.cpp` gets `kill_all` right and keeps every pair for every
other policy, without asking whether a pair is good. `driver.cpp` (provided, the same in
starter and solution) forms fixed windows and calls your `resolve` for windows of three
or more singles.

**Acceptance** (`tests/test_policies.cpp`):
- One window by hand: the right pairs for each policy, the energy winner, the tie rule,
  and nothing when no pair is good.
- On simulated data at 5 and 30 MBq, with a sector cut and a 120 mm field of view, every
  policy gives exactly the coincidences of MiniDAQ's `CoincidenceSorter`.
- The policies keep, in decreasing order: take all goods, winner, only one good, kill all.

**Then, by hand.** Run
`build/release/minidaq/apps/minidaq_sim --activity A --seconds S --policy P --sectors 1 --fov 120`
for activities from 1 to 40 MBq and the four policies (or read
`measurements/ch10/validation.txt`). Plot trues per second and the randoms fraction of
the prompts against activity, one line per policy. One paragraph: which policy, and what
the delayed-window estimate of the randoms would need to be corrected for.

**Hints.** Write the list of good pairs once; every policy is a short rule about that
list. Why does `keep_if_only_one_good` without any geometry cut behave exactly like
`kill_all`?
