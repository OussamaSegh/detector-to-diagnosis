# Exercise 38.1: notes

The starter fails four of the five tests: its offset includes the path's delay, its delay is
always 0, and its average over all exchanges is pulled by the queueing (by microseconds, against
a tolerance of 5 ns). The turnaround test passes by accident: the starter never uses t3.

Design choices:

- Two equations in two unknowns: t2 - t1 = delay + offset and t4 - t3 = delay - offset. Half
  their difference is the offset and half their sum the delay. The derivation assumes the same
  delay both ways; whatever the paths differ by, half of it goes into the offset, and no exchange
  of messages can tell.
- Queueing only adds, and adds differently in each direction. An average keeps that asymmetry;
  the exchanges with the shortest round trip are the ones that met none. Linuxptp and most
  clients filter the delay in a similar way (a minimum or a median over a window).
- `keep=0.1` takes the fastest tenth. A smaller share is closer to the minimum and noisier; one
  exchange alone is the minimum filter.
