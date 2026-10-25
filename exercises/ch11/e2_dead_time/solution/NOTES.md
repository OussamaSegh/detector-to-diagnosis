# Exercise 11.2: notes on the solution

**Which event starts the dead time.** Non-paralyzable: only a recorded event, so the block
is free tau after the event it is processing, whatever arrives meanwhile. Paralyzable:
every event, because the electronics cannot tell a second pulse from the tail of the
first and restart (for example, a pulse that must return below threshold before the
next can be accepted). The starter swapped them, which passes a test at low rate, where
the two models agree to first order: m = n(1 - n tau) for both.

**The boundary.** The dead time is the half-open interval [t, t + tau): an event at
exactly t + tau is recorded. Either convention is defensible; this one matches
`minidaq::sim::DeadTime` and is stated in the header.

**Pile-up.** The lost event's light adds to the pulse being integrated, so its energy is
added to the event the block is recording. A 511 keV event with a 200 keV pile-up becomes
711 keV and leaves a 435 to 585 keV window: at high rates pile-up removes trues from the
energy window and moves scatters into it (`measurements/ch11/countrate.txt`: with a 1 us
block dead time and pile-up the scatter fraction at 100 MBq is 0.40, against 0.33 without).

**Two true rates.** n exp(-n tau) rises to 1 / (e tau) at n = 1 / tau and falls again. Every
lower recorded rate is produced by one true rate on each side of the maximum. An operator
who raises the activity and sees the count rate fall is on the far side: more activity
gives fewer counts, and a dead-time correction that assumes the near side is wrong by a
large factor. Scanners are characterized well beyond the peak (the NEMA count-rate test
does this) so that the operating range is known to be on the near side.
