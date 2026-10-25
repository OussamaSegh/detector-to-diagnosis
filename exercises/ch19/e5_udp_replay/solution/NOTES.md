# Exercise 19.5: notes on the solution

The recorder times each datagram from the first with the monotonic clock, and stops after the
link has been idle; the receive buffer is raised to 8 MiB so that a Python loop keeps up with a
million singles per second on loopback (the test checks that the recording holds exactly the
datagrams `minidaq_send` sent: its packets, less the ones it dropped, plus its duplicates). The
replayer sleeps until each datagram's deadline from the start, not for each gap, so its errors do
not add up over a long capture.

A replay reproduces what the DAQ received: the payloads, their order, and their gaps to within
the replayer's timing. The server's counters and records are the same in both replays because
everything the server decides depends on the payloads and their order: sequence numbers, time
stamps, energies. What a replay does not reproduce is what the network did on the way. A
datagram the original link lost is not in the capture; the capture is of the receiving side, so
it shows the damage but not its cause; and a replay on loopback does not load the network
interface, its interrupts and its buffers as the real link did (that is what a bench with the
board is for, system test plan section 6).

Two replays can differ when the server's decisions depend on time instead of order: a stage that
drops when a queue is full, a run stopped by duration, or the sequence tracker's hold time. The
tracker gives up a gap either when the reorder window has moved past it (an order) or when the
gap is older than `max_hold_us` (a time, 1 ms by default). A delayed packet that arrives 0.9 ms
after its gap opened is used in one replay and too late in another whose timing differs by a
fraction of a millisecond. The test therefore sets `max_hold_us` to one second, so that the
window decides, replays at speed 1, and compares the replays with each other, not with the
original run. Not every counter describes the data, either: `receive_batches` counts the
server's reads of its socket, which depend on scheduling, so the test leaves it out. At speed 0 the replay can also overrun the receive buffer and lose datagrams that
the original run received.
