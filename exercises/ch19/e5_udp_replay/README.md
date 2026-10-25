# Exercise 19.5 (H, extra): Record a readout link and replay it

**Goal.** Write a tool that records the datagrams a readout board sends and replays them to the
DAQ with the recorded timing, so that a stream seen once (at a site, on a bench, in a failing
run) becomes a test that gives the same result every time. Use it to record a damaged stream from
`minidaq_send` and to show that two replays into `minidaq_server` give identical runs.

**Time.** 3 hours.

**Starter.** `starter/udp_replay.py`: the command line and the MDQ-CAP1 format in the module's
comment; `record()`, `read_capture()` and `replay()` are to do. The tests use the helpers of
MiniDAQ's system tests (`minidaq/tests/system/systest.py`) to start the server and the client,
and need the programs: run them with CTest, which sets `MINIDAQ_APPS`.

**Tasks.**
1. `record(sock, path, idle_s, timeout_s)`: write every datagram with its arrival time, until the
   link has been idle for `idle_s`; fail if nothing arrives.
2. `read_capture(path)`: the records in order; refuse a wrong magic, a truncated record and a time
   that goes backward.
3. `replay(path, host, port, speed)`: send in order, at the recorded gaps scaled by `speed`, or as
   fast as possible at speed 0.

**Acceptance** (`ch19/e5_udp_replay/<variant>/unittest`): a recording reads back in order with the
format specified; damaged captures are refused; recording without a sender fails; replays keep,
halve and drop the gaps; a damaged stream of `minidaq_send` (loss, reordering and duplicates) is
recorded completely, and two replays into the server give the same link counters, sorter counters
and records, with the recorded damage.

Then answer in `NOTES.md`: what does a replay reproduce of the original run, and what does it not?
When would two replays of the same capture give different runs? (The test configures the
sequence tracker's `max_hold_us`: find out why.)
