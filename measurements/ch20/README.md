# Chapter 20 measurements

Recorded 2026-10-25 and 2026-10-26 on the book's machine (4 vCPU VM, Ubuntu 24.04, GCC 13.3,
Clang 18) and on GitHub Actions `ubuntu-24.04` runners (2 vCPU, AMD EPYC 7763).

| File | What | How |
|---|---|---|
| `gate-selftest.md` | The gate self-test of 27a2b53: 15 of 15 planted faults caught for their reason, 12 minutes | `tools/gate_selftest.py measurements/ch20/gate-selftest.md` |
| `repro-local.txt` | Two builds of f63f5bf from two checkouts on the book's machine: identical | `tools/repro_check.sh OUT f63f5bf` |
| `repro-local-de1b7cf.txt` | The same for de1b7cf, with the manifest | `tools/repro_check.sh OUT de1b7cf` |
| `repro-local-2d123f5.txt` | The same for 2d123f5 | `tools/repro_check.sh OUT 2d123f5` |
| `repro-github-2d123f5.txt` | 2d123f5 built twice on a GitHub runner, copied from the job log | CI job `reproducible-build` |
| `package-contents.txt` | The files and sizes of the product archive of f63f5bf | `tar -tvf minidaq-0.3.0-f63f5bf1653f.tar` |
| `aa-local.txt` | 15 A/A comparisons of the release build of de1b7cf with itself | `tools/perf_ab.sh build/release build/release OUT 5 1`, 15 times |

## Results

- Reproducibility across machines (2d123f5): the programs, their debug files and the SBOM are
  identical on the book's machine and on the runner. The archives differ only in
  `BUILDINFO.json`, which records CMake, Ninja and Python versions that differ between the two.
- A/A on the book's machine: 1 false alarm in 15 jobs (`BM_HistogramRecord`, 0.946, p 0.0045);
  the exact 95% interval of the rate is 0.2% to 32%.
- A/A on GitHub (workflow `perf`, runs 40245601223, 40245605698, 40245610438 by
  `workflow_dispatch` with base = head, and 40245121399 for the push of de1b7cf against d4ef398):
  no alarm in 4 jobs; all 23 median ratios within 3.2% of 1, 19 within 1.0%. In the push job the
  base side lacked `BM_EnergyFilter/3/50/0/4096` and the gate did not report it; since 2893d09
  `tools/perf_ab.sh` fails when the sides differ.
- Local CI (`ci/run_all.sh`) on f63f5bf: all six presets green (614, 614, 614, 615, 613 and 613
  tests).
