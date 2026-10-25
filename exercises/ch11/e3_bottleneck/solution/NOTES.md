# Exercise 11.3: measurement report, first software bottleneck

**Question.** As the activity of the NEMA-style source rises, which MiniDAQ stage saturates
first, at what singles rate, and what saturates next?

**Setup.** `measurements/ch11/bottleneck.py` on the book's VM (Intel Xeon at 2.30 GHz,
4 vCPU, GCC 13.3, Release -O2), nothing else running. For each activity, up to 4 M decays (at
most 50 ms) of the NEMA-style line source are recorded with `minidaq_sim` (no dead time, seed 3) and replayed
through the pipeline in real time with `minidaq_latency` for 3 s, twice. Default sorter:
4 ns fixed window, 435 to 585 keV, kill all, delayed window at 100 ns. The sink discards
the coincidences: the disk is not measured.

**Results.** Busy percentages grow linearly with the rate in every stage but the source,
whose number is the replay source's own work and levels off at about 65% (clock reads,
copies; a real source is a network card). Repeats agree within 3 percentage points in the
stages that can limit the pipeline.

| Stage | Busy at 16.7 M singles/s | Busy at 66.8 M singles/s | Fitted capacity |
|---|---:|---:|---:|
| decode | 6.7 to 6.8% | 19.0 to 19.8% | 328 M singles/s |
| sort | 19.1 to 19.6% | 68.1 to 69.0% | 95.8 M singles/s |
| pair | 22.9 to 23.0% | 97.3 to 97.5% | 69.8 M singles/s |

At 400 MBq (66.8 M singles/s) the pair stage is 97% busy, the source drops 0.06 to 0.17% of
the words, and the end-to-end p99 latency, 0.8 to 2.3 ms up to 200 MBq, is 6.5 to 12 ms:
the pipeline is at its limit.

**Conclusion.** The first software bottleneck is the pair stage (the coincidence sorter's
window search and multiples handling), at about 70 M singles/s on this machine, or about
420 MBq of the NEMA-style source. The sort stage is next, at about 96 M singles/s.

**What it does not say.** The five stages ran as five threads on 4 vCPUs with nothing else running;
with other work on the machine the capacities are lower. The rate of singles that pass
the energy window, which is what the pair stage works on, depends on the phantom and the
dead time; a recording with pile-up would move it. The disk and the network are not in
this measurement: a single Gigabit link (14.8 M singles/s, Chapter 9) saturates at about
89 MBq, well before the software.

**What to change first.** Nothing, for this scanner: the front end's dead time puts the
NECR peak near 100 MBq (`countrate.txt`), and the software has about four times that in
reserve. If a target needs more, split the pair stage by time slices (Exercise 10.3) before
optimizing it, since it scales across cores and the window search does not get much faster.
