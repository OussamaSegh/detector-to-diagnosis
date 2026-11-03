# minidaq-analysis

The analysis package of *Detector to Diagnosis*, Chapter 31: MDQ-L1 list-mode files read through a
memory map, fits of histograms with uncertainties (Poisson maximum likelihood), rate checks, and
the acquisition quality control report with the provenance of its inputs. It is a tool (TL-33),
not part of the shipped DAQ software. Requirements: SRS-ANA-001 to SRS-ANA-006.

```sh
python3 -m venv .venv && .venv/bin/pip install --no-deps -r analysis/requirements.lock
.venv/bin/pip install --no-deps --no-build-isolation -e analysis   # or: PYTHONPATH=analysis/src
.venv/bin/minidaq-qc RUN.run.json qc-out/        # exit 0 pass, 1 fail, 2 cannot analyze
.venv/bin/python analysis/run_checks.py pytest   # also: mypy, ruff (CTest: analysis.*)
```

| Module | What |
|---|---|
| `listmode` | `ListModeFile` (memory map, block index, `chunks()`), `Run` (a run record and its files) |
| `fitting` | `Histogram`, bin-integrated models, `fit()` (Poisson or Neyman), `fit_photopeak`, `fit_timing` |
| `histograms` | `signed_dt_ps`, crystal pair counts, `RunHistograms` (one pass over a run) |
| `rates` | `check_rate`: constancy and dips |
| `provenance` | dataset manifest (SHA-256), environment record |
| `report`, `plots` | the QC protocol (TOML), `quality_control`, `write_report`, figures |
