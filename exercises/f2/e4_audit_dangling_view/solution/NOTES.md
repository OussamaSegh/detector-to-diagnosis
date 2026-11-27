# Notes on the solution (and the review)

**Finding 1: `peak_region` views a temporary.** `counts()` returns a new `std::vector` by value.
The span is built over that temporary, which is destroyed at the end of the `return` statement,
so the caller receives a span into freed memory. The function also copies the whole vector to do
it, the opposite of the specification. Fix: view the member `counts_`.

**Finding 2: `label` views a temporary.** `material_ + " spectrum"` builds a new `std::string`
that dies at the end of the `return` statement; the `string_view` outlives it. Nothing to view
exists before the call, so the function must return the string itself. Returning a `std::string`
costs one allocation (or none, for a short string with the small string optimization).

**Finding 3: no bounds check.** `subspan(first, last - first)` with `last < first` wraps to a
huge count, and `last > size()` is undefined behavior. A function that takes indices from its
caller checks them, or documents and asserts the precondition.

**Finding 4: the claims.** "No warnings" depends on the compiler: GCC 13 says nothing about either
function at `-Wall -Wextra`; Clang 18 warns about the `string_view` ("returning address of local temporary object") but not about
the span. "The example plot shows the right title" is what undefined behavior often looks like:
the freed bytes had not been reused yet.

**The rule.** A function may return a view only of something that outlives the call: a member
(valid while the object lives and is not modified), a parameter the caller owns, or static data.
Never of a local or a temporary.
