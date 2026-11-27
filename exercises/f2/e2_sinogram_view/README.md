# Exercise F2.2 (M): A sinogram view in the shape of std::mdspan

**Goal.** A sinogram is a two-dimensional array (angles by radial bins) stored in one flat
buffer. Write `SinogramView<T>`, a non-owning view of such a buffer with C++23's
multidimensional subscript `v[angle, bin]`, a bounds-checked `at`, and `row(angle)` as a
`std::span`. It is what `std::mdspan` with `std::layout_right` does; your library may not have
`<mdspan>` yet, and if it does, a test compares the two.

**Time.** 60 minutes.

**Acceptance tests** (`tests/test_sinogram_view.cpp`): extents; row-major layout; writes reach
the buffer; `row` is a span into the buffer; `at` throws `std::out_of_range`; a buffer of the
wrong size is rejected; a view of `const float` works on `const` data; and, where
`__cpp_lib_mdspan` is defined, the view agrees with `std::mdspan` element by element.

**Hint.** `operator[]` with two parameters is valid from C++23 (GCC 12, Clang 15). In a test
macro, wrap `v[a, b]` in parentheses: the macro would split it at the comma.
