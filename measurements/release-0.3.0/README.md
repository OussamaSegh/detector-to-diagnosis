# Release 0.3.0 measurements

The evidence of the release record (`docs/regulatory/releases/0.3.0.md`). Each file starts with
the time, the commit and the command, except the JSON files, whose `context` has the time.

From the release candidate `4c3ac87`, before the release checks were a script:

- `perf-current-4c3ac87.json`: the gated benchmarks (`tools/perf_suite.sh`, 10 repetitions),
  the whole-pipeline row of the performance budget version 2.
- `perf-gate-old-baseline.txt`: `tools/perf_gate.py` against the baseline of tag `ch05`, the
  finding of MDQ-PR-014.
- `pipeline-attribution.txt`: interleaved runs of three commits that put the drop on `1b6bcd3`.
- `starters-release.txt`: the starters one by one in a `Release` build (CAPA-0004).

From the released commit `8821c48`, by `tools/release_checks.sh`: every other file, and
`release-checks.txt`, the script's list of passed checks. The run stopped once after the writer
benchmark, when the session that ran it was restarted; the rest of the script (the gate and
fuzzing) was resumed on the same clean commit, and `release-checks.txt` shows where.
`ci-run.txt` records the GitHub Actions run of the same commit.
