# SPDX-License-Identifier: MIT
"""MiniDAQ's data, after the acquisition: corrections (Chapter 27) and reconstruction (Chapter 28).

This package is tool TL-30. It reads what MiniDAQ writes and computes what turns counts into
activity; it is a teaching implementation, checked against the simulator's truth, not a clinical
reconstruction:

- listmode: the coincidences of MDQ-L1 list-mode files and their run record, as numpy arrays;
- sinogram: the scanner geometry and MiniDAQ's SSRB sinograms (Interfile header and raw data),
  and which crystals each sinogram bin joins;
- corrections: normalization from a cylinder scan, randoms from the singles, attenuation of a
  water cylinder, scatter by tail fitting, dead time and decay.

Only numpy, as for tools/calib: no SciPy, scikit-image or a reconstruction toolkit.
"""
