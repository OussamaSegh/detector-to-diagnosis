# Notes on the solution

- **Monotonic resource.** Allocation is a pointer bump inside `arena_`; deallocation is a
  no-op. "Freeing" a whole batch means re-creating the resource over the same buffer
  (`std::optional::emplace`), which costs a few stores. `monotonic_buffer_resource::release()`
  is the other way to reset it.
- **null_memory_resource upstream.** If a batch ever needs more memory than the arena,
  the upstream throws `std::bad_alloc` instead of silently calling `malloc`. Combined with
  the explicit capacity check, a capacity problem shows up as an error you can count, not
  as an unexplained latency spike.
- **Order of destruction.** The output vector lives in the arena, so it must be destroyed
  before the resource is reset. `out_` is declared after `resource_`, and `process()`
  resets `out_` first.
- **The span returned by `process()`** is valid until the next call. That is the contract
  of most DAQ stages (the downstream stage consumes a batch before the next one arrives);
  document it in the API.
- **A simpler fix exists:** keep a `std::vector` member, `clear()` it per batch (which keeps
  its capacity) and `reserve()` once in the constructor. For a single vector that is
  equivalent. The arena wins when a stage builds several temporary containers per batch
  (a list of multiples, a per-crystal map): all of them come from the same buffer and are
  released together.
- **Measured effect** (`build/release/benchmarks/bm_alloc`, 4 vCPU Xeon @ 2.30 GHz VM, GCC 13.3
  -O2): filtering 64 batches of 4,096 singles took 1.84 ms with a new vector per batch,
  1.62 ms with the monotonic arena and 1.66 ms with a reused vector. glibc's allocator is fast
  for this repetitive pattern, so the throughput gain is modest (about 12%). The bigger win
  is predictability: no call into `malloc` means no lock, no `mmap`/`brk` system call and
  no page faults in the hot path (Chapter 4 measures the tail latency).
