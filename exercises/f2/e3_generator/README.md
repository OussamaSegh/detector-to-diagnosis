# Exercise F2.3 (M): A generator over a list-mode file

**Goal.** `singles_in` reads 16-byte records from a buffer and yields them as `Single`s;
`in_window` filters a stream of singles by energy. The starter is correct but eager: it decodes
everything into a vector before the caller sees anything. Rewrite both as coroutines that
`co_yield` one single at a time, so that work happens only when the caller asks for the next
single. `generator.hpp` provides `Generator<T>`, the shape of C++23's `std::generator<T>`, for a
library that does not have it yet.

**Time.** 60 minutes.

**Acceptance tests** (`tests/test_listmode.cpp`): every record in order; nothing decoded before
the first request and three records decoded for three singles; a truncated last record ignored;
a filtered stream that pulls only as many records as it needs; an exception thrown in the
middle reaches the caller after the singles before it.

**Hint.** A function whose body contains `co_yield` is a coroutine: its local variables live in
a frame on the heap, and the function pauses at each `co_yield` until the caller's loop asks
for the next value. You do not need to touch `generator.hpp`.
