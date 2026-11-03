# Exercise 29.1: notes on the solution

**The three mistakes.**

- *The layout is the caller's.* NumPy arrays have strides, and only a C-contiguous array has its
  rows one after the other in memory. `py::array_t<double>` accepts a Fortran-ordered or strided
  array as it is, and `data()[i * cols + j]` then reads the wrong elements. The solution asks for
  `c_style | forcecast`: pybind11 converts every other layout or dtype into a new C-contiguous
  float64 array before the function runs, and the function may index it as rows. (`unchecked<2>()`
  would also index a strided array correctly; with `c_style` it is a plain array either way.)
- *The shape is the caller's too.* The starter called `shape(1)` on a one-dimensional array, and
  pybind11 raised `IndexError: invalid axis`, an error about the C++ code, not about the call. A
  `factors` that was too short would have been read past its end: no error, just numbers from
  whatever memory followed. The solution checks the dimensions and lengths first and raises
  `ValueError` with both shapes.
- *In place is a change to the caller's data.* The starter scaled `a` and returned it. For a
  float64 C-ordered array that is the caller's own array, so a call meant to compute something
  changed its input. The solution allocates the result.

**The Fortran array** (Then, by hand, 1). The starter read the Fortran array's memory as if it
were rows: element (i, j) of its loop was element (j', i') of the array for some other indices,
so it returned a scrambled array of the right size. It did not crash because it stayed inside
the array's memory; the strided view did the same within the larger array it came from. A wrong
answer of the right size is the dangerous kind: nothing at the boundary notices it.

**int32** (2). An int32 array is not float64, so `forcecast` made a new float64 copy. The starter
scaled the copy in place and returned it, so the caller's int32 array was left alone and the
result was right. A float64 array needs no conversion, so it was passed as it is, and scaled in
place. The same code changed some callers' data and not others', depending on a dtype: the
reason to never write into an argument that the function did not promise to change.

**The GIL** (3). With the GIL released the C++ code may not create, change or destroy any Python
object, raise a Python exception or call back into Python: other Python threads run meanwhile.
It may read and write the memory of arrays it holds references to. If another Python thread
writes the same array during the call, the C++ code reads a mixture of old and new values; the
array stays alive (the call holds a reference), so there is no crash, but there is a data race.
`recon_cpp` avoids the question for its inputs whenever `forcecast` copies them, and otherwise
documents that the caller must not change an array while a projection of it is running.
