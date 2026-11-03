# Exercise 29.2: notes on the solution

**The two mistakes.**

- *The remainder.* `count / threads` rounds down, and `(count / threads) * k` leaves the last
  `count % threads` indices to nobody. With 43,584 lines and 5 threads the starter left the last
  4 lines out; with 7 indices and 9 threads the chunk was 0 and nothing ran at all. The
  solution's boundaries `count * k / t` differ by at most one between chunks and the last one is
  `count`. It also uses at most `count` threads, so no thread gets an empty chunk, and runs the
  body on the calling thread when one is enough.
- *Two threads, one output.* `out[index[i]] += value[i]` is a read, an addition and a write.
  When two threads do it to the same element at the same time, one addition is lost. That is a
  data race, undefined behavior in C++, and it shows only sometimes. The solution gives each
  thread its own output vector and adds them afterwards in thread order. It costs `threads` times
  the memory of the output (for the projector, 4 images of 128 x 128 doubles, 0.5 MB), and no
  thread ever waits for another.

**The missed indices** (Then, by hand, 1). With 5 threads the chunks were 0 to 8716, 8716 to
17,432, ..., 34,864 to 43,580: lines 43,580 to 43,583 were never computed. In a sinogram they
are the last radial bins of the last view, near the edge of the field, where a missing value
looks like an image edge effect and not like a bug.

**ThreadSanitizer** (2). It reports a data race on the output vector between two of the
threads, with the stacks of both accesses. Without it, a lost update needs two threads to touch
the same element within a few nanoseconds, so whether a run loses one depends on the scheduling
of that run: the race is real on every run and visible on some. A test that passes is not
evidence of the absence of a race; the sanitizer is.

**The last bits** (3). Floating-point addition is not associative: the solution adds each
output's contributions in a different order with 1 and with 4 threads (four partial sums, then
their sum), so the results differ by rounding, here below 1e-12 relative. With the same number
of threads the order is the same and so are the bits. A projection is a sum of real numbers that
the reconstruction iterates on, and rounding at 1e-15 is far below its noise. Counts are
integers, and a sinogram of counts must be exact: there the sum is done in integers (Chapter 12),
where the order does not matter.
