# CR-0038: the first interleaved soak

`ab-trial/`: `tools/soak_ab.py` on 2026-11-24, about 20:05 to 23:40 UTC, on the release machine
(a 4-CPU virtual machine), with the `release` preset: the previous release, book-v2.2.0
(c4b5ca3), built from its tag in a scratch worktree, against the candidate at 2cdb8e1 (2.3.0-dev:
no file of `minidaq/src`, `apps` or `include` has changed since 2.2.0 but the two lines of
whitespace of MDQ-PR-102). Five blocks of 20 minutes each, in the order A B, B A, A B, B A, A B.
The run was stopped by the two-hour limit after five blocks and run again with the same OUT: it
kept the five and ran the other five (the resume of CR-0038).

| Side | Intervals above 10 ms (of 600) | Highest p99 | Steal, mean | Memory trend |
|---|---|---|---|---|
| book-v2.2.0 (`base/summary.txt`) | 2 | 41.94 ms | 0.59% | +0.035 MiB/h (SE 0.041) |
| candidate (`head/summary.txt`) | 5 | 116.39 ms | 0.56% | +0.041 MiB/h (SE 0.041) |

- ACC-04 on the candidate: 5 of 600, within the six allowed. PASS.
- ACC-10 (`compare.txt`): p = 0.2259 one-sided, PASS. The test's power to find a doubled rate
  is 9% at the previous release's rate of 0.33%: at rates this low, 600 intervals a side cannot
  show a doubling. ACC-10 can tell the code from the machine when the machine is busy (as on the
  day of 2.2.0's release, 8 and 11 of 600), which is when it is needed; on a quiet day it says
  little, and ACC-04 decides.
- The same programs of 2.2.0 had 8 and 11 slow intervals of 600 at their release
  (`measurements/mdq-pr-096/`) and 2 here: the machine's state, not the code, moved the count.
- The summaries of the previous release's blocks named its programs by the scratch worktree's
  absolute path; they were edited to "the previous release's build", and `tools/soak_ab.py`
  now writes it so (MDQ-PR-103).
