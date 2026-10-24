# Exercise 2.1 (E): How many bytes per second?

**Goal.** Compute the data rate of a singles stream at 30 M singles/s for records of 8, 12
and 16 bytes, in bytes/s, GiB/s and Gbit/s, and how many records fit in a 64-byte cache
line. Then encode the arithmetic in `ex::stream_budget()` so the tests can check it.

**Time.** 30 minutes (most of it thinking about what the numbers mean: which link, which
memory bus and which disk can carry each rate?).

**Acceptance tests.** `tests/test_budget.cpp` checks the three cases and an edge case
(a record larger than a cache line). Write your interpretation in `ANSWER.md`.
