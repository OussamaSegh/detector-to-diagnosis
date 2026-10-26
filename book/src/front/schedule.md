# How to use this book: the 10-week schedule {.unnumbered #schedule}

The book is written for about ten weeks of preparation before a first day as DAQ lead. Each week
pairs a deep C++ chapter with a domain chapter and a lighter regulatory chapter, so that hard coding
days alternate with reading evenings. The chapters refer to this table for their week; it is the
only place where the schedule is stated.

Every chapter starts with an estimate of its reading time, its exercises and its MiniDAQ
milestone. The two columns of hours add those estimates up (midpoints of the ranges):

- **Core** hours are the reading and the milestone: what you need to follow the next chapters and to
  keep MiniDAQ complete.
- **All** hours add every exercise, the extras included.

| Week | Chapters | MiniDAQ by Sunday | Core, h | All, h |
|---|------|-----------------------|---|---|
| 1 | 1, 2, 8 | Core types, packed format, detector simulator | 17 | 35 |
| 2 | 3, 9, 13 | Threaded pipeline, UDP readout with loss counters | 20 | 44 |
| 3 | 4, 5, 10 (first half) | Real-time profile, benchmarks, first sorter | 16 | 45 |
| 4 | 10 (second half), 11, 14 | Validated sorter, count-rate curves, SRS and SOUP list | 19 | 45 |
| 5 | 6, 12, 15 | Control API and state machine, list-mode writer, risk file | 22 | 57 |
| 6 | 7, 16, 17, 18 | Static analysis, fuzzing, SBOM, design file, threat model, unit tests | 20+ | 42+ |
| 7 | 19 to 23 | Replay and soak tests, CI evidence, hardware layer, tuned receiver | | |
| 8 | 26, 27, 28, 31 | Calibration, Python analysis package, 2D OSEM | | |
| 9 | 29, 30, 32 (skim 24, 25) | C++ OSEM with bindings, image quality report, build presets | | |
| 10 | 33, 34 | MiniDAQ 1.0, walkthrough, a 30-60-90 day plan | | |

Week 6's hours do not yet include Chapter 18, and those of weeks 7 to 10 are filled in when
those chapters are written (this edition contains Parts I to III).

The weeks interleave the Parts, but MiniDAQ grows in chapter order: each milestone starts from
the previous chapter's tag in the companion repository (`ch07` for Chapter 8's milestone, for
example). In a week that mixes Parts, start each milestone from its tag rather than from your
own code of the week before, and merge your own work into it when you want to keep it.

**Be honest with yourself about the workload.** The core path of Chapters 1 to 17 is about
110 hours, close to 20 hours a week for the first six weeks. Everything in those chapters is
about 290 hours, more than ten weeks of evenings and weekends can hold. So:

1. Follow the core path every week: read the chapter, do the milestone, and answer the
   Check yourself questions from memory on Sunday.
2. Add exercises in the order the chapter lists them. Several chapters say which ones to keep
   when time is short; the ones marked (H) and the extras can wait.
3. Protect Parts I and II and Chapter 14 (IEC 62304) when you fall behind: they are the core
   of the work: the DAQ, its C++ and the regulated life cycle. Chapters 24, 25, 29
   and 30 can be skimmed and finished later.
4. Keep the exercises you skip on a list. They make good material for the first months in the
   job, when the real system gives you a reason to do them.

A week of the core path is about 19 hours: four evenings of 2.5 hours for reading, a Saturday
of about 8 hours for the milestone, and an hour on Sunday for the Check yourself questions and
a short log of what to revisit. Each exercise you add costs the time its README states; the
lighter weeks 9 and 10 are the place to catch up.
