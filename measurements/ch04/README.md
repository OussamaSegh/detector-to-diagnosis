# Chapter 4 raw measurements

Machine: 4 vCPU Intel Xeon @ 2.30 GHz (Firecracker VM), Linux 6.18 PREEMPT_DYNAMIC (not
PREEMPT_RT), clock source tsc, GCC 13.3 -O2 (release preset), run as root, 2026-10-24.
Load: `stress-ng --cpu 4 --vm 2 --vm-bytes 256M --io 1`.

- `cyclictest/`: `cyclictest -m -t1 -a1 -i200 -D30 -h20000 -q` with `--policy=other` (no `-p`;
  confirmed SCHED_OTHER with `chrt -p`) or `--policy=fifo -p80`.
- `latency/`: `minidaq_latency --rate 10e6 --seconds 20 --batch 4096 [--profile ...]`, three
  repetitions, end-to-end latency measured from the due time (`PipelineConfig::due_time_ns`).
  These runs predate the `behind schedule` field; the backlog in the chapter is
  200 M offered words minus delivered minus dropped. `run_matrix.sh` is the script used.

The histograms are the evidence for the chapter's tables; the tables are derived from them.
