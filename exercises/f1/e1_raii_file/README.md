# Exercise F1.1 (E): A RAII file handle

**Goal.** `File` wraps a C `std::FILE*`. The starter works only if every caller calls `close()`
exactly once on every path, including the path an exception takes. Make `File` the owner of its
`FILE*`: the destructor closes it, copies are impossible, and a move transfers ownership and leaves
the source empty. Move assignment closes the file the target held before.

**Time.** 45 minutes.

**Acceptance tests** (`tests/test_file.cpp`):
- `File` is move-only, and its moves are `noexcept`.
- A failed open returns no `File` and opens nothing.
- The file is closed, and its content is on disk, when the `File` goes out of scope, also when an
  exception leaves the scope.
- A moved-from `File` is empty; move assignment closes the old file, and self-move is harmless.
- `close()` may be called twice.

**Hint.** Write the destructor first, then delete the copy operations, then write the moves with
`std::exchange`. `File::open_count()` is how the tests see a leak.
