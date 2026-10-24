# Exercise 10.4: performance report (solution)

**Setup.** Book VM: Intel Xeon @ 2.30 GHz, 4 vCPU; GCC 13.3, `-O2 -DNDEBUG` (preset
`release`). Input: 20 ms of simulated 20 MBq data (90 mm water phantom), pushed in batches
of 4096; 44.9% of the singles pass the 435 to 585 keV window. Policy take winner of goods,
delayed window on, 120 mm field of view. Rates are singles inside the energy window per
second, best of five runs inside the test; the test was run five times.

**Before.** The baseline sorts 16.0 to 16.7 M singles/s. A profile of only the sorter's
samples (`perf record -F 20000 -e cpu-clock -g`, 10 repetitions, 6,278 samples whose call
chain passes through the sorter):

| Where | Share | Why |
|---|---|---|
| `close_ready` | 53.2% | indexing a `std::deque` while scanning the buffer for each window |
| `malloc`, `_int_free`, `cfree`, `operator new` | 26.5% | two `std::vector`s built for every window |
| `__sincos_fma` | 12.0% | crystal positions recomputed for every pair (field-of-view cut) |
| `resolve` | 7.0% | the windows themselves |
| `std::function` call | 0.5% | the callback per coincidence: cheap here, despite its reputation |

**Changes** (all in `solution/fast_sorter.cpp`):
1. A `std::vector` buffer with an index for the next opener and one compaction every few
   thousand singles, instead of a `std::deque` with a `pop_front` per single.
2. Windows as index ranges into that buffer: no vector per window, no allocation at all in
   the steady state.
3. Crystal positions from `crystal_xy_table` and sectors from a `constexpr` table;
   the field-of-view test compares squared distances, so no `hypot` and no division.
4. The delayed window's start index carried from opener to opener, since it only moves
   forward.
5. Coincidences appended to the output vector directly.

**After.** 40.7 to 41.3 M singles/s, 2.47 to 2.55 times the baseline, over the 30 M/s
target with a margin of about a third. The changes were made together; a report on your own
work should measure them one at a time, because the profile above only says where the time
was, not how much each change recovers (the allocations and the deque, together 80% of the
time, are the obvious first two).

**Next.** At 41 M/s a single costs about 24 ns. What remains is the per-window scan and
the copies of 16-byte singles into each coincidence. A structure-of-arrays buffer (times
in one array) would make the window scan a run over 8-byte values. Before going further,
check where the pipeline's real limit is: the stream merger of Chapter 10 manages only
14 M singles/s for 24 boards on the same machine, counting all singles before the energy
gate (`measurements/ch10/bench_sorter.txt`), so a faster sorter alone changes nothing end to
end.
