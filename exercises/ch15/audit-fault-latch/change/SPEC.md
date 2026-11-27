# Task given to the agent

Extend `FaultLatch` (`fault_latch.hpp`) so that it implements all of risk control RC-27 of
hazard H-10 ("detector gain drifts with temperature": a board whose bias is not what the
calibration assumes gives wrong energies and times), as far as this class is concerned:

1. **A board that does not answer.** A cycle in which any register access fails, a read or a
   write, is a failed cycle. `max_failed_cycles` failed cycles in a row latch a fault. Only a
   cycle whose every access succeeded ends a run of failed cycles (SRS-HW-004).
2. **Overcurrent.** A measured current above `max_current_ua` latches a fault, and so does the
   board's own overcurrent flag: its comparator is faster than the loop, so the reading of the
   same cycle may be below the limit.
3. **The reason.** The reason is what the operator reads at the console and what the flight
   recorder keeps. It says what happened, and nothing that did not: a trip by the board is
   not a reading above the limit.
4. A fault stays latched until it is acknowledged (SRS-HW-005).

Add tests.
