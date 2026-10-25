# Exercise 20.2: notes on the solution

**Three differences.** Built twice, the starter differs in three places: the date and time in
the build information, the absolute path of `main.cpp` in the log line (`__FILE__` is the path
the compiler was given, and CMake gives absolute paths), and the paths in the debug information
(the compilation directory and each source and header file). The solution takes the version from
the project instead of the clock and maps both the source and the build directory to relative
paths with `-ffile-prefix-map`, which covers `__FILE__` and the debug information at once.

**`SOURCE_DATE_EPOCH` instead?** It would make the date reproducible, but it answers a question
nobody asks: the date of a build says nothing that the commit does not say better, and a program
that prints a build date invites the belief that two builds of one commit can differ. MiniDAQ's
release package records the commit and its time in `BUILDINFO.json`, set from the commit
(`SOURCE_DATE_EPOCH` is used there, by the packaging, for the archive's file times).

**The debugger.** The debug information now names `src/main.cpp`, relative to an unknown
directory. Start gdb from the top of a checkout of the same commit, or tell it where that is
with `directory /path/to/checkout` (or `set substitute-path`); Chapter 21 does this with
MiniDAQ's split debug files.
