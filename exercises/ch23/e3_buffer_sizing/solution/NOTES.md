# Exercise 23.3: notes on the solution

**Which rate.** The buffer must hold what arrives while the receiver is not reading, so what
matters is the rate *during the stall*, not the average. A readout board that sends as it measures
produces 4,923 datagrams per second at 2 MBq, and a 4 MiB buffer then covers a stall of 0.74 s. A
board, a switch or a firmware FIFO that holds data and releases it in bursts produces the burst
rate for the length of the burst; at 470,000 datagrams per second the same buffer covers 7.7 ms,
less than one time slice of a busy CPU. Ask the firmware team how the board sends (and whether a
switch in between buffers), size for the burst rate over the longest burst, and add the longest
stall the receiving thread can see (Chapter 4 measured it).

**Why truesize.** The kernel accounts for memory, not for payload: the socket buffer structure and
the allocation the driver made for the frame, which on loopback is a power-of-two size. A 1,472-byte
datagram costing 2,305 bytes is 57% overhead, and an 8,208-byte datagram costing 16,644 bytes
doubles its size, because the allocation rounds up to 16 KiB. Sizing with the payload alone
overestimates the capacity by that much.

**When the request does not fit.** `rmem_max` is a host setting, so the remedy is in the platform
configuration (Chapter 25), recorded with the installation, and checked at start: MiniDAQ reports
the granted size and says when it is smaller than requested (Chapter 9).
