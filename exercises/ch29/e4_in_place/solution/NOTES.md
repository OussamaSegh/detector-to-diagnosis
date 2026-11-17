# Exercise 29.4: notes on the solution

**The three mistakes.**

- *A converted output is a lost output.* `forcecast` is right for an input: if the caller's array
  is not what the C++ reads, a converted copy is read instead, and the caller sees no difference.
  For an output it is wrong. A float32, Fortran-ordered or strided `out` was converted into a new
  float64 array, the starter added into that copy, and pybind11 dropped it when the call
  returned. The caller's array stayed zero, with no error. The solution converts nothing for
  `out`: it accepts a NumPy array that is already float64, C-contiguous and writeable, and refuses
  every other with what it must be. The C-contiguous rows of a larger array pass: they are memory
  the caller owns, and writing them is what the caller asked for.
- *An index is the caller's data too.* The starter wrote `out[50]` of 50 elements: the 8 bytes
  after the array, which belong to some other object of the interpreter. Nothing failed at the
  call; whatever used those bytes later had a wrong number, or the allocator crashed much later in
  unrelated code. The solution checks every index before the first write, so a refused call
  changes nothing, and names the position and the value.
- *The GIL was held for the whole loop.* No other Python thread ran for the length of the call:
  a thread that writes the previous image, or answers a health check, waited. The solution
  releases it after the last check, the last exception and the last call into Python.

**float32** (Then, by hand, 1). A zero array, as before the call. The sums had gone into the
temporary float64 copy.

**Index 50** (2). The value was added to the double after the array's end, inside the heap. A
crash at the call would have shown the mistake; corrupted memory shows it later, somewhere else,
and only sometimes.

**Another thread** (3). Each `+=` reads and writes the caller's memory without a lock, so a
concurrent change by another thread is a data race: the caller finds some of the sums, some of
the other thread's values, in an order that changes from run to run. The C++ cannot prevent it:
releasing the GIL is a promise that the C++ touches no Python object, not that the caller's
arrays are frozen. The contract belongs in the docstring: do not change `out` until the call
returns, as with any function that writes into an argument.
