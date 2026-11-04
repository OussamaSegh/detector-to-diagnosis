# Exercise 31.3: notes on the solution

Measured on the book's reference machine (x86_64, 4 CPUs, Python 3.13, NumPy 2.5.3, Numba
0.68.1); the full table is `measurements/ch31/histogram-speed.txt`.

## 1. The starter's first bin

The starter computes `(dt - lo) / bin` with C++'s `/`, which truncates toward zero: for
`lo = -2000` and `bin = 20`, every time from -2019 to -2001 gives `(-19..-1) / 20 = 0` and lands in
the first bin. Those entries are outside. Python's `//` and NumPy's `floor_divide` floor:
`-1 // 20 = -1`. The edge test sees it as `counts[0, 0] == 3` instead of 1: `lo`, `lo - 1` and
`lo - bin + 1` all counted in the first bin. On a timing peak centered near zero with
`lo = -2000`, very few entries fall there, so the reference test on 200,000 random entries may
pass while the rule is wrong: the edges need their own test.

## 2. forcecast

`py::array_t<std::int32_t, py::array::c_style>` accepts an array that already is C-contiguous
int32, and asks NumPy to convert anything else with its "safe" casting rule. int64 to int32 is not
safe, so the conversion fails and pybind11 reports that no overload matches: a `TypeError` naming
the signature. `forcecast` asks NumPy to convert with the "unsafe" rule, which for an int64 value
beyond 32 bits keeps the low 32 bits: 2^32 + 5 becomes 5, silently.

For MDQ-L1 that is acceptable because the format bounds the values: `dt_ps` is a signed 32-bit
field and a crystal id a 15-bit one, so an array of either read from a file fits in 32 bits by
construction, and a signed difference with the delay removed stays within a few microseconds.
For values the format does not bound to 32 bits (a time in picoseconds since the start of a run,
which passes 2^31 after 2.1 ms), forcecast to int32 would be a bug that no test of short runs
finds: take int64, or check the range before converting.

## 3. Is the C++ worth it?

On 10,000,000 entries: NumPy (`floor_divide` and one `bincount`) 169 ms, the C++ 39 ms, Numba
19 ms after a compilation of 0.26 s. A Python loop takes 165 ns per entry, 1.6 s for the same
entries. The test asks for 15 times the loop's speed on 50,000 entries, best of five runs each, in
an optimized build only: the first version asked for 20 times from one run each, and failed in
CI's debug build at 4.2 times (MDQ-PR-047). A correct solution reached 29 times at the slowest,
with four other processes busy, a margin of 94% over the criterion (CAPA-0001).

The C++ is four times faster than NumPy, and half as fast as Numba. NumPy is slower because it
makes four temporary arrays of 10 million entries (the int64 copy, the bins, the mask, the keys),
each a pass through memory; the loops make one pass. The C++ is slower than Numba mostly for
reasons outside the language: a 64-bit division that LLVM shortens to 32 bits when it can, and
the code GCC chose (the experiment is in the measurement file).

For this package the answer is no. The histogram of a whole run is 0.2 s in NumPy on 10 million
coincidences, against seconds to read them; a C++ module adds a compiler, the Python headers and a
build for each Python version to a package that is otherwise pure Python and installs anywhere.
The exercise is how to make such a boundary correct when a measurement does ask for it: a loop
that NumPy cannot express without temporaries much larger than the data, run often, on data that
does not fit a vectorized form. Numba gives most of the speed with no build at all, at the price
of a large dependency (LLVM) and a compilation at first call; that is why the package uses NumPy
and Numba appears only in a measurement (tool TL-36).
