# CR-0025: the gate's baseline and the latency limit

`compare.py` applies the criteria that CR-0025 sets for release 1.0.0 to the evidence that
releases 0.7.0 to 0.9.0 already recorded, and `compare.txt` is its output. Nothing was measured
again: the inputs are the interleaved benchmark runs of `release-0.8.0/perf-interleaved/` and
`release-0.9.0/perf-interleaved/`, and the soaks' `samples.csv`.

- Gate, against the previous release run interleaved the same day (two rounds of ten
  repetitions per side, pooled): the 0.8.0 and 0.9.0 candidates pass. Against the recorded
  baseline `benchmarks/baseline/book-vm.json` both failed, on the energy filter, with no change
  to the code it runs.
- Power of that comparison on the same data: the 0.9.0 samples made 3% slower are not flagged,
  7% slower flag 2 of the 6 benchmarks, 10% slower 5 of 6, 15% slower all 6. The threshold
  (5%) and the significance level (0.01) are those of `tools/perf_gate.py` since Chapter 5. A
  release's own run has five rounds of two (`tools/perf_ab.sh ... 5`), the same ten repetitions
  per side.
- Latency, at least 99% of the 10 s intervals at or below 10 ms: releases 0.7.0 (180 of 180) and
  0.9.0 (179 of 180) pass; release 0.8.0 (165 of 180) and the programs of 0.7.0 on 0.8.0's day
  (167 of 180) fail. The rule removes a single disturbance in a 30-minute soak, not a bad day.
