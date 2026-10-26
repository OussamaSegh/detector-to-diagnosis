# Exercise 22.3 (E): Decode a temperature sensor

**Goal.** Decode the registers of a Texas Instruments TMP117 digital temperature sensor as its
datasheet describes them, and refuse the readings that are not temperatures. Many detector boards
carry a sensor like it next to the SiPMs; the slow control's bias is only as good as this decoder.

**Time.** 30 minutes.

**What the datasheet says** (TMP117 datasheet, SNOSD82): the temperature result register `0x00`
holds a 16-bit two's complement number with 7.8125 m°C (1/128 °C) per bit. Following a reset it
reads `0x8000` (−256 °C) until the first conversion is complete. The device ID register `0x0F`
holds the device ID `0x117` in bits 11 to 0 and a revision number in bits 15 to 12. The sensor
operates from −55 °C to +150 °C. An I2C read of a register returns the most significant byte
first.

**Starter.** `starter/tmp117.hpp` and `.cpp`: the declarations, and functions that return
nothing useful.

**Tasks.**
1. `decode_temperature(msb, lsb)`: the temperature in °C, or empty for the reset value and for
   any value outside the operating range.
2. `is_tmp117(msb, lsb)`: whether a device ID register says TMP117, whatever its revision.

**Acceptance** (`ch22/e3_tmp117/<variant>/...`): the values of the tests, which include positive
and negative temperatures, the smallest step, the byte order, the reset value and the revision
bits.
