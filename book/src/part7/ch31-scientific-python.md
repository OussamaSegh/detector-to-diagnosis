# The scientific Python package: analysis you can defend {#ch31}

::: box-why
Every PET group has analysis scripts: a photopeak fit, a timing histogram, a count rate plot. They
answer questions quickly, and for exploration that is what they should do. The trouble starts when a
script's number becomes evidence: the daily check that lets the scanner be used, the acceptance test
of a detector module, the figure in a verification report. Then three things matter that a script
rarely has. The number must be right, which for a fit of a few hundred counts is not what
`curve_fit` gives by default. It must be reproducible, which needs the same code and the same
library versions next year. And it must be traceable, so that when a check fails someone can say
exactly which files and which code produced it. This chapter builds MiniDAQ's analysis as a package
that has all three, and measures what goes wrong without them.
:::

**A day in the life.** A detector physicist at a PET site runs the morning QC on a point source and
sees the energy resolution at 11.6%, better than the 12.1% of the week before. Nothing was changed
on the scanner. The resolution of a detector does not improve by itself, so the physicist looks at
the analysis. The QC script had been "cleaned up" by a colleague the previous Friday: its fit range
had moved from 440 to 580 keV to 460 to 560 keV, cutting the tails of the peak, and its environment
had been rebuilt with a newer SciPy whose least squares stopped at a slightly different point.
Neither change was wrong in itself. Both changed the number, nobody had recorded either, and the
week's QC records could not be compared with the baseline. The fix took an hour. Working out what
had happened took two days, because the reports did not say which code or which protocol had
produced them.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Lay out a Python package for analysis: a `src` layout, a `pyproject.toml`, a lock file of exact
   versions, tests, type checks and lint run by CTest and CI.
2. Read a binary list-mode file larger than memory through a memory map and NumPy structured dtypes,
   in chunks of whole blocks, and say where the memory goes.
3. Explain why least squares weighted by the observed counts biases a weak peak, fit by Poisson
   maximum likelihood instead, and get each parameter's error from the Fisher information.
4. Check that a fit's errors are right with pull tests, and propagate the covariance to a derived
   quantity such as the energy resolution.
5. Measure the coincidence time resolution on a time difference that does not fold the peak.
6. Test a count rate for constancy and for a dip, and turn the results into checks against a
   protocol's limits.
7. Record the provenance of a report: the SHA-256 of every input, the code's commit and the versions
   of the libraries that can change a number.

## Prerequisites and estimated time {.unnumbered}

Chapter 12 (the MDQ-L1 list-mode format), Chapter 26 (the energy and time calibration) and Chapter
29 (Python and C++ in one build). Some statistics: the Poisson distribution, a likelihood, a
chi-square test. Reading: about 3 hours. Exercises: 5 hours. Milestone: 6 hours. If time is short,
do Exercises 31.1 and 31.2.

## From scripts to a package

MiniDAQ's Python lived in `tools/`: the calibration procedure (Chapter 26), the corrections and the
reconstruction (Chapters 27 to 30). Each tool read MDQ-L1 with its own reader and fitted its own
peaks. That was the right start, and the tools have tests. But a QC analysis is different in one
way: its output is a record that decides whether the scanner is used, and it is read by people who
did not write it. ADR 0026 records the choice of form.

A notebook is the usual form of an analysis, and for exploration it is good. As the form of a QC
record it has three problems. Its state depends on the order in which its cells ran, so the same
notebook can give two results. Its file is JSON with outputs embedded, so a review sees a diff of
base64 images. And nothing in the build runs its code, types it or lints it. A notebook is a fine
place to explore a run; a package is where the code that produces evidence lives, and a notebook can
import it.

The package is `analysis/`, called `minidaq_analysis` when imported:

```text
analysis/
  pyproject.toml          the package: name, version, dependencies, entry point, tool settings
  requirements.lock       every package of the environment, at an exact version
  CMakeLists.txt          three CTest tests: pytest, mypy, ruff
  run_checks.py           runs one of them; skips (77) when the environment is not installed
  src/minidaq_analysis/
    listmode.py           MDQ-L1 through a memory map
    fitting.py            histograms, models, Poisson maximum likelihood
    histograms.py         the histograms of a run, filled chunk by chunk
    rates.py              constancy and dip tests of a count rate
    report.py             the QC protocol, the checks, the report
    plots.py              figures with residuals
    provenance.py         manifests and the environment
    __main__.py           the program minidaq-qc
    py.typed              the package's type hints are part of its interface
  tests/                  pytest, one file per module, each test tagged with its requirement
```

Three choices in that tree are worth stating. The `src` layout puts the package one directory below
the project, so a test can only import it as installed or through an explicit path, never by
accident from the current directory; a test that passes only because it found the source next to it
is a test of the wrong thing. The `pyproject.toml` is the one place for the package's metadata and
its tools' settings (pytest, mypy, ruff); its build backend is scikit-build-core with CMake switched
off, because the package is pure Python, and the same backend builds a compiled part with CMake when
one is needed, as Chapter 32 does for the projector's wheel, without a change of backend. And
`py.typed` says that the type hints are meant for callers: mypy in strict mode checks the package,
and a caller's mypy checks its use.

### An environment you can rebuild

`pyproject.toml` states what the package needs: `numpy>=1.26`, `scipy>=1.11`, `matplotlib>=3.6`.
Those are ranges, which is right for a library that others install next to their own packages. They
are not an environment. Two machines that install the package a month apart get different SciPy
versions, and the day-in-the-life story shows what that can do to a number.

