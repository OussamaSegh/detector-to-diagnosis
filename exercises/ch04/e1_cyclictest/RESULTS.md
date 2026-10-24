# Exercise 4.1 results

Machine (CPU model, cores, virtualized or not):
Kernel (`uname -a`; PREEMPT_RT or not):
Clock source (`cat /sys/devices/system/clocksource/clocksource0/current_clocksource`):
Load used:

| Run        | samples | min | p50 | p99 | p99.9 | p99.99 | max | overflows |
|------------|---------|-----|-----|-----|-------|--------|-----|-----------|
| idle_other |         |     |     |     |       |        |     |           |
| idle_fifo  |         |     |     |     |       |        |     |           |
| load_other |         |     |     |     |       |        |     |           |
| load_fifo  |         |     |     |     |       |        |     |           |

All values in microseconds. Policies confirmed with `chrt -p` (paste one line per run):

What surprised you:
