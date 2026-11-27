# Notes on the solution

**A view is a pointer and a shape.** The class holds a `std::span<T>` and two extents and owns
nothing, like `std::string_view` for text and `std::mdspan` for any number of dimensions. It is
cheap to copy and pass by value, and it dangles if the buffer dies first.

**Layout.** Row-major (`std::layout_right`) puts the bins of one angle next to each other, so
the inner loop over bins walks memory in order and `row(angle)` is a contiguous span. A
projector that loops over angles inside bins would want the other layout (`std::layout_left`);
`std::mdspan` makes the layout a template parameter for that reason.

**`const` is in `T`.** `SinogramView<const float>` reads only. The member functions are `const`
because a view's constness is about the view (which buffer it looks at), not about the elements,
the same rule as `std::span`.

**Checked and unchecked access.** `operator[]` does no check, for the inner loops; `at` checks,
for indices that come from outside. Building the debug preset with `_GLIBCXX_ASSERTIONS`
(Chapter 7) adds a check to `std::span::operator[]` too.

**Why not `std::mdspan`?** Use it where the compiler has it. In libstdc++ it arrived after GCC 14,
so a test guarded by `__cpp_lib_mdspan` compares the two where it can.
