# Exercise 5.5 notes

**Why the median.** Benchmark times are skewed: the floor is the machine's best, and
interruptions only ever add time. The median is robust to a few slow runs; the mean is not.

**Why bootstrap.** The distribution of a ratio of medians has no simple formula. Resampling
the observed runs approximates how much the estimate would move if you repeated the whole
experiment, without assuming normality.

**Small samples.** With 5 runs per side there are only a few distinct medians a resample can
produce, so the interval is coarse and its coverage is below the nominal level (the percentile
bootstrap is known to under-cover for small n; verify: Efron and Tibshirani, *An Introduction
to the Bootstrap*, 1993). Five is the minimum for any judgement at all; for a release gate use
10 or more repetitions, interleave the two versions' runs so drift affects both, and keep the
raw samples. The regression gate of Exercise 5.3 uses a rank test (Mann-Whitney) for the
yes-or-no decision and the median ratio for the size of the effect.
