# Exercise 14.2: notes

- The linter catches form, not content. "The sorter shall pair two singles at most 4000 ps
  apart" passes, and would be wrong if the window were exclusive. The check against the code
  and the tests is the review's job.
- Several requirements state a default in parentheses. The default is configuration, so the
  requirement is the behavior ("the configured window"); the default value belongs to the
  configuration's documentation and has its own test (SRS-CFG-001).
- SRS-SRT-120 (latency) is the requirement that problem report MDQ-PR-007 is about: the sorter
  can only close a window when a later single shows that it is closed. Writing it as "at the
  latest when it receives a single more than the window plus the delay later" makes it
  testable without a clock.
- SRS-SRT-121 (throughput) is verified by measurement: the reference machine, the preset and
  the benchmark are part of the evidence, and the number must be measured again on the
  acquisition PC.
