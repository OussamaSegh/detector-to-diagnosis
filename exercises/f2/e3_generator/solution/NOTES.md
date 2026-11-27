# Notes on the solution

**What a generator buys.** The caller's loop and the decoder look like two ordinary loops, but
they take turns: each `++` of the caller's iterator resumes the coroutine until its next
`co_yield`. Nothing is buffered, so memory use is one single whatever the file size, and a caller
who stops early pays only for what it read.

**Composition.** `in_window` takes a `Generator<Single>` by value (it owns it) and is itself a
generator. A chain of generators is a lazy pipeline with no intermediate containers, the same
idea as a chain of views, written as plain loops.

**Exceptions.** An exception thrown inside the coroutine is caught by `unhandled_exception`,
stored, and rethrown by `Generator` at the caller's `++`. The singles before it were already
delivered; what the caller does then is its decision.

**The cost.** Each generator allocates its frame once (the compiler may elide it when it can
prove the lifetime), and each resume is an indirect call. That is fine per file or per batch and
too much per single in MiniDAQ's hot path, which hands batches between threads (Chapter 3).
`std::generator` (C++23, GCC 14) replaces `generator.hpp` with the same code shape.
