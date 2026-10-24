# Exercise 7.4 (M): Read a file whose name you did not choose

**Goal.** MiniDAQ's `configure` command accepts an `rt_profile` path from a control
client and reads it (`read_small_file` in `acquisition_service.cpp`). Write the
general version: `read_untrusted_file(path, max_bytes)` that reads a file named by
someone else without blocking, without reading forever, and without following a
symbolic link planted in its place.

**Time.** 1.5 hours.

**Acceptance** (`tests/test_untrusted_file.cpp`):
- a small regular file is read; a file of exactly `max_bytes` is accepted, one byte
  more is not;
- `/dev/zero` and a directory are rejected;
- a symbolic link is rejected with a message that says so;
- a file writable by every user is rejected;
- a FIFO without a writer is rejected, and the call returns within 2 seconds;
- every error message names the path.

**Hints.** Which `open` flags stop it from following a link and from waiting for a
FIFO's writer? Why must the checks use `fstat` on the descriptor rather than `stat`
on the name? `O_NOFOLLOW` covers only the last component of the path: what would you
need for the directories above it (look up `openat2` and `RESOLVE_NO_SYMLINKS`)?
