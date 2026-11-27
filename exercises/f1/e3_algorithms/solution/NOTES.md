# Notes on the solution

**A name instead of a loop.** `count_if` says "count the ones that match"; a `for` loop with a
counter says the same thing in four lines, any of which can hold an off-by-one or a wrong
comparison. The algorithm's name is the reviewer's first check.

**Empty input.** `max_element` of an empty range returns `end()`, which must not be dereferenced,
and a mean of nothing divides by zero. Both functions return `std::optional` and test for empty
first. The tests check the empty case of every function.

**A total order.** Sorting by time alone leaves singles with the same time in an unspecified order
(`std::sort` is not stable), so two runs of the same data could differ. Adding the crystal as a
tie-breaker makes the order total, and the output reproducible. Chapter 3 makes the same choice for
the pipeline's sort stage.

**`erase_if`.** C++20's `std::erase_if(vector, pred)` is the erase-remove idiom in one call. It
keeps the order of the remaining elements and runs in linear time.

**When a loop is clearer.** The histogram `counts_per_crystal` is a loop: `++counts[x.crystal]` is
already one line, and `std::for_each` would only add a lambda around it. Prefer the algorithm when
it names the operation; prefer the loop when the algorithm only hides it.
