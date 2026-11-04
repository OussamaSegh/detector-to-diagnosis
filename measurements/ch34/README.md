# Chapter 34 measurements: a survey of MiniDAQ

- `survey.md`, `survey.json`:
  `tools/survey.py . --since 2026-10-01 --json measurements/ch34/survey.json` on the repository
  at Chapter 34, after CR-0021 removed the two prefixes of the item map that claimed no file.
  128 product source files in 22 items. The three items with an open problem report come first
  among the class B items: `service` (MDQ-PR-006), `sim` (MDQ-PR-009) and `sorter`
  (MDQ-PR-007). The top hotspot is `minidaq/src/control/acquisition_service.cpp` (13 commits,
  500 code lines). Two files are owned by `hw` through a longer prefix inside `config`'s
  directories.
- Before CR-0021 the same survey listed two prefixes that claimed no file:
  `minidaq/src/metrics/` (item `metrics`) and `minidaq/src/processing/count_rates` (item
  `processing`); both components are header-only.
- `coupling.txt`: the pairs of files under `minidaq/` changed in the same commits, from Exercise
  34.1's solution (the command is in the file). The two CMake files change together in 20
  commits; across items, `acquisition_config.hpp` and `acquisition_service.cpp` share 4 commits
  with degree 1.0.

The history is short (MiniDAQ's starts with the book), so the commit counts say more about the
order in which the chapters were written than about where defects gather; the method is the
point.
