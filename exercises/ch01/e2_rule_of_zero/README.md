# Exercise 1.2 (M): From raw pointers to the Rule of 0

**Goal.** `EventBuffer` holds a fixed-capacity array of `Single` records. The starter is
"legacy" code: it owns a raw `new[]` array, has a destructor, and relies on the
compiler-generated copy operations. Copying it causes a double free. Refactor it so the
class declares **none** of the five special members (Rule of 0), owns its storage
through `std::unique_ptr<Single[]>` (or `std::vector`), exposes its contents as
`std::span`, and has the copy semantics the tests ask for.

**Time.** 45 to 60 minutes.

**Acceptance tests** (`tests/test_event_buffer.cpp`):
- Copies are deep (changing the copy leaves the original intact). Run it under the
  `asan-ubsan` preset: the starter dies with `attempting double-free`.
- Moves are `noexcept` and leave the source empty but valid.
- `view()` returns a `std::span<const Single>` over exactly `size()` elements.
- `push()` returns `false` (and changes nothing) when the buffer is full.

**Hint.** `std::unique_ptr<T[]>` is move-only. To keep copies you can write a small
copyable owner (a "value_ptr"), or use `std::vector<Single>` with `reserve()`. Both are
in `solution/`; NOTES.md compares them.
