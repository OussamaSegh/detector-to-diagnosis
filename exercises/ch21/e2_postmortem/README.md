# Exercise 21.2 (E): A crash from the field, from the core dump

**Goal.** Find the cause of a crash from its core dump, not from a guess: run the failing input,
open the core with gdb, read the stack, and fix the defect so that the input is an error, not a
crash. A site sent a configuration file with its crash report; the group parser of the site
configuration tool died on it with SIGSEGV.

**Time.** 30 minutes.

**Starter.** `starter/group_parser.cpp`, a recursive parser of nested braces. The format allows
`max_depth` (64) levels.

**Tasks.**
1. Build the starter's tests and run the last one alone with core dumps on
   (`ulimit -c unlimited`, then the test program with
   `--gtest_filter=GroupParser.TheFieldCaptureIsAnErrorNotACrash`). Find the core: `sysctl
   kernel.core_pattern` says where the kernel writes it.
2. Open it: `gdb PROGRAM CORE`, then `bt -frame-info short-location 5`, `bt -5`, `frame 0`,
   `info frame` and `p depth`. How deep was the recursion, and how many bytes of stack did each
   level take (compare `$sp` of two frames far apart)?
3. Fix the parser: reject a group nested deeper than `max_depth` with an error that names the
   byte offset, before the recursion goes deeper.

**Acceptance** (`ch21/e2_postmortem/<variant>/...`): the first three tests pass on the starter
already; the fourth wants the error `groups nested deeper than 64 at byte 64` for 65 levels; the
fifth runs the field capture (16,777,216 opening braces) and wants that error instead of a crash.

Then answer in `NOTES.md`: a capture of 1 MiB of braces crashes the debug build and not the
release build. Why, and what does that tell you about a crash report that says "cannot
reproduce"?
