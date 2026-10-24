# Exercise 2.3 (M): Take the heap out of the event loop

**Goal.** `EnergyWindowStage::process()` filters a batch of singles into an output batch.
The starter creates a new `std::vector` for every batch. Make the steady state
allocation-free using `std::pmr::monotonic_buffer_resource` over a buffer allocated once
in the constructor, then measure the difference.

**Time.** 60 minutes.

**Acceptance tests** (`tests/test_stage.cpp`, which replaces global `operator new` with a
counting version):
- Results are correct (only singles inside the window, in input order).
- After the first batch, 1,000 further batches cause **zero** calls to global `operator new`.
- A batch larger than the configured capacity is rejected with an error instead of
  allocating. (Silent growth in the hot path hides capacity problems.)

The allocation test is skipped under AddressSanitizer, which installs its own allocator.
