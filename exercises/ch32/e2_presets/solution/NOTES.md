# Exercise 32.2: notes

The starter's `asan` configuration fails to link: the objects call AddressSanitizer's runtime
(`__asan_report_load4` and the rest), and only `-fsanitize=address` on the link line brings that
runtime in. Without build, test and workflow presets, `cmake --workflow` has nothing to run.

A workflow preset names a configure, a build and a test preset, in that order, and runs them as
one command. Its value is that the command is the whole gate of that configuration: what CI runs
for `asan` is what a developer runs, so "it passed on my machine" means the same thing.

By hand:

1. The loop's last step reads `copy[n]`; both tests reach it (`sums` with width 3 over five
   counts, and `edges` with one count). Change `i <= n` to `i < n` and drop the `if`.
2. The value read is added to a sum that is then dropped, so no output changes. The read itself
   is undefined behavior; in the `dev` build it reads whatever lies after the array in the heap,
   which is mapped memory, so nothing crashes.
3. `CMakeUserPresets.json` holds one developer's settings (a local compiler, a cache path). CMake
   reads it after `CMakePresets.json`, and it may inherit from the project's presets; the project's
   file is shared and reviewed, the user's file is not.
