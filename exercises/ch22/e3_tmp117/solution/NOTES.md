# Exercise 22.3: notes on the solution

**The byte order.** I2C transfers bytes; the TMP117 sends the most significant byte of a register
first. A decoder that takes the two bytes in the order of memory on a little-endian processor reads
25 °C (`0x0C80`) as `0x800C`, about −255.9 °C, which the range check then refuses. Without the
range check it would be a temperature.

**The reset value.** `0x8000` is a valid two's complement number (−256 °C), so nothing in the
arithmetic marks it. It is the datasheet that gives it a meaning: no conversion has completed
since the reset. A slow control that believes it computes a bias for −256 °C, 9.5 V too low for a
34 mV/°C SiPM, or the lowest bias its limits allow. The same holds for every sensor: find the
value it reads before it has measured anything.

**The range.** The sensor cannot report a temperature outside −55 to +150 °C, so such a value is a
defect somewhere between the sensor and the decoder, not a temperature. The slow control has its
own, narrower limits for what it believes of a detector (MiniDAQ: below 5 °C is a fault); the
decoder only knows what the sensor can say.

**The revision bits.** The device ID register holds a revision in its top four bits. Comparing all
16 bits with `0x0117` would reject the next revision of the same part, and a board built with it
would fail its identity check in the field.
