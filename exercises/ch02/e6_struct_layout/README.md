# Exercise 2.6 (E, extra): Shrink a struct by reordering its fields

**Goal.** `DetectorStatus` (one per detector block, sent with every status packet) is
40 bytes because of padding. Reorder its members so it fits in 24 bytes, without changing
any member's type or name. Then explain where each padding byte was.

**Time.** 20 to 30 minutes.

**Acceptance tests.** `sizeof(DetectorStatus) <= 24`, every member still exists with the
same type, and an aggregate-initialized value round-trips through `memcpy`.
