# Exercise 33.1 (E): Counts that add up

**Goal.** Write the conservation equations of the coincidence sorter as a function that a test,
or a whole end-to-end run, can call: given the sorter's counters after `flush()` and the
coincidences it wrote, name every equation that does not hold.

**Time.** 1 hour.

**Starter.** `starter/accounting.cpp` checks the partition of the singles and nothing else. A
sorter that counted a prompt it never wrote, or a pair window that was neither a prompt nor
rejected, would pass it.

**What to check.** For a sorter in `WindowMode::fixed` with `MultiplesPolicy::kill_all`:

1. `singles`: every single that entered is in exactly one place,
   `singles_in = energy_rejected + out_of_order + singles_alone`
   `+ 2 pair_windows + singles_in_multiples`.
2. `pair windows`: every window of two singles became a prompt or was rejected by geometry,
   `prompts + geometry_rejected = pair_windows`.
3. `multiples`: kill_all keeps nothing from a multiple, `prompts_from_multiples = 0`, and every
   multiple window holds at least three singles, `3 multiple_windows <= singles_in_multiples`,
   with no singles in multiples when there are no multiple windows.
4. `prompts written`: the prompts among the coincidences equal `prompts`.
5. `delayed written`: the delayed among them equal `delayed`.

**Acceptance** (`tests/test_accounting.cpp`):
- The sorter's own counters over 200,000 random singles, pushed in chunks of random sizes,
  with out-of-order singles mixed in, satisfy every equation.
- Each counter but one, raised or lowered by one, makes at least one equation fail, and the
  failing equation is the one the test names.
- A coincidence lost between the sorter and the file fails `prompts written` or
  `delayed written`.

**Then, by hand.**
1. One counter, `multiple_windows`, can be off by one without failing any equation. Why can no
   equation over these counters catch it? What would the sorter have to count to make it
   checkable?
2. Under `take_all_goods`, equation 2 no longer holds. Write the equation that replaces it, and
   say which counter the sorter would need to add.
3. Why is an off-by-one test of the equations worth having, when the sorter's own tests pass?

**Hints.** Use unsigned arithmetic only where it cannot wrap: compare sums, not differences.
Return the names in the order above, so that a report reads the same on every run.
