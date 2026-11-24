# Part 3 run again: ACC-04 on the soak of 2026-11-24 (MDQ-PR-096)

Release 2.2.0, candidate 5647d2e. Every check of part 3 passed (the soak's own verdict PASS:
no loss, no fault, complete, memory flat), but `tools/acceptance.py` judged ACC-04 FAIL: 8 of
600 intervals had a 99th percentile above 10 ms, where six are allowed (98.7%, 99% required);
the highest 62.65 ms. The first result is kept in `first-part-3/`.

Investigation (SDP section 8):

- **Every peak is a scheduling wait.** In each of the 8 intervals one server thread waited
  21 to 61 ms in a single second to be given a CPU while it was runnable (`runq_wait_1s_max_ms`:
  mdq-write three times, mdq-decode three times, mdq-sort twice). The pipeline runs at 1 M
  singles/s, about 4% of its measured capacity (ACC-01: 26.6 M/s), so a 10 ms stall is not work
  the threads had to do.
- **The machine was busier than at 2.1.0.** Steal time over the 10 s intervals: mean 0.66%,
  max 1.46% (2.1.0's soak: mean 0.25%, max 0.81%); per second up to 6.79% (2.1.0: 4.03%).
- **The code the soak runs did not change in what it does.** The soak uses the default
  configuration, one readout node; CR-0037's `PacedSource` then calls the same generator as
  before (`SyntheticSource::generate` now loops over `next()`, the same statements), and the
  regression gate of part 3 found no slower benchmark against book-v2.1.0, interleaved. No
  thread was added and no stage after the source changed.
- **The same symptom is MDQ-PR-064's**, closed by CR-0035 with no cause in MiniDAQ found
  (2 of 1,740 intervals at 2.0.x, 3 of 600 at 2.1.0).

Conclusion: the failure is of the machine, a 4-CPU virtual machine whose host withheld CPUs from
runnable threads more than at 2.1.0; it has its own problem report, MDQ-PR-096. Part 3 runs
again once, in full, on the same commit and into the same OUT. If ACC-04 fails again, the
failure is a problem report against the commit and the release stops for the software lead's
decision.
