# Exercise 32.4 (M): A dependency pinned by its bytes

**Goal.** Fetch a third-party library the way MiniDAQ's `cmake/Dependencies.cmake` does: pinned by
the SHA-256 of its archive, so that different bytes at the same location fail the configure, and
with its headers outside the project's warnings, so that `-Werror` applies to the project's own
code and not to code that is reviewed as SOUP instead.

**Time.** 60 minutes.

**Starter.** `starter/CMakeLists.txt` fetches tinylib 1.0 with `FetchContent` from the archive
named by `TINY_URL`, with no hash, and builds `usetiny` with `-Wall -Wextra -Wconversion -Werror`.
Write the archive with `python3 tests/make_archive.py` (the same bytes on every machine) and
configure with `-DTINY_URL=$PWD/tests/tinylib-1.0.tar`. The build fails in tinylib's header.

**Acceptance** (`tests/test_pin.py`, run by `ctest --test-dir build/debug -R ch32/e4`), all
offline:
- With the archive, the project configures, builds with the same warning options and
  `-Werror`, and prints `scaled 10`.
- With a tampered archive of the same name (one line of the header changed), the configure fails
  and says the hash does not match.
- A narrowing conversion added to `main.cpp` still fails the build: the warnings were not turned
  off for the project.

**Then, by hand.**
1. Which line did the starter accept from the tampered archive, and what would a `GIT_TAG v1.0`
   have pinned instead of a hash? Who can move a tag?
2. Find the include option that carries tinylib's directory in `build.ninja` (or the compile
   commands), before and after your change. What does it switch off, and what replaces the
   warnings for that code in MiniDAQ's process?
3. You computed the hash from an archive you were given. If that archive had already been
   replaced, what did the hash pin? What would you check it against before recording it in the
   SOUP list?

**Hints.** `cmake -E sha256sum tests/tinylib-1.0.tar`. `FetchContent_Declare` takes `URL_HASH
SHA256=...` and, since CMake 3.25, `SYSTEM`. Silencing the warning with a pragma or by dropping
`-Werror` does not pass the third test.
