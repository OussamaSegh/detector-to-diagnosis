# Exercise 29.2 (M): Work shared between threads

**Goal.** Share a loop between threads so that every index is processed exactly once, and add
many contributions into one output from several threads without a data race and with a
reproducible result. These are the two halves of the C++ backprojector's `parallel_chunks` and
`back`.

**Time.** 60 minutes.

**Starter.** `starter/parallel_impl.hpp` and `starter/parallel.cpp` build and run.
`parallel_for(count, threads, body)` gives each of `threads` threads a chunk of `count / threads`
indices. `scatter_add(index, value, size, threads)` adds `value[i]` to `out[index[i]]` from every
thread into one output vector.

**Acceptance** (`tests/test_parallel.cpp`):
- `parallel_for` covers every index of 0, 1, 7, 100, 1001 and 43,584 exactly once with 0 to 9
  threads, with at least one call and no more calls than threads or indices.
- `scatter_add` of 200,000 values into 500 outputs gives the serial sum to 1e-12 relative with 2
  to 8 threads, and the same bits in 10 runs with 4 threads.
- `scatter_add` refuses an index outside the output with `std::out_of_range`, and gives zeros
  for no values.

**Then, by hand.**
1. Which indices did the starter's `parallel_for` miss for 43,584 lines and 5 threads, and for 7
   indices and 9 threads?
2. Run the starter's `scatter_add` under ThreadSanitizer (the `tsan` preset). What does it report,
   and why can the plain test pass on some runs and fail on others?
3. Why does the solution's result differ between 1 and 4 threads in the last bits, and why is
   that acceptable here and not for the number of counts in a sinogram? Answer in `NOTES.md`.

**Hints.** Chunk boundaries `count * k / t` cover `[0, count)` exactly for any remainder. Give
each thread its own output and add the outputs afterwards, in a fixed order. `std::jthread`
joins when it is destroyed.
