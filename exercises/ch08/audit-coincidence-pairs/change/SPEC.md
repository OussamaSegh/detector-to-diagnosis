# Task given to the agent

Add `find_pairs(singles, window_ps)` to `pairs.py`, the coincidence tools of Chapter 8.

- `singles` is any iterable of `Single(time_ps, crystal, energy_kev)`, in any order.
- A coincidence is two singles of different crystals whose times are at most `window_ps`
  apart, the limit included.
- The multiples policy is "take all goods": three or more singles in one window give every
  pair of them. Each pair of singles is one coincidence, counted once.
- The result is a list of pairs `(first, second)`, `first` the earlier single. Singles with
  equal times are ordered by crystal, then by energy (as SRS-SRT-013 asks of the sorter), so
  the result is the same list whatever order the singles are given in.
- Standard library only. Add tests.
