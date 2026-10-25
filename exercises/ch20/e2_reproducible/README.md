# Exercise 20.2 (M): Make a build reproducible

**Goal.** Make a small program's build give the same bytes from two checkouts in different
directories, built at different times, while it keeps its debug information and still says
what it is. Each source of difference is one you will meet in MiniDAQ's shipped build.

**Time.** 60 minutes.

**Starter.** `starter/`: a CMake project with two sources. The program prints its build
information and a log line that names its source file.

**Tasks.**
1. Build the starter twice yourself, from copies in two directories, and compare the programs
   (`cmp`, then `strings` and `readelf --debug-dump=info` to see where they differ).
2. Remove every difference: the clock, the source path in the log line, the paths in the debug
   information. Keep the debug information and the version in the output.

**Acceptance** (`ch20/e2_reproducible/<variant>/unittest`): the test copies the project to two
directories, builds each (`RelWithDebInfo`) in a different second of the clock, and checks that
the program says `reproducible-demo 1.0`, logs `src/main.cpp:<line>: starting`, contains no build
directory, keeps `.debug_info`, and that the two programs are identical.

Then answer in `NOTES.md`: GCC honors `SOURCE_DATE_EPOCH` for `__DATE__` and `__TIME__`. Why did
you not use that instead of removing them, and what does a debugger need now to find the sources?
