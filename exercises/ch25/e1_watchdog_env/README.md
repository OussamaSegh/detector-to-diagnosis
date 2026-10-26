# Exercise 25.1 (E): What systemd asks of a service

**Goal.** Read the watchdog settings that systemd gives a service in its environment, and split the
notification messages a service sends back into their assignments. Both are small, and both are
where a service quietly goes wrong: a watchdog that is never pinged because a value was misread
restarts a healthy server every few seconds, and one that is pinged when it was meant for another
process protects nothing.

**Time.** 30 minutes.

**Starter.** `starter/watchdog_env.hpp` and `.cpp`.

**Tasks.** `watchdog_settings` and `parse_notification`, as the header's comments say.

**Acceptance** (`ch25/e1_watchdog_env/<variant>/...`): no variable, a valid interval and its ping
period, a watchdog meant for another process, malformed numbers of both variables, and messages with
empty values, equals signs, empty lines and keys that are not keys.

**Then** answer in `NOTES.md`: why does a service ping at half the interval rather than just before
the interval ends, and why should a malformed WATCHDOG_USEC stop the service from starting instead
of being treated as "no watchdog"?
