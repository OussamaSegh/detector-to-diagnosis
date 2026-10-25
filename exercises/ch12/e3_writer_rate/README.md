# Exercise 12.3 (H): A writer that keeps up with the sorter

**Goal.** Make the list-mode writer sustain the sorter's rate on a disk whose fsync is
slow, without giving up durability: every coincidence written, everything on stable
storage when the run closes, and a stated bound on what a power cut can take. Then
measure your own disk and write down the fsync policy you would ship. This is the plan's
"make the writer sustain the sorter's rate on your disk; document fsync policy".

**Time.** 6 hours.

**Starter.** `starter/fast_sink.cpp` is a correct sink that writes and fsyncs every
64 KiB block on the caller's thread: safe, and with a 20 ms fsync limited to about
200,000 coincidences per second. Keep its public interface and its guarantees; change
everything else. You may use `minidaq::listmode` for encoding and `FileOps` for the
disk, but not `minidaq::control::ListModeSink`, which is a solution.

**Acceptance** (`tests/test_fast_sink.cpp`; the disk is simulated: 20 us per write,
20 ms per fsync):
- 500,000 coincidences in batches of 4,096: `write()` costs at most 0.5 s more than
  encoding the same records does on your machine and build, no more than two `write()`
  calls take as long as one fsync, and the file holds exactly the input, ending with an
  end-of-run block. (The starter waits 2.5 s for the disk.)
- A trickle of 4,096 coincidences every 10 ms: fewer than one fsync per three blocks,
  every written byte covered by an fsync that ends within `max_unsynced` (100 ms) plus
  one fsync plus 50 ms of scheduling slack, and the last fsync covers the whole file.
- A disk that fills up: `close()` and `fault()` report "No space left on device", and
  nothing hangs.

**Then, by hand.** Build Release and run
`build/release/benchmarks/writer_throughput --dir DIR --coincidences 200e6 --fsync F`
for F = none, close and interval (`--every 16` and `--every 256`) on the disk you would
acquire to, with a run longer than the kernel lets dirty pages grow (`sysctl
vm.dirty_ratio`). In `NOTES.md`: the sustained rate of each policy against the rate the
sorter produces (Chapter 11), the fsync policy you choose, what a power cut can take
with it, and how much memory the buffers cost.

**Hints.** Who must wait for an fsync, and who must not? One fsync can cover many
blocks; what decides how many? A bound in time holds at any rate, a bound in blocks
only at one. A thread that only waits for blocks never notices that it is time to sync.
