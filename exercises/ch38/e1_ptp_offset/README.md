# Exercise 38.1 (E): A clock's offset from four time stamps

**Goal.** Compute a slave clock's offset and the path delay from one exchange of the Precision
Time Protocol (IEEE 1588), and estimate the offset from many exchanges whose delays include
queueing in network switches.

**Time.** 1 hour.

**What to write** (`ptp.py`):
- `offset_and_delay(t1, t2, t3, t4)`: the master sends Sync at t1 (master time), the slave
  receives it at t2 (slave time), sends Delay_Req at t3 (slave time), and the master receives it
  at t4 (master time). Return `(offset, delay)`, the slave's time minus the master's and the one-way
  delay, assuming the path takes as long in both directions.
- `estimate(exchanges)`: the offset from a list of such exchanges. Queueing only ever adds to a
  delay, and it is different in the two directions; the exchanges with the shortest round trip
  met the least of it.

**Starter.** `starter/ptp.py` takes `t2 - t1` as the offset, which includes the path's delay,
and averages every exchange.

**Acceptance** (`tests/test_ptp.py`):
- A symmetric path gives the offset and the delay exactly; an asymmetric path errs by half the
  asymmetry; the slave's turnaround time does not matter.
- From 1,000 exchanges with exponential queueing of 5 us on average in each direction, one in ten
  without queueing, the estimate is within 5 ns of the truth.

**Then, by hand.**
1. Why can no protocol that only exchanges messages measure the asymmetry of a path?
2. A PTP exchange over a cable of 100 m and one of 80 m (out and back on different fibers) has
   what offset error?
3. What does hardware time stamping in the network card change in this exercise, and what does
   a transparent clock in a switch change?
