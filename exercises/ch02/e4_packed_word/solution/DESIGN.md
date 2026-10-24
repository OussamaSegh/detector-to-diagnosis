# Design of the 64-bit single (MDQ-P1)

| Field | Bits | Range | Resolution | Why |
|---|---|---|---|---|
| crystal | 15 | 0 .. 32,767 | 1 | MiniDAQ has 18,432 crystals; 15 bits leaves 78% headroom for a larger scanner. 14 bits (16,384) would not fit. |
| energy | 11 | 0 .. 1023.5 keV | 0.5 keV | 511 keV photopeak FWHM is about 50 keV; 0.5 keV is 100x finer than needed and leaves range for the 1,275 keV Na-22 line to saturate visibly (and the 202/307 keV Lu-176 lines to be resolved, Chapter 26). |
| coarse | 28 | 0 .. 2^28 - 1 | 5.12 ns | One tick of a 195.3125 MHz clock. assumption: confirm with team. |
| fine | 10 | 0 .. 1023 | 5 ps | TDC interpolation within a tick. Coincidence time resolution of modern SiPM PET is 200 to 500 ps FWHM, so 5 ps is far below the noise. |

**Wrap period.** coarse+fine form one 38-bit counter of 5 ps units, which wraps every
2^38 x 5 ps = 1.374 s. A stream decoder must reconstruct absolute time; the MiniDAQ
`TimeUnwrapper` does it assuming events are time-ordered to within half a period (0.69 s),
and the transport (Chapter 9) adds explicit time markers so a receiver that joins late, or
loses a burst of packets longer than the half period, can resynchronize.

**Alternatives considered.**
- *Absolute 64-bit time in a second word* (16 bytes per single): no wrap logic at all, but
  double the bandwidth and memory traffic (Exercise 2.1).
- *Time relative to a frame header* (as several commercial ASICs do): fewer time bits per
  word, but every word depends on its frame header, so a lost header loses the frame.
- *Energy as raw ADC or time-over-threshold code* instead of calibrated keV: this is what the
  hardware really sends (Chapter 9); MDQ-P1 carries calibrated energy because MiniDAQ uses
  it as its internal and storage format after calibration (Chapter 26).

**Why shifts and masks, not bit-fields.** The order, alignment and padding of C++
bit-fields are implementation-defined, so a `struct { uint64_t crystal : 15; ... }`
does not define a wire format. Shifts and masks act on values and give the same result
on every compiler and every host byte order.
