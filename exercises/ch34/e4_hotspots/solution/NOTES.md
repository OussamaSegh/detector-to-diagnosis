# Exercise 34.4: notes on the solution

## 1. MiniDAQ's own history

On `minidaq/` at the time of writing (110 commits, 212 files), a threshold of 20 files leaves out
7 commits, of 24 to 37 files each. The top file stays `acquisition_service.cpp` (667 code lines),
but with 13 commits instead of 20; the tests of the control protocol drop out of the top five, and
`minidaq_sim.cpp` comes in. With a threshold of 40 nothing is left out: the largest commit touches
37 files.

Then read what was left out, which is the point of listing it. None of the 7 is a reformat: they
are Chapter 6 (the architecture and the control API), Chapter 7 (safe C++), the register map and
hardware port (CR-0008), the flight recorder (CR-0007), the watchdog and A/B updates (CR-0011),
time markers (CR-0026) and control API 3.0 (CR-0030). Each is a change of an interface that every
stage had to follow, and the service did take part in it. On this history the threshold removes
real work, and the ranking without it is the more honest one. A threshold is a hypothesis about
what large commits are; the list of commits it removed is how you test it.

## 2. tools/survey.py

`churn` maps a rename to its new name in the commit that made it, so that commit counts for the
current file, but the commits before it still count under the old name, which is no longer a
file and drops out of the ranking. A file renamed after ten commits starts again at one. It has
no threshold for mass commits and takes a window through `git log --since`. On MiniDAQ the 14
renames in the history are of figures, measurements and one tool, none of a product file, so the
survey's numbers are not affected today; they would be after the first rename of a source file.
That is a limitation worth a line in the tool's validation record (TL-43), and a problem report
if a rename of a product file is planned.

## 3. The threshold

No. 20 is about a tenth of the files under `minidaq/`, and on MiniDAQ every commit above it was a
real interface change; a project of 5,000 files has ordinary changes of 50. Better signals of a
mechanical change: the lines changed per file (a reformat changes many lines in every file, a
rename none), a trailer in the commit message (`Mass-change: format`), or an explicit list of
commits to skip, like the `.git-blame-ignore-revs` file that `git blame --ignore-revs-file`
already reads. A project that records its mechanical commits there can give the survey the same
list, and the survey then removes exactly those, not every large commit.
