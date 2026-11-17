# Exercise 31.4: notes on the solution

Measured with the acceptance tests' data (64 crystals, 200,000 values, a spread of about 50 per
crystal, so a variance of about 2,500), on the book's reference machine (Python 3.13, NumPy 2.5.3).

## 1. The mean of the means

The mean of the chunks' means weights every chunk the same, whatever the number of values each
crystal had in it. With equal chunks of random crystals each crystal has about the same count in
every chunk, so the error is small but not zero: 0.13 at most on means spread over hundreds, which
fails a tolerance of 1e-9. With the second test's chunks (1,000 values of crystal 0, then 7, an
empty one, 150,000 and 3) a chunk of 3 values counts as much as one of 150,000, and the means are
wrong by up to 440. The empty chunk adds a mean of 0 for every crystal. It is exact only when every
crystal has the same count in every chunk, which a detector never gives.

## 2. The sum of squares at a large offset

At the offset 3.6e15, `sum2 - n mean^2` gave variances wrong by a relative 9e13, and the plain
one-pass formula `(sum2 - sum^2 / n) / (n - 1)` with the right sums gave a median of -3.1e17: a
negative variance. A double has 53 bits, about 16 significant digits. `x^2` for `x = 3.6e15` is
1.3e31, whose last digit is worth about 1e15, and a variance of 2,500 is the difference of two
such numbers summed over thousands of values. Nothing of it survives. The test of the mean also
fails, by 29: a mean of 3.6e15 stored in a double has a resolution of 0.5.

## 3. What makes the offset harmless

Merging by the difference of two means is necessary but not enough: each chunk's own mean and M2
are still computed from values of 3.6e15, and a sum of thousands of them has lost the digits. What
works is to subtract a per-crystal origin, the first value the crystal ever had, before anything
is summed. The differences are exact (two doubles within a factor of two of each other subtract
exactly), and of the size of the spread, so the sums keep their digits. The cost is one array of
origins and one subtraction per value. With it the variances agree with the reference within a
relative 2e-15 and the means within 1e-13. The reference itself shifts by one value for the same
reason: `np.var` on the raw values would have been the wrong yardstick.

The two passes per chunk (the mean, then the squared deviations from it) are over the chunk only,
which is in memory anyway; the run is still read once.
