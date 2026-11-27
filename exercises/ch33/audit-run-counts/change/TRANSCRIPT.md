# The session, condensed

This session is reconstructed for the book. The change was written to hold defects that
MiniDAQ really had, and the dialogue is shortened to the steps that matter. It works from this
record alone: you do not need an agent to do the exercise.

**Person:** Implement `change/SPEC.md` in `run_counts.py`.

**Agent:** For the partition, a single either fails the energy window, finds no partner, is
one of a pair (two singles per pair) or is in a multiple; I'll check that these add up to
`singles_in`. For the recorded singles: the simulator generates until the end of the run, so
the count is the number it generated.

*(edits `run_counts.py`: the diff is `change/agent.patch`)*

**Agent:** Tests:

```text
test_partition_adds_up .............. ok
test_lost_single_is_reported ......... ok
test_recorded_singles ................ ok
Ran 3 tests in 0.001s  OK
```

Both checks pass on the three end-to-end runs of the chapter (seeds 1, 2 and 33).

**Person:** I'll review it.
