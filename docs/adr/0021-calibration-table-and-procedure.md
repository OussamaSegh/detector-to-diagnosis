# 0021. A calibration table per scanner, applied by the server, made by a Python procedure with acceptance criteria

Date: 2026-11-03
Status: Accepted

## Context

Until Chapter 26, MiniDAQ took the board's energy code times 0.5 keV as the energy and the board's
time as the time. A real detector is not that uniform: each crystal and its SiPM have their own
gain (spread by about 10%), the SiPM saturates as more of its cells fire, so the response bends at
high energies, and each timing channel has its own delay (cables, electronics, hundreds of ps).
Uncalibrated, the energy window keeps a different share of each crystal's events, the summed
photopeak is twice as wide as one crystal's (19.4% FWHM against 10.8%, measurements/ch26), and true
coincidences fall outside the coincidence window. Three questions:

- where the correction is applied: on the board, in the server, or later, on the list-mode data;
- what the correction is, and how it is stored and protected;
- how it is made, and what keeps a bad one from being used.

## Options

Where:

1. **On the boards.** The firmware applies a lookup table per crystal. No cost on the PC; the
   table becomes part of the firmware contract (ICD-FEB), and changes need the firmware team.
2. **In the server's decode stage.** One multiply-add per single on the PC, measured as no
   visible cost (about 30 M singles/s with and without, BM_Pipeline); the table is a file that
   the server checks and the run record names.
3. **After the acquisition**, on the list-mode data. The sorter would then use uncalibrated
   energies and times for the energy window and the coincidence window, which is exactly what is
   wrong.

The model: a lookup table of energy per code per crystal (18,432 times 2,048 floats, 150 MB), or
a curve with few coefficients. The protection: none, a CRC, or a signature.

How it is made: in C++ in the server, or as a separate procedure in Python with numpy.

## Decision

Option 2. The model is a quadratic `E = a + b c + q c^2` per crystal and a delay per channel,
stored in a JSON file of about 1 MB ([format](../formats/calibration.md)), sealed by a CRC-32 of
its coefficients, tied to a scanner serial and an expiry date.

- The quadratic is fitted over 200 to 700 keV, where the energy window and the scatter just below
  it are, and is within 0.5% of the exact inverse of the saturation there (E_sat 1500 keV). A
  lookup table would be exact and a hundred times larger; three coefficients are easy to check
  against the limits of a working detector, and a curve that is wrong is visible.
- The sort stage holds back as many singles as the spread of the delays, so that the time
  correction cannot make a single late (SRS-CAL-003).
- A CRC, not a signature: the table protects against damage and editing by hand; its authenticity
  rests on the permissions of the configuration directory, as the configuration's does. A
  signature would need a key at every site that calibrates (assumption: confirm with team).
  SHA-256 was considered and dropped because the application layer does not use OpenSSL
  (layers.json).
- The procedure is a Python package, `tools/calib`, with numpy only: no SciPy or scikit-image,
  which would be new SOUP for a tool that makes part of the product (TL-29, class T3). It fits
  each crystal's photopeak, fits the curve, and solves the delays by least squares on the graph
  of coincident pairs, by conjugate gradients, with the pairs that random coincidences make set
  aside. It writes the table only if every acceptance criterion passes, including the server's
  own limits (SRS-CAL-007).
- The source is a uniform cylinder centred in the ring. A centred point source pairs each crystal
  only with the few crystals opposite it: the delays come out 130 ps rms wrong. The criterion on
  each crystal's distinct partners refuses it.
- The server monitors each block's mean photopeak energy during a run and names the blocks that
  drift beyond a tolerance (2% by default, SRS-CAL-006): the table is checked against the data it
  calibrates, every run.

## Consequences

- The run record and the list-mode metadata name the table (id, version, scanner, creation time,
  CRC), so a table found wrong later identifies the runs it affected (H-11, RC-38).
- The procedure's results depend on inputs that no criterion checks: the sensor's saturation
  energy, given on the command line from the bench, and the source's position. A wrong one gives
  a table that passes. The daily quality control with a phantom remains the control for those
  (H-11, residual).
- Calibrating needs about 30 M singles: 3 s at 20 MBq in the simulation, minutes with a real
  source of a few MBq. The procedure takes about 40 s and 3 GB of memory for that, on the book's
  machine.
- The curvature limit is asymmetric: the first version allowed 40% each way, and the first table
  of a detector with a saturating SiPM was refused by the server. The tool now checks the server's
  limits before it writes, and a test checks both have the same.
- The table is per crystal; a board that identifies crystals by position (a flood map and a
  crystal lookup table) needs another calibration step, which Exercise 26.2 sketches.
