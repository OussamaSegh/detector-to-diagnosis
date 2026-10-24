# Notes on the solution

**What was wrong.** The legacy class had a destructor but used the implicit copy
operations. That violates the Rule of 3/5: a class that needs a user-written destructor
almost always needs user-written copy and move operations too. Copying duplicated the
pointer and both copies called `delete[]` on it.

**Two correct fixes.**

1. *Rule of 5*: write the copy constructor, copy assignment (copy-and-swap), move
   constructor and move assignment by hand. Correct, but five functions to review and
   keep in sync, and the next person who adds a member will forget one of them.
2. *Rule of 0*: give the class members that already manage themselves, and declare no
   special members at all. This is the C++ Core Guidelines default (C.20).

The solution uses option 2. The `FixedStorage` member is the one place that knows how to
copy (preserving capacity, which `std::vector`'s copy constructor does not promise) and
how to leave a moved-from object empty. `EventBuffer` itself declares no special
members.

**Why not `std::unique_ptr<Single[]>`?** It is the right owner for a move-only buffer
(and in MiniDAQ most event buffers *should* be move-only: copying a 64 MiB buffer by
accident on the hot path is a performance bug). If you choose it, delete the copy
operations explicitly or write a `clone()` function; the tests here ask for copies only
to practise the semantics.

**noexcept moves matter.** `std::vector<EventBuffer>` only moves elements during
reallocation if the move constructor is `noexcept`; otherwise it copies them.

**Spans.** `view()` returns `std::span<const Single>`, a non-owning view. It dangles if
the buffer is destroyed or reallocated, which is why `push()` never reallocates.
