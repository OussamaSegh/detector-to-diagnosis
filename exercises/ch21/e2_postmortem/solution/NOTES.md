# Exercise 21.2: notes on the solution

**What the core said.** With the starter built at `-O0` with GCC 13.3, as the `debug` preset builds
it, `bt -5` shows the outermost frames, `main` and `parse_groups` under a `Parser::group` that calls
itself, and `p depth` in frame 0 gives about 130,000 (130,850 in the measurement, from a small
program that calls the parser directly). The stack pointers of frame 0 and frame 1000 differ by
59,856 bytes over 998 levels: 60 to 64 bytes a level, so the 8 MiB stack of the main thread
(`ulimit -s` says 8192) ends after 8,388,608 / 64 = 131,072 levels. That is the whole diagnosis:
the text decides the depth of the recursion, and nothing bounds it.

**The fix.** One check, before the recursion: a group deeper than `max_depth` is an error with
its byte offset. It is the shape of MDQ-PR-001 again (an input that controls a resource the code
never bounded), and the review checklist asks for it in section 2.4: input from outside is
checked before use.

**Why 1 MiB crashes the debug build and not the release build.** At `-O2` GCC inlines the
recursion into itself, so one real call covers several levels: in the same measurement, 1000
frames took 5,328 bytes for 992 levels, about 5.4 bytes a level, and the crash came at a depth
of 1,570,178. A capture of 1,048,576 braces needs about 5.6 MB at `-O2` and fits; at `-O0` it
needs about 60 MiB and does not. The release build would have died on a slightly larger file, or with
a smaller stack (a thread of 1 MiB, or the 64 KiB alternate stack of a signal handler).

**What it says about "cannot reproduce".** Reproduce with the build that crashed: the same
optimization, the same stack size, the same thread. A crash that depends on the build is still
a defect in the code; the build only moved the threshold. That is why the crash report names
the build ID and why `tools/postmortem.sh` refuses a program whose build ID differs from the
core's.
