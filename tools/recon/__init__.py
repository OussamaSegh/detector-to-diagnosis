# SPDX-License-Identifier: MIT
"""MiniDAQ's data, after the acquisition: corrections (Chapter 27), reconstruction (Chapters 28
and 29) and image quality (Chapter 30).

The corrections are tool TL-30, the rest tool TL-31. The package reads what MiniDAQ writes and
computes what turns counts into activity; it is a teaching implementation, checked against the
simulator's truth, not a clinical reconstruction:

- listmode: the coincidences of MDQ-L1 list-mode files and their run record, as numpy arrays;
- sinogram: the scanner geometry and MiniDAQ's SSRB sinograms (Interfile header and raw data),
  and which crystals each sinogram bin joins;
- corrections, chain: normalization from a cylinder scan, randoms from the singles, attenuation
  of a water cylinder, scatter by tail fitting, dead time and decay;
- project, mlem: the Joseph projector (numpy, or C++ through the module recon_cpp) and OSEM with
  the corrections in the model;
- fbp, quality: filtered backprojection, and the figures of merit of an image.

Only numpy, as for tools/calib: no SciPy, scikit-image or a reconstruction toolkit.
"""
