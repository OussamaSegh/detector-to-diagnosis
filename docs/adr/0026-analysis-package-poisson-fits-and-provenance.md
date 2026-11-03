# 0026. The run analysis as an installable Python package, with Poisson fits and provenance

Date: 2026-11-03
Status: Accepted

## Context

The physicists analyze runs in Python: the calibration procedure (Chapter 26), the corrections
(Chapter 27) and the reconstruction (Chapters 28 to 30) are Python tools in `tools/`, each with
its own reader of MDQ-L1 and its own fits. A daily quality control (QC) check of the scanner
needs one more analysis, of a point source: the photopeak's position and resolution, the
coincidence time resolution (CTR), the constancy of the rate. Its result decides whether the
scanner is used that day, so its numbers must be right, reproducible, and traceable to what
produced them. Four questions:

- what form the analysis code takes, and how its environment is fixed;
- how a run larger than memory is read;
- how peaks are fitted, and where their uncertainties come from;
- how a report names what it was computed from.

## Options

1. **Notebooks.** The usual form of an analysis, and good for exploration. A notebook's state
   depends on the order its cells ran in, its diff is JSON with outputs, and it is not tested or
   type-checked by the build. Jupyter was not approved as a dependency of the project.
2. **More scripts in `tools/`.** What the earlier chapters did. The scripts share no reader or
   fit, and each pins nothing beyond the system's Python.
3. **An installable package, `analysis/`,** with a `src` layout, a `pyproject.toml`, a lock file
   of exact versions, its tests run by CTest, mypy in strict mode and ruff, and a command line
   program for the QC report.

For the fits: least squares weighted by the observed counts (what `scipy.optimize.curve_fit`
does when given `sigma=np.sqrt(counts)`), least squares weighted by the model, or maximum
likelihood for Poisson counts.

## Decision

Option 3, with these rules:

- **Environment.** `analysis/requirements.lock` pins every package, direct and indirect, to an
  exact version; CI builds a virtual environment from it and runs `pip check`. NumPy, SciPy and
  Matplotlib are SOUP of a tool (TL-34); pytest, mypy and ruff are tools (TL-35); Numba is used
  only by a measurement (TL-36). None of them ships in the product. The package itself is TL-33.
- **Reading.** `ListModeFile` maps the file (`mmap`) and views each block's records in place as
  a NumPy structured array; it verifies every header, CRC, sequence number and the closing block
  when it opens the file, and gives the coincidences in chunks of whole blocks (SRS-ANA-001).
  The histograms of a run are filled chunk by chunk, so the memory is that of a chunk and the
  histograms, not of the run (SRS-ANA-003).
- **Fits.** Poisson maximum likelihood (the deviance, also called the Cash statistic), with the
  models integrated over each bin, parameter bounds, and the covariance from the inverse Fisher
  information; solved by Fisher scoring with projected steps, started from the least squares
  solution when that is valid. A fit that does not converge raises an error (SRS-ANA-002).
- **Time resolution.** On the time of the single in the lower-numbered crystal minus that of the
  higher-numbered one, not on the file's `dt_ps`, which is never negative and folds the peak
  (SRS-ANA-003).
- **QC report.** `minidaq-qc` checks every limit of a protocol file (TOML), writes JSON,
  Markdown and figures, and exits `0` (pass), `1` (a check failed) or `2` (the run cannot be
  analyzed, and no report is written) (SRS-ANA-005).
- **Provenance.** Every report carries a manifest of its inputs (path, size, SHA-256), the
  manifest's own SHA-256, and the environment: the package's version, the git commit, Python and
  the library versions, the platform and the command (SRS-ANA-006).

The earlier tools keep their own readers; moving them onto the package is a change of its own.

## Consequences

### Positive

- At 1,000 counts in a peak, least squares weighted by the counts underestimates the area by 13%
  and its errors are 26% too small; the Poisson fit's bias is under 1% and its pulls have a
  standard deviation near one (measurements/ch31). The difference is gone above about 10,000
  counts, which is why it is not seen on strong peaks.
- A 1 GiB run is analyzed with 179 MiB of private memory when the pair counts are left out, and
  1.3 GiB with them on a synthetic file of many distinct pairs, against 6 GiB for the reader of
  the corrections tool, which decodes the whole file at once (measurements/ch31).
- A report can be checked years later: the manifest proves which bytes it read, and the
  environment which code and libraries computed it.
- The analysis code is tested, type-checked and linted by the same CTest run as the C++.

### Negative

- A lock file to maintain: every upgrade is a change with a SOUP review, and the lock pins wheels
  for one Python version (3.12 in CI).
- Fisher scoring is code of our own where SciPy has general minimizers. They were tried first:
  L-BFGS-B stopped short of the minimum from a poor start. The package's own solver is tested by
  pull tests and by a real histogram on which its first version failed (CR-0017).
- The pair counts of an extended source take memory in proportion to the distinct pairs, not to
  a chunk; a pass that does not need them turns them off.
- The default protocol's limits are the book's, from the simulator's resolutions (assumption:
  confirm with team the scanner's QC limits).
