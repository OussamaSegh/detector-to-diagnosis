# Task given to the agent

Implement the two count checks of the end-to-end run in `run_counts.py` (Chapter 33):

1. `recorded_singles(generated_ps, end_ps)`: the number of singles the run recorded. The
   simulator's `generate_until(end)` stops at the first single at or after `end` and keeps it
   for the next call; `generated_ps` holds the times of every single it generated, that one
   included. A single is recorded if its time is before `end_ps`. The check compares this
   number with the singles `minidaq_send` sent from the same seed.
2. `partition_problems(c)`: the sorter's report accounts for every single it received exactly
   once. Its counters are `singles_in`, `energy_rejected`, `alone`, `pairs` (each of two
   singles), `in_multiples` and `out_of_order`. Return a problem if they do not add up.

Add tests.
