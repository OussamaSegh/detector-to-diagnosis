# Exercise 14.1: notes

**Moving the audit log into its own process.**

- Gain: the audit log could be developed and verified as class A, with less documentation
  for its units; a crash or a memory error in it could no longer corrupt the pipeline.
- Cost: an interprocess interface (a pipe or a socket), its own failure modes (the log
  process is gone, the pipe is full: does the server block, drop records or stop?), a second
  program to start, monitor and release, and integration tests for the interface. For a
  small item the cost of the segregation is larger than the documentation it saves.
- The argument would have to show that no failure of the log process can affect the server:
  the server never blocks on it (bounded, non-blocking writes, with a counted loss of
  records), it validates nothing the log returns, and the operating system's process
  isolation separates their memory. The audit trail's own requirement (who did what) would
  still need verification, at class A.
- MiniDAQ keeps the log in the server at class B: the extra activities for B are small, and
  the audit trail is evidence that a reviewer wants to trust.
