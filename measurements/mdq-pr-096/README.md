# MDQ-PR-096: ACC-04 on the release soak of 2.2.0

Three 100-minute soaks at 1 M singles/s on the release machine (a 4-CPU virtual machine), on
2026-11-24, with `tools/soak.py` (summary and samples of each):

| Soak | Programs | Intervals above 10 ms (of 600) | Highest p99 | Steal, mean |
|---|---|---|---|---|
| `first/` | candidate 5647d2e, release checks part 3 | 8 | 62.65 ms | 0.66% |
| `rerun/` | candidate 5647d2e, part 3 run again | 11 | 20.45 ms | 0.83% |
| `control-2.1.0/` | book-v2.1.0, built the same day | 6 | 20.97 ms | 0.71% |

ACC-04 allows six. 2.1.0's own release soak had 3 (`measurements/release-2.1.0/soak/`). Each
interval above the limit, in all three soaks, has one server thread that waited 20 to 95 ms in
one second for a CPU while runnable. The candidate's 19 of 1,200 against the control's 6 of 600
is a rate 1.6 times as high, which two soaks cannot tell from chance; the control's own count is
twice its count at release, on the same programs.

`rerun/perf-gate.txt`: the regression gate of the rerun judged `BM_SortFunctor` slower (0.862,
p 0.0026), after passing it in the first run. `bm_sort_functor.s` is the benchmark's machine
code, the same instruction for instruction (addresses aside) in the candidate's and in
book-v2.1.0's build.
