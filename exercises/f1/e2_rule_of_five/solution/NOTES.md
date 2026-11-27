# Notes on the solution

**The rule of three, then five.** A class that needs a user-written destructor manages a resource,
and the copies the compiler writes for it copy the handle (the pointer), not the resource. So it
needs its own copy operations too (the rule of three). Since C++11 it also wants moves, or every
"move" falls back to a copy (the rule of five).

**Copy and swap.** The copy assignment builds a full copy first and only then swaps it in. If
`new` throws, `*this` is untouched: the strong exception guarantee, with no special code. The cost
is one extra allocation when the target was already large enough; a hand-written assignment could
reuse the old array, at the price of more code to get right.

**Counting is the test.** A test of a resource-owning class asserts the resource counts, not only
the values: "a copy allocates once", "a move allocates nothing", "nothing is left at the end".
Values can be right while the resource leaks.

**The vector test.** `std::vector` moves its elements on reallocation only when the move
constructor is `noexcept` (it uses `std::move_if_noexcept` to keep its own strong guarantee).
Without `noexcept`, every growth copies every element, and the allocation count shows it.

**Rule of zero.** Five functions are five places to forget a member. Production code (and Exercise
1.2) gives the class members that already manage themselves, `std::vector<double>` or
`std::unique_ptr<double[]>`, and declares none of the five. Write the five once to see what they do;
then let the library write them.
