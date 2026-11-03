# CR-0017: The analysis package and its QC report

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-03, by the software lead with the physics team |
| Source | improvement: a daily QC check of the scanner needs an analysis whose numbers are right, reproducible and traceable; each tool had its own reader and fits, and none recorded its inputs (ADR 0026) |
| Decision | approved, 2026-11-03, software lead and risk manager |
| Commits | 46c0417, a039853, 81aa87c and the commit that adds the chapter |

## Description

A new installable Python package, `analysis/` (`minidaq_analysis`), reads MDQ-L1 runs through a
memory map in chunks of whole blocks, fills a run's histograms in one pass, fits peaks by Poisson
maximum likelihood with errors from the inverse Fisher information, measures the coincidence time
resolution on the crystal-ordered time difference, tests the rate for constancy and for a dip,
and writes a QC report (JSON, Markdown, figures) checked against the limits of a protocol file,
with a manifest of its inputs and a record of its environment. Its dependencies are pinned in
`analysis/requirements.lock`; CTest runs its tests, mypy and ruff, and CI has a job that builds
its environment from the lock file. The fit of one simulated run stopped with an error at its
minimum: the numerical derivatives used a step of 1.6e-8 ps for a timing mean near zero, which
made the score rounding noise. The step now has a floor of 1e-5 of a unit, a fit that no step can
improve is accepted when its predicted fall of the deviance is below 5e-5, and a parameter whose
error is wider than its bounds is an error (the derivatives had hidden that case).

## Reason

The QC result decides whether the scanner is used. Least squares weighted by the observed counts
underestimates a peak of 1,000 counts by 13% (`measurements/ch31/analysis.txt`), and the folded
time difference of the files halves the timing peak; a report that names neither its inputs nor
its code cannot be investigated when a check fails.

## Impact analysis

### Requirements

New: SRS-ANA-001 to SRS-ANA-006 (SRS version 20), all verified by test. No requirement changed.

### Software items and safety class

None of the product's: the package is a tool (TL-33) outside the shipped programs. Nothing in
`minidaq/` changed.

### Risk

New hazard H-14 (a QC report that passes a degraded detector or a run that lost data) with risk
controls RC-45 (Poisson fits with tested errors, the crystal-ordered time difference, an error
when a fit fails) and RC-46 (complete runs only, the rate checks, the prompt count against the run
record, the protocol's limits, the exit status, provenance). Its residual risk names the book's
limits and the slow drift within limits, which trending finds.

### SOUP

New, section 2 of the SOUP list (tools, not shipped): the Python packages of
`analysis/requirements.lock`, among them NumPy 2.5.3, SciPy 1.18.1, Matplotlib 3.11.2, Numba
0.68.1, pytest 9.2.0, mypy 2.4.1, ruff 0.17.3 and scikit-build-core 1.1.2; tools TL-34 to TL-36.
Approved by the software lead on 2026-11-03. Conan, lmfit and Jupyter were proposed and not
approved.

### Interfaces and data formats

None changed. The package reads MDQ-L1 and the run record as their specifications define them;
the QC report's JSON is a new output read by people and scripts (its exit status is the
interface a script uses).

### Documents

ADR 0026 (new) and the ADR index; the SRS, version 20; the trace matrix; the risk file (H-14);
the architecture description, version 17; the SOUP list, version 14; the tool list (TL-33 to
TL-36); the threat model, version 5 (reviewed: no element added, the gap "QC reports are not
signed"); the CHANGELOG.

### Regulatory

The intended use of MiniDAQ does not change. The package is a tool whose output is evidence (QC
records); it is validated as a tool (the tool list), not as part of the device.

## Verification

The package's tests (`ctest -R '^analysis\.'`: analysis.pytest, analysis.mypy, analysis.ruff),
among them test_listmode::test_refuses_a_file_that_is_not_complete_and_intact,
test_fitting::test_the_errors_are_the_spread_of_the_estimates,
test_fitting::test_neyman_least_squares_underestimates_a_weak_peak,
test_fitting::test_a_timing_fit_at_the_precision_of_the_deviance_converges (fails with the first version's fit), test_histograms::test_the_histograms_do_not_depend_on_the_chunks,
test_rates::test_one_missing_block_is_a_dip, test_report::test_a_lost_block_and_a_wrong_count_are_found
and test_report::test_a_simulated_point_source_passes_with_the_simulators_resolutions, run in CI
with every package required; the measurements in `measurements/ch31/`, where five simulated runs
pass with the simulator's resolutions; Exercises 31.1 to 31.3, whose starters fail.

## Decision

Approved on 2026-11-03 by the software lead and the risk manager: a tool with pinned dependencies,
Poisson fits and provenance, no change to the product, and the book's QC limits (assumption:
confirm with team the scanner's QC protocol and limits).
