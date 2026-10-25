# Exercise 11.3 (H): Find the first bottleneck

**Goal.** Raise the rate through MiniDAQ's pipeline until something gives, and say which
stage gave first, at which rate, and how you know. You write the analysis as
code, so the next measurement (on the next machine, or after the next optimization) is
analyzed the same way.

**Time.** 4 hours, half of it measuring.

**Starter.** `starter/bottleneck.py` reads only the first stage of the utilization table,
counts the replay source's own work as a limit of the pipeline, ignores the data the source
dropped, and estimates a stage's capacity from the last point of the sweep alone.

**Acceptance** (`tests/test_bottleneck.py`, run by CTest as `ch11/e3_bottleneck/...`):
- A real `minidaq_latency` report parses into its offered rate, delivered and dropped
  words and five stages with their counters; the latency table and the end-to-end line are
  not stages; text that is not a report raises `ValueError`.
- At 50 MBq the busiest stage that can limit the pipeline is the pair stage, at 9.7%, and
  nothing is saturated.
- In the chapter's sweep (`measurements/ch11/bottleneck.txt`), the pair stage is saturated
  at 400 MBq and not at 300 MBq; drops mark it saturated even with a 99% busy limit.
- Fitted through the origin over the whole sweep, the pair stage is full at 69.82 M
  singles/s and the sort stage at 95.85 M; the first bottleneck is the pair stage.

**Then, by hand.** Run `measurements/ch11/bottleneck.py` on your machine with nothing else
running, feed its reports to your code, and write a one-page measurement report in
`NOTES.md`: the question, the setup (machine, build, data, what is not measured), the
results with their spread between repeats, the first bottleneck and its capacity, what
saturates next, and what you would change first. Chapter 3's report is the template.

**Hints.** A busy percentage is a share of wall time; a pipeline stage that is busy 100%
of the time is the slowest stage, and every stage upstream of it starts to stall or the
source starts to drop. Why does the fit go through the origin, and why is one point not
enough?
