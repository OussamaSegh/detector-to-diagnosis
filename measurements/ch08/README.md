# Chapter 8: simulated rates and spectrum

Both files come from `minidaq_sim` with a fixed seed, so they are the same on every machine and
every build of the same code; a change of the simulator that moves them is a change of the
chapter's numbers.

- `rates.txt`, written by `rates.py`: the table "Measured with MiniDAQ's simulator" (trues,
  scatters, randoms and multiples per second, and the scatter fraction, for the energy windows
  100 to 1000 keV and 435 to 650 keV). Rerun on 2026-11-10 at 1.1.1-dev: identical to the table.
- `spectrum.txt`, written by `spectrum.py`: the energy spectrum of Figure "fig-ch08-spectrum".

```bash
cmake --preset release && cmake --build build/release --target minidaq_sim
python3 measurements/ch08/rates.py build/release/minidaq/apps/minidaq_sim > measurements/ch08/rates.txt
python3 measurements/ch08/spectrum.py build/release/minidaq/apps/minidaq_sim > measurements/ch08/spectrum.txt
```

The rows of the table "Simulated quantity / Configured / Measured (test)" are the assertions of
the test `DetectorSimulator.CoincidenceTimeResolution` and its neighbors, run by `ctest`.
