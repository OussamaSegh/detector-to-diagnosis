# Chapter 22: the datasheet model, recomputed

Chapter 22 quotes no measurement of a machine. Its numbers are computed from the datasheet of the
SiPM it models (breakdown 38 V at 25 °C, 34 mV/°C, overvoltage 2.7 V), from the temperature
sensor's register format (1/128 °C per bit, two's complement) and from MiniDAQ's configuration (a
5 mV dead band). `model.py` recomputes each of them into `model.txt`:

    python3 measurements/ch22/model.py > measurements/ch22/model.txt

The check found one wrong number: a bias compensated for the sensor's reset value of −256 °C is
281 degrees × 34 mV = 9.55 V too low, which the chapter and Exercise 22.3's notes gave as 9.5 V
(erratum E-010, fixed in 2.1.0). The figure's description said 79 percent of the nominal gain at
41 °C for 79.9. Every other number agrees with the text to the digits it gives.