`requirements.lock` is the environment: every package, direct and indirect, at one exact version
(NumPy 2.5.3, SciPy 1.18.1, Matplotlib 3.11.2 and the nine packages Matplotlib needs besides NumPy,
pytest, mypy and ruff with theirs, Numba and llvmlite, scikit-build-core). CI's job `python` creates
a virtual environment, installs exactly that list, and runs `pip check`, which fails if any
installed package's own requirements are not met by the others. Then it builds the simulator and
runs the three CTest tests with `MINIDAQ_ANALYSIS_REQUIRED=1`, so a missing package is a failure
there instead of a skip. A developer's machine without the environment skips the three tests with
CTest's status 77, and says why, rather than failing them or running them against whatever NumPy the
system has.

Every package in the lock file is SOUP of a tool: none of it ships in the product, but its results
become evidence. The SOUP list's section 2 names them with the lock file as their pin, and the tool
list records what each is trusted for: the package itself (TL-33), NumPy, SciPy and Matplotlib
(TL-34), pytest, mypy and ruff (TL-35), and Numba, which only a measurement uses (TL-36). Each tool
class rests on a test that shows the tool can fail: for TL-34, the dip test that must find one lost
block; for TL-33, the test that shows least squares biased where the package's fit is not. A lock
file is also a maintenance cost: every upgrade is a change with a SOUP review, and the wheels it
pins are for one Python version.

## Reading runs larger than memory

A run of the scanner is many MDQ-L1 files of up to 1 GiB each. The corrections tool's reader,
`tools/recon/listmode.py`, reads a whole file into memory and decodes it, which is right for the 2D
reconstruction of a short run. For a QC pass over a long run on a laptop it is not.

### Structured dtypes: the format, in NumPy

A record of MDQ-L1 is 16 bytes of little-endian fields with no padding. NumPy can describe exactly
that:

```{.python include="analysis/src/minidaq_analysis/listmode.py" snippet="dtypes"}
```

An array of `RECORD` is the bytes of the file, seen as records. `records["crystal_a"]` is a view of
every record's crystal field, with a stride of 16 bytes; no Python loop touches a record. The `<` in
each field says little-endian, which the format specifies, so the reader is correct on a big-endian
machine too, where NumPy converts on access. The `assert` after the definitions checks the sizes
against the specification: a dtype with a field of the wrong width would shift every field after it,
and every value would be wrong without an error.

### A memory map, block by block

`ListModeFile` opens the file and maps it with `mmap`: the operating system makes the file's bytes
addressable without reading them, and pages them in as they are touched. Opening reads the file
header (32 bytes of fixed fields, the JSON metadata padded to a multiple of 8 bytes, and a CRC) and
then walks the block headers:

```{.python include="analysis/src/minidaq_analysis/listmode.py" snippet="walk"}
```

The walk is as strict as the format: the magic and the header CRC of every block, the sequence
numbers, a record count and flags that make sense, records that fit in the file, the payload CRC
(unless `verify=False`), a closing block, and nothing after it. A file that fails any of these is a
`FormatError` that names the file, the block and the reason. A truncated file from a crashed
acquisition is an error here, not a shorter run: recovering it is a separate step that needs a
person (Exercise 12.5).

The records of one block are a NumPy view of the mapped bytes, no copy:

```python
np.frombuffer(self._map, dtype=RECORD, count=count, offset=offset)
```

That view is valid because the format puts each block's records right after its 32-byte header, and
a block's offset in the file is a multiple of 8: the records are where the dtype expects them,
whole. A format with padding inside a record or records split across blocks would need a copy.

`chunks()` gives the coincidences of consecutive whole blocks, about a million records at a time,
decoded into arrays of the fields a caller uses:

```{.python include="analysis/src/minidaq_analysis/listmode.py" snippet="chunks"}
```

Decoding does what the format says once, in one place: the delayed bit is split from crystal A, tags
(crystal 0x7FFF) are counted and dropped, each record's time is its block's base time plus its
offset, and energies are scaled from 1/32 keV. A `Run` joins the files that its run record lists,
and checks that every file but the last ends with "end of file" and the last with "end of run": a
run with a missing middle file is an error too.

### Where the memory goes

`measurements/ch31/analysis.txt` reads a synthetic 1 GiB file (67 million records) five ways, each
in a fresh process, three times:

| Reader | Time, s (median) | Private memory, MiB | File pages, MiB |
|---|---:|---:|---:|
| Corrections tool, `read_file` (whole file decoded) | 7.7 | 6,038 | 17 |
| `ListModeFile.coincidences()` (mapped, decoded whole) | 3.0 | 3,777 | 1,042 |
| `RunHistograms` over chunks, with pair counts | 13.9 | 1,286 | 1,067 |
| `RunHistograms` over chunks, without pair counts | 6.6 | 179 | 1,067 |
| Open and check every payload CRC, decode nothing | 0.6 | 15 | 1,040 |

Two kinds of memory appear, and they mean different things. Private (anonymous) memory is what the
process allocated: arrays, objects. File-backed pages are the mapped file in the page cache, counted
against the process while it maps them, but owned by the kernel, shared, and dropped first when
memory is short. A pass that maps a 1 GiB file shows about 1 GiB of file pages whatever it does;
what decides whether it fits on a laptop is the private memory.

Decoding the whole file through the map costs 3.7 GiB. The decoded fields take 29 bytes per record
(the time in 64 bits, the crystals, the time difference and the energies in 32, the delayed flag in
one), 1.8 GiB for the file, and `coincidences()` holds the decoded chunks and their concatenation at
the same time, which doubles it. The corrections tool's reader costs 6 GiB because it also builds
intermediate arrays. The chunked pass costs 179 MiB, the size of one chunk's arrays and
the histograms, and would cost the same for a 100 GiB run. The row with pair counts is the lesson of
the measurement: counting coincidences per crystal pair keeps one entry per distinct pair, and an
extended source over the whole ring has tens of millions of them. That memory grows with the run,
not with the chunk. The first version also merged the pair counts after every chunk, which sorted
the growing total each time and took minutes; merging every sixteen chunks fixed the time, and
`count_pairs=False` lets a pass that does not need them leave them out.

