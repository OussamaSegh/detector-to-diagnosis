# The coincidence sorter's surviving mutants

The review of `mutation-sorter-final.txt` (`tools/mutation_test.py` on
`minidaq/src/processing/coincidence_sorter.cpp` with `CoincidenceSorter.*` and `Properties.*`,
after the tests of Chapter 18): 10 survivors, each argued equivalent here. A reviewer checks the
argument, not the score.

| Mutant | Why no test can kill it |
|---|---|
| 92:30 `sa > sb` to `sa >= sb` | When the sectors are equal both branches compute 0. |
| 105:38 `cross * cross > fov_r2_ * len2` to `>=` | Only a line exactly on the field-of-view boundary, in double arithmetic, tells them apart; a configuration cannot aim at that equality reliably, and the specification does not say which side such a line falls on. |
| 153:3, 153:14 (2), 153:21, 153:35 (2), the compaction condition | They change when the buffer of singles is compacted (never, always, or at another fill level). Compaction moves data and adjusts indices; it never changes which coincidences are found or the counters. A mutant that never compacts grows the buffer with the run, which the benchmarks and the memory budget see and a unit test does not. |
| 279:35 `delayed_begin_ > first_` to `<=` or `>=` | `delayed_begin_` is never less than `first_` when `compact()` runs (the delayed window starts after the prompt window ends), so `>=` gives the same value, and `<=` resets the index to 0, which makes the next delayed window rescan from the opener and find the same singles. Without a delay the index is never read.

The 11 survivors of `mutation-sorter-properties.txt` that are not in this list were gaps; the
tests `TheLimitsOfTheConfigurationAreInclusive`, `GeometryCutsDoNotDependOnOrderOrOrientation`
and `DelayedMultiplesFollowThePolicy` kill them, and SRS-SRT-007 now states the delay's limit.
