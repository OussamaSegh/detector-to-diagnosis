# Exercise 25.1: notes on the solution

**Digits only.** `std::stoll` accepts a sign, leading spaces and trailing text ("5s" is 5), and
throws on overflow; `from_chars` stops at the first character it cannot use. Checking that every
character is a digit first, then that `from_chars` used all of them, leaves exactly the values
systemd writes. Zero is not an interval: a watchdog that must be pinged every 0 microseconds cannot
be satisfied.

**Another process.** systemd sets WATCHDOG_PID when the main process is not the one it started (a
wrapper that forks), and the variable is inherited by every child. A child that pinged would keep
the service alive while the process systemd watches was hung, so a mismatch turns the watchdog off
for this process, which is what sd_watchdog_enabled(3) does.

**Half the interval.** A ping is a datagram to a socket, sent by a thread that the scheduler may
delay; systemd may also read it late under load. Pinging at half the interval leaves a whole
half-interval of margin for both, so a lost or late ping is followed by another before the deadline.
MiniDAQ uses the same rule (`control/service_manager.cpp`).

**Invalid stops the start.** A malformed value means that the unit and the program disagree about
the protocol: a typo in a drop-in file, or a version of systemd the software was not verified with.
Treating it as "no watchdog" would run the system without one of its risk controls and without
anyone knowing; refusing to start makes the disagreement visible at installation, where it is cheap.
MiniDAQ's server refuses to start when `from_environment` returns an error.

**Notification messages.** The format is newline-separated `KEY=VALUE` assignments in one datagram.
The value runs to the end of the line, so it may hold `=`; the key may not be empty or lowercase. A
manager that parsed `READY` without `=1` as readiness would accept a garbled message.
