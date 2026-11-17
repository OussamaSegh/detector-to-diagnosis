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

Its first version mapped a rename to the new name only in the commit that made it, so that commit
counted for the current file, but the commits before it still counted under the old name, which
is no longer a file and drops out of the ranking: a file renamed after ten commits started again
at one. Writing this exercise found it; it is MDQ-PR-083, fixed the way this solution does it,
with a test of a file renamed twice. On MiniDAQ the 14 renames in the history are of figures,
measurements and one tool, none under `minidaq/`, so no survey the book reports was affected.
The survey has no threshold for large commits, which section 1 suggests is right for this
history, and takes its window through `git log --since`.

## 3. The threshold

No. 20 is about a tenth of the files under `minidaq/`, and on MiniDAQ every commit above it was a
real interface change; a project of 5,000 files has ordinary changes of 50. Better signals of a
mechanical change: the lines changed per file (a reformat changes many lines in every file, a
rename none), a trailer in the commit message (`Mass-change: format`), or an explicit list of
commits to skip, like the `.git-blame-ignore-revs` file that `git blame --ignore-revs-file`
already reads. A project that records its mechanical commits there can give the survey the same
list, and the survey then removes exactly those, not every large commit.
