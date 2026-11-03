# SPDX-License-Identifier: MIT
"""MiniDAQ's calibration procedure (Chapter 26, tool TL-29).

From the singles of a calibration acquisition (a source of 511 keV photons centered in the field of
view), this package finds each crystal's energy curve and channel delay and writes a calibration
table (docs/formats/calibration.md) that minidaq_server applies:

- readout: the packed singles of a words file, as numpy arrays;
- energy: each crystal's photopeak, fitted as a Gaussian on a linear background, and the curve
  from the board's energy code to keV that puts the photopeak at 511 keV;
- timing: each channel's delay, from the time differences of coincident pairs, by least squares;
- table: the table file, with the CRC-32 that the server checks;
- __main__: the procedure, with its acceptance criteria (SRS-CAL-007).

Only numpy, which the book's figures already use: no SciPy or scikit-image.
"""
