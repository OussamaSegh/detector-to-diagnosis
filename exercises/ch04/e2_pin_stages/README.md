# Exercise 4.2 (M): Pin the pipeline stages and compare the tail

**Goal.** Generate a real-time profile for the MiniDAQ pipeline from the CPUs you are allowed
to use, apply it with `minidaq_latency`, and measure what pinning (and then `SCHED_FIFO`) does to
the end-to-end p99.9, idle and under load.

**Time.** 2 hours.

**Tasks.**
1. `ex::parse_cpu_list(text)`: parse the Linux *cpulist* format used by
   `/sys/devices/system/cpu/isolated`, `/proc/<pid>/status` (`Cpus_allowed_list`) and the
   `isolcpus=` boot parameter: comma-separated CPUs or inclusive ranges, for example
   `0-2,5,7-8`. Return the CPUs sorted and without duplicates. Surrounding whitespace (the
   trailing newline of a sysfs file) is allowed, and an empty string is an empty list (that is
   what `isolated` contains when nothing is isolated). Throw `std::invalid_argument` for
   anything else: `3-1`, `1,,2`, `-1`, `x`, `1-`.
2. `ex::assign_stage_cpus(cpus)`: place the five stages (source, decode, sort, pair, write)
   on the given CPUs. The first CPU is the *housekeeping* CPU, shared with the operating
   system. The three busy stages get a dedicated CPU each, in that priority order, from the
   remaining CPUs; pair and write, and any busy stage left without a dedicated CPU, run on
   the housekeeping CPU. Extra CPUs stay unused. An empty list throws
   `std::invalid_argument`.
3. `ex::make_profile(placement, fifo)`: build a `minidaq::rt::RtProfile` with memory locked and
   256 KiB of prefaulted stack. With `fifo`, *dedicated* stages get `SCHED_FIFO` (source 80,
   decode and sort 70); every shared stage stays `SCHED_OTHER`. Never two FIFO stages on one
   CPU: Section 4.1 shows what happens when you do.
4. Measure. Print the profile for your machine with
   `ctest --preset debug -R PrintsProfileForThisMachine -V`, save it as `my.conf`, then run
   `minidaq_latency --rate 10e6 --seconds 20 --profile my.conf` with and without
   `stress-ng --cpu $(nproc)` in another terminal, for the default profile, pinning only, and
   pinning plus FIFO. Record the end-to-end p50, p99, p99.9 and drops in your notes.

**Acceptance tests** (`tests/test_pin_stages.cpp`): cpulist parsing including the error cases,
placement for 1 to 8 CPUs, the "no two FIFO stages per CPU" property, and a round trip through
the library's profile format.

**Think about it:** your pipeline has five threads but the acquisition PC (assumption: confirm
with team) may have more cores. Which stage would you split first, and how would the profile
change?
