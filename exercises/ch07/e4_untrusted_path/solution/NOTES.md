# Exercise 7.4: notes on the solution

The order of operations is the design. The starter checked nothing; a version
that first calls `stat(path)` and then opens `path` checks one file and reads
another if the name is changed in between (a time-of-check to time-of-use race,
CERT FIO45-C). The solution opens first and asks every later question of the
descriptor, which keeps referring to the same file whatever happens to the name.

- `O_NOFOLLOW` makes `open` fail with `ELOOP` if the last component is a
  symbolic link. It does not cover the directories above it; on Linux 5.6 and
  later `openat2` with `RESOLVE_NO_SYMLINKS` does. Whether that matters depends
  on who can write those directories: on a scanner PC where only the service
  account can, the last component is the realistic attack.
- `O_NONBLOCK` makes `open` of a FIFO return at once instead of waiting for a
  writer; `fstat` then shows it is not a regular file. The starter blocked
  forever in `std::ifstream`'s constructor.
- The size is checked twice: by `fstat` before reading (cheap, rejects
  `/dev/zero`'s neighbors and big files) and by reading at most `max_bytes + 1`
  (the file can grow between the two).
- A world-writable file is rejected because anyone on the machine could have
  written its content. A stricter policy also checks the owner (`st_uid`); that
  needs to know which account is trusted, which is a deployment decision.
- `Fd` closes the descriptor on every return path. Ten returns and one
  `close`: without RAII one of them would leak.
