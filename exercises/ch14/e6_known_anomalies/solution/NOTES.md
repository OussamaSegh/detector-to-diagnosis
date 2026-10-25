# Exercise 14.6: notes

**When MDQ-PR-005 would become relevant to safety.** The evaluation rests on one fact: every
integer MiniDAQ reads is checked with `is_number_integer()`, so a value parsed as a float is
rejected, never used. Evidence that would change the answer:

- a place where MiniDAQ reads a number with `get<double>()` or `get<int>()` without the
  integer check (a `grep` of the reader and the protocol answers it, and a test should pin it);
- a client that treats an `id` echoed as `2.0` as a different request and repeats a `start`
  or `stop` (the reference client compares IDs; a third-party client might not);
- a value whose float rounding changes it: integers above 2^53 have no exact `double`. MiniDAQ's
  64-bit `seed` is read through the unsigned-integer check (`is_number_unsigned()` in
  `acquisition_config.cpp`), so today such a seed is refused, not rounded; a reader that
  accepted any number for it would change the answer.

Each would turn "a refused request" into "a different setting", which is HZ-3.
