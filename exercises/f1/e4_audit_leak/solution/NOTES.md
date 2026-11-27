# Notes on the solution (and the review)

**Finding 1: a leak when the constructor throws.** `header_` is built first, then `new Index{0}`
throws. The object was never fully constructed, so its destructor never runs, and the `Header` it
allocated is lost. C++ destroys the members a constructor had *finished* building, but a raw
pointer member has no destructor that frees anything. Input: `RunLog{7, "x", 0}`.

**Finding 2: a double free on copy.** The class has a destructor but no copy operations, so the
compiler's copy copies the two pointers, and both objects delete them. Input: `RunLog b = a;`.

**Finding 3 (minor): the claim.** "The unit tests pass" was true and proved nothing: the tests the
assistant wrote never constructed a log with capacity 0 and never copied one. A review checks what
the tests exercise, not only that they pass.

**The fix.** Members by value (or `std::unique_ptr` if they must live on the heap). Each member
then owns its part, a throw half-way destroys the parts already built, and the compiler-written
copies are deep. The class declares none of the five special members: the rule of zero.

**How to say it in a review.** "Rejected: leaks the header when the index throws (input:
capacity 0), double free on copy. Use members by value; add tests for both inputs." Each finding
names an input that shows it, so the author can reproduce it without arguing.
