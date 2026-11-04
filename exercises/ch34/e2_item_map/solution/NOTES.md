# Exercise 34.2: notes

The starter fails six of the seven tests: its owner is the first match, so it changes with the
order of the map, it never raises for an ambiguous owner, and it reports no shadowed file, no
dead prefix and no count.

Design choices:

- `claims` keeps, for each item, its longest matching prefix: an item with two prefixes that both
  match a file (`src/` and `src/a/`) competes with the longer one.
- `owner` raises; `check_map` catches and lists. A function that answers one question should
  refuse a question with no answer; a report about the whole map should report every problem and
  not stop at the first.
- The ambiguous message names the items in sorted order, so that it does not depend on the map's
  order either.

By hand:

1. The survey lists `minidaq/include/minidaq/config/hardware_config.hpp` and
   `minidaq/src/config/hardware_config.cpp` as owned by `hw` and shadowed by `config`, and the
   dead prefixes before CR-0021 were `minidaq/src/metrics/` and
   `minidaq/src/processing/count_rates` (both components are header-only). Moving the two
   hardware configuration files into `hw/` would make the directories tell the truth, at the cost
   of every include of them and their history under `git log` without `--follow`; leaving them
   costs a sentence in the architecture description. Either is defensible; leaving the map silent
   about it is not.
2. The report is read to find every problem of the map at once; raising at the first ambiguous
   file would hide the others and the rest of the report.
3. A file without an item has no safety class, so the rigor of its review is undefined: that is a
   gap in the classification. A dead prefix claims nothing, so nothing is misclassified; it is a
   sign that the map and the code have drifted, worth fixing but not a failure.