The CRC check of the whole file takes 0.6 s from the page cache. It reads every byte once,
sequentially, and it is the reason `verify=True` is the default: a damaged block found at open is an
error before any number is computed.

Figure [](#fig-ch31-readers) puts the five readers on one plane.

```{.figure #fig-ch31-readers src="book/figures/plots/ch31/readers.py" caption="Five ways to read a 1 GiB list-mode file: the median time against the private memory each needs. The chunked pass without pair counts holds 179 MiB whatever the size of the run." alt="Scatter on a log memory axis. The whole file in memory: 6,038 MiB, 7.7 s. Mapped and decoded whole: 3,777 MiB, 3.0 s. Chunks with pair counts: 1,286 MiB, 13.9 s. Chunks without pair counts: 179 MiB, 6.6 s. Mapped with CRCs only: 15 MiB, 0.6 s. A dotted line marks the file's 1,024 MiB." width="75%" inputs="measurements/ch31/analysis.txt"}
```

## Fitting counts

A QC report reduces histograms to a few numbers: the photopeak's position and width, the timing
peak's width and center. Each comes from a fit of a model to counts, and each needs an uncertainty,
because a limit of 14% on the energy resolution means something different for a measured 13.9% ±
0.04% than for 13.9% ± 1%.

### A model of expected counts per bin

A histogram bin holds the number of events between its edges. A model of it should give the expected
number in the same interval, not the density at the bin's center times its width. For a Gaussian the
integral is exact with the error function:

```{.python include="analysis/src/minidaq_analysis/fitting.py" snippet="models"}
```

The difference matters when the bins are not small against the peak: a timing peak of 300 ps FWHM in
20 ps bins is fine either way, a 1.2 keV-wide feature in 1 keV bins is not. Integrating also keeps
the area parameter in counts, so the fitted area is the number of events in the peak.

The background under the photopeak is a straight line, and it has a trap. Written as `b0 + b1 * x`,
a line can be negative at one end of the range even when both parameters are within any simple
bounds, and a negative expected count is impossible for a Poisson likelihood. `gaussian_plus_line`
writes the line by its values at the two ends of the fit range, `b_low` and `b_high`. Bounding both
at zero keeps the whole line at or above zero, because a straight line between two non-negative
values is non-negative.

### Why least squares weighted by the counts is wrong

The usual fit of a histogram is least squares with each bin weighted by its own count:
`curve_fit(model, x, n, sigma=np.sqrt(n))`. It minimizes Neyman's chi-square, the sum of `(n - mu)^2
/ n`. It looks reasonable: a Poisson count's variance equals its mean, and `n` estimates the mean.
The flaw is that it estimates each bin's variance from the same count that is being fitted. A bin
that fluctuated low gets a small variance and a large weight, and pulls the fit down; a bin that
fluctuated high gets a small weight. Bins with zero counts need a fudge (MiniDAQ's code uses one
count, a common choice) and still pull. The result is biased low, and the bias grows as the counts
per bin fall.

`measurements/ch31/analysis.txt` measures it: a Gaussian peak at 511 keV with sigma 26 keV on a flat
background, fitted from 440 to 580 keV in 1 keV bins, 400 histograms for each number of counts:

| Counts in the peak | Counts per bin at the top | Area bias, Neyman | Area bias, Poisson | Area pull SD, Neyman | Area pull SD, Poisson |
|---:|---:|---:|---:|---:|---:|
| 100 | 1.5 | -32.2% | -5.4% | 0.82 | 0.88 |
| 300 | 4.6 | -34.1% | -3.0% | 1.53 | 0.86 |
| 1,000 | 15.3 | -13.3% | -0.4% | 1.26 | 0.87 |
| 3,000 | 46.0 | -2.4% | -0.1% | 0.93 | 0.97 |
| 10,000 | 153.4 | 0.0% | +0.2% | 0.98 | 0.99 |
| 100,000 | 1,534 | 0.0% | 0.0% | 0.95 | 0.95 |

At 1,000 counts, a peak of a short QC acquisition or of one crystal's spectrum, least squares
underestimates the area by 13%, and the spread of its estimates is 1.26 times what its errors say:
the error bars are too small as well as the value. At 10,000 counts the two fits agree, which is why
the bias is rarely noticed: the fits people check by eye are of strong peaks. At 100 counts even
maximum likelihood is biased by a few percent, which is a property of so few counts, not of the
method: no fit makes 1.5 counts per bin into a precise width.

Figure [](#fig-ch31-fits) draws the table.

```{.figure #fig-ch31-fits src="book/figures/plots/ch31/fits.py" caption="Least squares weighted by the counts against Poisson maximum likelihood, 400 histograms per point. Left, the bias of the fitted area; right, the spread of the area's pull, which is 1 when the reported errors are right." alt="Left: area bias in percent against counts in the peak from 100 to 100,000 on a log axis. Neyman least squares is minus 32% at 100 and minus 34% at 300, minus 13% at 1,000, and near 0 from 10,000. Poisson likelihood is minus 5% at 100 and near 0 from 1,000. Right: pull SD; Neyman reaches 1.53 at 300 counts, Poisson stays between 0.86 and 0.99." width="100%" inputs="measurements/ch31/analysis.txt"}
```

### Poisson maximum likelihood

The right fit for counts maximizes the Poisson likelihood of the observed histogram. Equivalently,
it minimizes the deviance:

D = 2 sum over bins of (mu - n + n ln(n / mu)), with n ln(n / mu) taken as 0 where n = 0.

The deviance is minus twice the log likelihood plus a constant that makes it zero for a perfect fit;
astronomers call it the Cash statistic. Empty bins are handled exactly: they contribute `2 mu`,
which pushes the model down where nothing was seen, by the right amount. At its minimum the deviance
is approximately chi-square distributed with the number of bins minus the number of parameters as
its degrees of freedom, when most bins expect several counts, so `D / ndf` near one says the model
fits.

The package minimizes the deviance by Fisher scoring, Newton's method with the expected curvature
instead of the exact one:

```{.python include="analysis/src/minidaq_analysis/fitting.py" snippet="scoring"}
```

With `J` the derivative of the expected counts with respect to the parameters, the score `U = J^T (n
/ mu - 1)` is the gradient of the log likelihood and `I = J^T diag(1 / mu) J` is the Fisher
information, the expected curvature. A step solves `I step = U`. Three details make it robust. A
step that does not lower the deviance is halved until it does. Parameters are projected onto their
bounds, and a parameter on a bound whose score pushes it further out is held there, so a background
of zero at one end of the range is a valid answer, not a failure. And the fit starts from the least
squares solution when that solution is valid: maximum likelihood needs a start near its minimum, and
a background guessed from the tails of a peak is not always one.

That last detail came from a failure. The first version used SciPy's general minimizer L-BFGS-B on
the deviance from a guessed start, and on one histogram it stopped at a deviance per degree of
freedom of 8.5 with the peak's mean at 509.8 keV instead of 511. A general minimizer knows nothing
about the problem; Fisher scoring uses its structure (the curvature is cheap and positive definite
wherever the model is valid), and its convergence test means something: the fall of the deviance
that a full step predicts, `U . step`.

A second failure taught more. On seed 2 of the five simulated QC runs below, the timing fit stopped
with "fit cannot lower the deviance". The fit was at its minimum to every visible digit, but the
predicted fall was 8e-8 and no step, however short, lowered the deviance. The derivatives were the
cause. `J` is computed by central differences, and the first version's step was 1e-6 of the
parameter's value, or of 1e-3 for a smaller value. The timing peak's mean was 0.016 ps, so its step
was 1.6e-8 ps, where the difference of two model values is mostly rounding: the score for the mean
changed sign with the step size, and the Newton step pointed uphill. The fix gives every step a
floor of 1e-5 of a unit (`_step` in `fitting.py`), and the fit then converges normally, with a
predicted fall of 7e-12. A second, defensive change accepts a fit that no step can improve when its
predicted fall is already below 5e-5, a change far below any parameter's error, and still raises an
error when a stuck fit is far from its minimum.

The regression test is that run's real timing histogram, stored in
`analysis/tests/data/timing-seed2.json`: it fails with the old code and passes with either change. A
synthetic histogram of the same size did not reproduce the failure, because its mean was not close
enough to zero; that is why the test uses the real one.

Better derivatives broke another test, for a good reason.
`test_a_fit_that_cannot_work_raises_instead_of_returning_a_number` fits a Gaussian to a flat
histogram, where the peak's area goes to zero and its mean and width mean nothing. With the old
step, their derivatives were exactly zero, the curvature was singular, and the fit raised an error.
With the new step, the derivatives were tiny but not zero, and the fit returned a mean of 511 ± 5e12
keV. The test had passed for an accidental reason. The fit now raises an error when a parameter's
error is wider than everything its bounds allow, which is the real condition: the data do not
determine it.

### Errors from the Fisher information

The covariance of a maximum likelihood estimate is, for enough counts, the inverse of the Fisher
information at the minimum:

```{.python include="analysis/src/minidaq_analysis/fitting.py" snippet="fit"}
```

Each parameter's standard error is the square root of a diagonal element of the inverse, not one
over the square root of a diagonal element of `I` itself: the inverse accounts for the correlations,
which for a peak on a background are strong (a wider peak with less background fits nearly as well
as a narrower one with more). Exercise 31.2 asks you to show the difference.

Whether the errors are right is a question a test can answer. Fit many synthetic histograms whose
truth is known, and compute each fit's pull, (estimate - truth) / error. If the errors are right,
the pulls have a mean near zero and a standard deviation near one.
`test_the_errors_are_the_spread_of_the_estimates` does this for every parameter, and SRS-ANA-002
states the bounds: a mean between -0.15 and 0.15 and a standard deviation between 0.85 and 1.15. The
table above shows the same check for the Neyman fit failing at low counts.

A derived quantity gets its error by propagating the covariance. The energy resolution is `2.3548
sigma / mean`; its error is `sqrt(g^T C g)`, where `g` is the gradient of the resolution with
respect to the parameters, computed numerically by `FitResult.derived`. Using only the errors of
sigma and mean, as if they were independent, gives a different number whenever they are correlated,
and `test_derived_errors_include_the_correlation` checks that the package does not.

Finally, a fit that does not converge raises `RuntimeError`. It never returns its last parameters
with a flag that a caller may forget to read. For a QC report that is the difference between "the
run cannot be analyzed" and a plausible number that is wrong.

## The time difference that does not fold

The coincidence time resolution (CTR) is the FWHM of the distribution of the time difference between
the two singles of a true coincidence from a source at the center. MDQ-L1 stores `dt_ps` as the
later single's time minus the earlier's, so it is never negative. A histogram of it is half the
timing peak folded onto the other half: its width is not the CTR, and its center is not the time
offset between the two sides of the scanner.

The fix is to order the pair by something other than time:

```{.python include="analysis/src/minidaq_analysis/histograms.py" snippet="signed_dt"}
```

The time of the single in the lower-numbered crystal minus that in the higher-numbered one is a
signed quantity whose distribution is the whole peak, centered on the time of flight from the
source, zero for a centered point. Delayed coincidences, which estimate the randoms, carry the delay
in their `dt_ps`; it is removed first, so the delayed histogram shows the randoms' flat distribution
in the same window. The timing fit is a Gaussian on a flat background, because random coincidences
are uniform in time difference.

The histograms of a run are filled in one pass, chunk by chunk: the energy spectrum of both singles
of every prompt, the signed time differences of prompts and delayeds, the counts per crystal, the
pair counts, and the prompt and delayed counts per 10 ms. Histograms add, so the result does not
depend on how the run was cut into chunks, and `test_the_histograms_do_not_depend_on_the_chunks`
checks that for chunk sizes from 1 to the whole file. The pass also counts coincidences out of time
order, within and across chunks: the sorter of Chapter 13 writes them in order, and a reset or a
file in the wrong place shows here.

Figure [](#fig-ch31-fold) shows the difference on simulated prompts.

```{.figure #fig-ch31-fold src="book/figures/plots/ch31/fold.py" caption="The time difference that does not fold, on prompts drawn with a fixed seed. Stored as later minus earlier, the peak is folded onto its other half; ordered by crystal number, it is whole, with its centre and its width." alt="Two histograms of time difference from minus 1000 to 1000 ps. The folded one, in grey, starts at 0 and is twice as high and half as wide. The signed one is a symmetric peak centred on 0 with a 300 ps FWHM marked by a double arrow." width="80%"}
```

## Is the rate constant?

A QC acquisition of a long-lived source should have a constant prompt rate over a few seconds. A
rate that drifts or drops says something is wrong: a block that stopped sending, data lost on the
way to disk, a source that moved. Two tests look for different failures:

```{.python include="analysis/src/minidaq_analysis/rates.py" snippet="rate_check"}
```

The dispersion test asks whether the counts per bin vary more than Poisson counts of a constant rate
would. Its statistic, the sum of `(n - mean)^2 / mean`, is chi-square with one fewer degrees of
freedom than bins, so `p_constant` is uniform between 0 and 1 for a constant rate: at a limit of
0.001, one good run in a thousand fails. `test_a_constant_rate_is_rejected_at_the_stated_rate`
checks the uniformity over 2,000 synthetic runs: 5% of them must fall below 0.05, within the
binomial spread (a rate of one in a thousand would need far more runs to test).

The dispersion test is weak against one bad bin among many: one bin that lost 16% of its counts adds
little to a sum over 200 bins. The dip test looks at the lowest bin: the probability that a Poisson
count with the run's mean is at most that low, times the number of bins (a Bonferroni correction,
because the lowest of 200 bins is low by chance more often than any one bin). At 1,000 counts per
bin, losing one block of 160 coincidences in one bin gives a dip test p far below 0.001, and
SRS-ANA-004 requires the package to find it. The last bin of a run is partial and is left out of
both tests.

Figure [](#fig-ch31-rate) runs both tests on a constant run and on one with a lost block.

```{.figure #fig-ch31-rate src="book/figures/plots/ch31/rate.py" caption="Is the rate constant? Two synthetic runs of 200 bins of 10 ms, drawn with a fixed seed, checked with the package's own check_rate. One bin that lost a block of 160 prompts is plain to the dip test and only marginal to the dispersion test." alt="Two step plots of prompts per 10 ms over 2,000 ms, around 1,000 with a shaded band of 3 SD. The constant run has p constant 0.28 and p dip 0.036. The second has one bin near 1,200 ms dropped to 793, labelled the dip, with p constant 0.007 and p dip of about 1e-9." width="100%" inputs="analysis/src/minidaq_analysis/rates.py"}
```

## The QC report

The checks, their limits and the fit ranges are not in the code. They are in a protocol file, TOML
read by the standard library's `tomllib`, with a default built in:

```{.python include="analysis/src/minidaq_analysis/report.py" snippet="protocol"}
```

A protocol has a name and a version, which the report records, so a report says which limits it was
checked against, and a site can tighten a limit by writing a file instead of changing code. The
limits here are the book's, set from the simulator's resolutions: a real scanner's QC limits come
from its specification and its baseline (Chapter 30, assumption: confirm with team).

`quality_control` fills the histograms, fits, and turns every result into a check with its value,
its error, its limit and whether it passed:

```{.python include="analysis/src/minidaq_analysis/report.py" snippet="qc"}
```

Two checks are not about the detector. The prompts in the files must equal the number the run record
states, which the server counted as it wrote them: a file lost from the run, or a run record of
another run, shows here. And no coincidence may be out of time order. The fit quality is a check
too: a deviance per degree of freedom above 2 says the model does not describe the peak, and then
its width is not a resolution.

The program `minidaq-qc RUN.run.json OUT_DIR` writes `report.json` for scripts, `report.md` for
people, `provenance.json`, and three figures, each fit drawn over its histogram with a panel of
residuals below, because a fit that is wrong in its tails is easier to see in the residuals than in
the curve. It exits with status `0` when every check passes, `1` when one fails, and `2` when the
run cannot be analyzed: a damaged file, a fit that does not converge. In the last case it writes no
report, because a report with a missing number is easy to misread as a report that passed. A script
that runs the QC every morning branches on the status, not on parsing text.

### Five runs of the simulator

`measurements/ch31/analysis.txt` runs the QC on five 2-second acquisitions of the simulator's point
source (seeds 1 to 5, about 135,000 prompts each). The simulator's detector has an energy resolution
of 12% FWHM at 511 keV and blurs each single's time so that a pair has 300 ps FWHM:

| Seed | Result | Photopeak, keV | FWHM/E, % | CTR FWHM, ps | Timing center, ps |
|---:|---|---:|---:|---:|---:|
| 1 | pass | 511.09 ± 0.07 | 11.964 ± 0.037 | 303.2 ± 0.6 | +0.60 ± 0.35 |
| 2 | pass | 510.87 ± 0.07 | 11.955 ± 0.037 | 303.0 ± 0.6 | +0.02 ± 0.35 |
| 3 | pass | 511.01 ± 0.07 | 11.999 ± 0.037 | 303.9 ± 0.6 | +0.38 ± 0.35 |
| 4 | pass | 511.02 ± 0.07 | 11.963 ± 0.036 | 303.9 ± 0.6 | +0.34 ± 0.35 |
| 5 | pass | 510.99 ± 0.07 | 11.993 ± 0.037 | 302.9 ± 0.6 | +0.95 ± 0.35 |

The energy resolution comes back as 11.975%, within its error of the simulator's 12%: the analysis
measures what the detector was made to do. The five values spread by 0.020% against a reported error
of 0.037%; five values are too few to call that a disagreement (the sample standard deviation of
five draws is below 0.55 of the true one about one time in eight).

The CTR comes back as 303.4 ps, not 300, and its errors are 0.6 ps, so the 3 ps are real. They are
the depth of interaction. Run with `--ctr 0`, without any time blur, the simulator's time
differences have a standard deviation of 101 ps, from the photons' flight inside the crystals to the
depth where they interact. Most of that is in long tails (the quartiles are at -14 and +14 ps), and
the fit of the peak's core weighs tails less than a standard deviation does, so the 101 ps add 3 ps
to the core's FWHM instead of the 83 ps that adding variances would suggest. A CTR measured on a
real scanner includes the same effect, which is one reason the CTR of a scanner is wider than that
of two small crystals on a bench.

The timing centers average +0.46 ps, about three standard errors from zero. Half a picosecond is
fifty times below the 25 ps limit and well below anything a time calibration resolves, and its cause
was not investigated. A measurement that finds something small and unexplained should say so instead
of rounding it away.

Figure [](#fig-ch31-qc) shows the two resolutions seed by seed.

```{.figure #fig-ch31-qc src="book/figures/plots/ch31/qc.py" caption="The QC report on five runs of the simulator's point source. The energy resolution comes back within its errors of the simulator's 12%; the CTR is 3 ps above 300, many errors away, and the depth of interaction explains it." alt="Left: FWHM over E in percent for seeds 1 to 5, between 11.95 and 12.00 with error bars of 0.037, around a dashed line at 12. Right: CTR FWHM in ps for seeds 1 to 5, between 302.9 and 303.9 with error bars of 0.6, all above a dashed line at 300." width="100%" inputs="measurements/ch31/analysis.txt"}
```

## Provenance

When a check fails, or an auditor asks how a number in a QC record was obtained, the first questions
are which data and which code. The report answers both in `provenance.json`:

```{.python include="analysis/src/minidaq_analysis/provenance.py" snippet="manifest"}
```

The manifest lists every input by its path relative to the run's directory, its size and its
SHA-256. `verify_manifest` compares it with the files on disk later and names each one that is
missing or differs; a renamed or re-copied run is recognized by its content. The manifest's own
SHA-256, over its canonical JSON, names the dataset in one string that does not depend on the order
in which the files were listed. The environment record holds the package's version, the git commit
of its code (with `-dirty` if the checkout had changes), the versions of Python, NumPy, SciPy and
Matplotlib, the platform, the command line and the time.

This is what tools such as DVC automate for many datasets and pipelines; for a run of a few files
the manifest alone is enough. It proves which bytes were read, not who wrote them: the threat
model's new gap "QC reports are not signed" records that a report edited afterward, or computed from
files changed with recomputed CRCs, looks like any other.

Figure [](#fig-ch31-provenance) shows what the report records.

```{.figure #fig-ch31-provenance src="book/figures/tikz/ch31/provenance.tex" caption="A QC report's provenance. The manifest names the bytes that were read and the environment the code that read them; the manifest's own digest names the dataset in one string." alt="The run's files feed a manifest of each file's path, size and SHA-256, whose own SHA-256 is the dataset id. An environment record holds the package, the git commit and the library versions. Both go into provenance.json beside report.json, report.md and three figures. Notes say verify_manifest later names every missing or changed file, and that the report is not signed." width="90%"}
```

## Is a loop worth compiling?

NumPy is fast when the work is whole-array operations; it is slow when the work is a loop with a
decision per element. The per-crystal timing histogram is between the two: one count per entry into
a two-dimensional histogram. Exercise 31.3 writes it in C++ behind pybind11, and
`measurements/ch31/histogram-speed.txt` compares four implementations on 10 million entries, one
thread:

| Implementation | Time, ms | ns per entry | Against NumPy |
|---|---:|---:|---:|
| Python loop (1 million entries) | 165 | 165 | 0.10x |
| NumPy: `floor_divide` and one `bincount` | 169 | 16.9 | 1x |
| Numba `@njit`, after a 0.26 s compilation | 19 | 1.9 | 8.7x |
| C++ through pybind11 | 39 | 3.8 | 4.4x |

All four give the same counts, bin for bin. NumPy is ten times faster than the Python loop and four
to nine times slower than the compiled loops, because its version makes four temporary arrays of 10
million entries (an int64 copy, the bins, a mask, the keys), each a full pass through memory. The
C++ is twice as slow as Numba, and the reasons found are outside the language. Built outside the
project as a plain module, the same source took 32 to 34 ms with GCC and 28 ms with Clang. LLVM,
which Numba and Clang use, divides in 32 bits when the operands fit, and GCC's 64-bit division is
the slowest instruction in the loop; with a 32-bit division the GCC build took 26 ms, against 22 ms
for Numba with the same values passed as arguments. The rest of the difference was not found. A loop
in C++ is not faster for being in C++.

For this package none of them is needed: 0.2 s of NumPy per 10 million coincidences is small next to
reading them. The package stays pure Python and installs anywhere; Numba appears only in the
measurement. The question to ask before compiling anything is the one Chapter 29 asked: what does
the profile say, and what does the speed cost in build, binding and dependencies?

## What this leaves out

The package checks one run against fixed limits. Trending the reports over weeks, to find a slow
drift within the limits, is the site's QC program (Chapter 30's run rules apply). The earlier tools
keep their own readers; moving the corrections and the reconstruction onto `ListModeFile` is a
change of its own. The QC is of a point source; a uniform cylinder for the normalization, a count
rate test at several activities and a sensitivity measurement would each add protocol sections and
fits. And the package fits one-dimensional histograms; a joint fit of energy and time, or of every
crystal's spectrum at once, needs the same likelihood with more parameters and more care with the
starting values.

::: box-regulated
- **A tool whose output is evidence.** The package is tool TL-33: QC records and acceptance results
  are evidence of the device's performance, so the tool is validated like the test tools of Chapter
  20, with tests that show it can fail (least squares biased where it is not, a lost block found).
  It is not part of the device, and its validation is not the device's (assumption: confirm with
  team how your organization classifies analysis tools).
- **Requirements a test can check.** SRS-ANA-001 to SRS-ANA-006 state the reader's refusals, the
  fit's error bounds, the time difference, the rate tests, the report's checks and exit statuses,
  and the manifest. Each test of the package carries its requirement's tag, and the trace matrix
  lists them.
- **A hazard of the tool.** H-14 is a QC report that passes a degraded detector or a run that lost
  data. Its controls are RC-45 (Poisson fits with tested errors, the signed time difference, an
  error when a fit fails) and RC-46 (complete runs only, the rate checks, the prompt count, the
  protocol's limits, the exit status, provenance).
- **SOUP with a lock file.** The lock file is the pin of every Python package; the SOUP list's
  section 2 and the tool list record them, and an upgrade is a change request with a SOUP review.
  CR-0017 records the change and ADR 0026 the decision; Conan, lmfit and Jupyter were proposed and
  not approved.
- **Records that can be traced.** A QC record that names its inputs by SHA-256 and its code by
  commit is what an auditor asks for when a number is questioned (assumption: confirm with team the
  retention and format of QC records at your sites).
:::

::: box-mistakes
- **`curve_fit` with `sigma=np.sqrt(counts)` on low counts.** It biases a weak peak low and makes
  its errors too small. Fit counts by Poisson maximum likelihood.
- **Errors from the diagonal of the curvature.** Invert the whole matrix; the correlations of a peak
  and its background are strong.
- **Trusting a fit because it returned.** Check the deviance per degree of freedom, look at the
  residuals, and make a failed fit an error.
- **The CTR from `dt_ps`.** It is never negative, and its histogram folds the peak. Order the pair
  by crystal.
- **Reading a whole run into memory.** Map it and pass over it in chunks; check what grows with the
  run (the pair counts did).
- **A view of bytes that are not where the dtype expects.** Check the dtype's size against the
  format, and the alignment of what you view.
- **An environment from version ranges.** Two installs a month apart differ. Pin every package in a
  lock file and rebuild it in CI.
- **A synthetic regression test.** When a real input failed, keep the real input as the test.
:::

::: box-askteam
1. Which analysis produces the QC and acceptance records, and where does its code live? Is it
   versioned, tested and reviewed like product code?
2. How are peaks fitted: least squares or maximum likelihood? Has anyone checked the errors with
   pulls?
3. What do the QC reports record about their inputs and their code? Could you reproduce last year's
   report?
4. How is the analysis environment pinned, and who reviews an upgrade of NumPy or SciPy?
5. How is the time resolution measured, and on which time difference?
6. Which QC limits are set from the specification and which from a baseline, and who may change
   them?
:::

## Exercises {.unnumbered}

**Exercise 31.1 (E): Coincidences per crystal pair, through a memory map.** *Goal:* count the prompt
coincidences of each crystal pair of an MDQ-L1 file through `np.memmap` and a structured dtype,
without decoding records one by one. *Starter:* `exercises/ch31/e1_pair_counts/starter/pairs.py`.
*Acceptance:* `tests/test_pairs.py` passes: a pair is one key whichever crystal saw the earlier
single, delayed coincidences and tags are not counted, and 50,000 coincidences in blocks of 777
records give the counts of a direct count. Then answer in `NOTES.md` where the file is read, why the
records may be viewed in place, and how much memory a dense matrix of pair counts would take.
*Time:* 45 minutes.

**Exercise 31.2 (M): A timing fit you can trust at low counts.** *Goal:* fit a Gaussian on a flat
background, integrated over each bin, by Poisson maximum likelihood with only NumPy, with errors
that are the real spread of the estimates. *Starter:*
`exercises/ch31/e2_timing_fit/starter/timing_fit.py`, a least squares fit weighted by the counts.
*Acceptance:* `tests/test_timing_fit.py` passes: a strong peak within four standard errors of the
truth, the mean area of 300 weak peaks within 3% of the truth, pulls of the FWHM with a standard
deviation within 15% of one, and too few counts refused. Then answer in `NOTES.md` whether the
starter's bias is every fit or a few, why the fitted total equals the observed total, and why the
errors come from the inverse of the Fisher matrix. *Time:* 2 hours.

**Exercise 31.3 (H): The per-crystal timing histogram in C++, behind a Python boundary.** *Goal:*
write the histogram in C++ called through pybind11, with the bin edges exactly those of NumPy and a
safe boundary. *Starter:* `exercises/ch31/e3_histogram/starter/dthist.cpp`. *Acceptance:*
`tests/test_dthist.py` passes: the counts of a NumPy reference bin for bin, the edges (`lo` in the
first bin, `lo - 1` outside), int64 arrays converted, wrong lengths and crystal ids refused, and at
least 15 times the speed of a Python loop in an optimized build. Then answer in `NOTES.md` which
entries the starter put in the first bin, what `forcecast` does to a value that does not fit, and
whether the C++ is worth its build. *Time:* 2 hours.

## MiniDAQ milestone: the analysis package {.unnumbered}

::: box-milestone
**Goal.** MiniDAQ has an analysis package that reads runs of any size, fits by Poisson maximum
likelihood with tested errors, writes a QC report checked against a protocol with the provenance of
every input, and runs its tests, type checks and lint in CTest and CI from a pinned environment.
**Start:** tag `ch30`. **End:** tag `ch31`.
:::

1. Write change request CR-0017 and ADR 0026; add SRS-ANA-001 to SRS-ANA-006 (SRS version 20),
   hazard H-14 with RC-45 and RC-46, the lock file's packages to section 2 of the SOUP list (version
   14) and TL-33 to TL-36 to the tool list; update the architecture description (version 17) and
   review the threat model (version 5).
2. Add `analysis/` with its `pyproject.toml`, `requirements.lock`, the modules and their tests, each
   test tagged with its requirement; add `analysis/CMakeLists.txt` and `run_checks.py`, and the CI
   job `python`.
3. Add `measurements/ch31/analysis.py` (the readers, the two fits, five QC runs, the run without
   time blur) and `measurements/ch31/histogram_speed.py`.
4. Add Exercises 31.1 to 31.3.

**Definition of done.** `ci/run_all.sh` is green on all six presets and the CI job `python` passes
with every package required; mypy in strict mode and ruff report nothing; the trace matrix shows
SRS-ANA-001 to SRS-ANA-006 tested; five simulated runs pass the QC with the simulator's resolutions;
every starter of the chapter fails. Tag `ch31`.

## Check yourself {.unnumbered}

1. Why does a package with a `src` layout keep a test from importing the wrong code?
2. What is the difference between the version ranges of `pyproject.toml` and the lock file, and who
   needs each?
3. Why may the records of an MDQ-L1 block be viewed in place as a structured array? What would
   prevent it?
4. A pass over a 1 GiB file shows 1 GiB of file pages and 179 MiB of private memory. Which one
   decides whether it fits on a laptop, and why?
5. What grew with the run in the first chunked pass, and how was it fixed?
6. Why does least squares weighted by the counts bias a weak peak low? What does it do with an empty
   bin?
7. Write the Poisson deviance. What does an empty bin contribute?
8. Why does Fisher scoring start from the least squares solution, and what happened without it?
9. Why did the fit of seed 2 fail, why is its regression test a real histogram, and which test did
   the fix break?
10. How do you check that a fit's errors are right? What did the check show for least squares at
    1,000 counts?
11. Why is the error of the energy resolution not computed from the errors of sigma and mean alone?
12. Why is the CTR not the FWHM of a histogram of `dt_ps`?
13. Why does the dispersion test miss one bin that lost 16% of its counts, and what finds it?
14. Why does `minidaq-qc` write no report when a run cannot be analyzed?
15. The simulator blurs pairs to 300 ps; the QC measures 303.4 ps. Where do the 3 ps come from?
16. What does a manifest prove, and what does it not?

## Summary {.unnumbered}

- Analysis whose numbers are evidence lives in a package: `src` layout, `pyproject.toml`, tests,
  mypy in strict mode and ruff run by CTest, and a lock file of exact versions that CI rebuilds and
  checks with `pip check`.
- `ListModeFile` maps MDQ-L1, checks every header, CRC and sequence number at open, and views each
  block's records in place as a structured array. A chunked pass over 1 GiB takes 179 MiB of private
  memory; decoding the whole file takes 3.7 GiB, and the corrections tool's reader 6 GiB.
- Models give expected counts per bin, integrated over the bin; a line is written by its two end
  values so that bounds keep it non-negative.
- Least squares weighted by the counts underestimates a 1,000-count peak by 13% with errors too
  small; Poisson maximum likelihood, solved by Fisher scoring with projected bounds and a least
  squares start, is within 1%, and its pulls have a standard deviation near one.
- Errors come from the inverse of the Fisher information; derived quantities propagate the full
  covariance; a fit that does not converge is an error.
- The CTR is measured on the time difference ordered by crystal; the folded `dt_ps` halves the peak.
- The rate is tested for constancy (dispersion) and for a dip (lowest bin, Bonferroni); a lost block
  of 160 in 1,000 is found.
- The QC report checks a TOML protocol's limits, the prompt count and the time order, writes JSON,
  Markdown, figures with residuals and provenance, and exits 0, 1 or 2.
- Five simulated runs pass with 11.975% and 303.4 ps; the 3 ps are the depth of interaction.
- A manifest of SHA-256 and an environment record make a report traceable; they do not make it
  authentic.

## Further reading {.unnumbered}

- W. Cash, "Parameter estimation in astronomy through application of the likelihood ratio", *The
  Astrophysical Journal* 228 (1979) 939 to 947, for the Poisson likelihood statistic (verify).
- S. Baker and R. D. Cousins, "Clarification of the use of chi-square and likelihood functions in
  fits to histograms", *Nuclear Instruments and Methods in Physics Research* 221 (1984) 437 to 442,
  for the bias of Neyman's and Pearson's chi-square and the likelihood ratio for histograms
  (verify).
- G. Cowan, *Statistical Data Analysis*, Oxford University Press, 1998: maximum likelihood, the
  Fisher information, and error propagation.
- F. James, *Statistical Methods in Experimental Physics*, 2nd edition, World Scientific, 2006.
- The NumPy documentation on structured arrays and on `numpy.memmap`, and the Python documentation
  of `mmap` and `tomllib`.
- The Python Packaging User Guide, on `pyproject.toml`, the `src` layout and lock files.
- ADR 0026 and CR-0017 in the repository: the decision and the change record.
