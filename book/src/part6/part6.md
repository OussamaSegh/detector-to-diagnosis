# Part VI: Calibration, corrections and image reconstruction {.part}

Part VI (five chapters) follows the data past the acquisition. Until now MiniDAQ's job ended
with a list-mode file whose coincidences were complete, ordered and checked. Whether they make a
good image depends on what the detector really measured and on what happens to the data next: the
energies and times of uncalibrated crystals, the photons absorbed and scattered in the patient,
the random coincidences, and an algorithm that turns millions of lines of response into an image a
physician reads.

You will not become a reconstruction scientist in five chapters, and the lead of the DAQ software
does not need to be one. You do need to know what each step assumes about the data you deliver,
to read the physicists' code and review it, and to put their Python and your C++ in one tested,
traceable product.

- **Chapter 26** is calibration: each crystal's energy curve and channel delay, a table the server
  applies to every single, the procedure that makes the table from a calibration acquisition, and
  the acceptance criteria that keep a bad table from being used.
- **Chapter 27** is the corrections: normalization, attenuation, scatter, randoms and dead time,
  what each one needs from the acquisition and where each one is computed.
- **Chapter 28** is reconstruction in two dimensions, in Python: the system model, MLEM and OSEM,
  and how to tell a converged image from a noisy one.
- **Chapter 29** moves the projector to C++ and calls it from Python, with one set of tests for
  both sides of the boundary.
- **Chapter 30** is image quality: the NEMA-style measurements of resolution, contrast and noise
  that validation of the whole chain rests on.
