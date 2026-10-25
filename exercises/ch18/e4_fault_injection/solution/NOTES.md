# Exercise 18.4: notes on the solution

`read()` limits each read of the inner port to the words left before the fault, so the fault
lands exactly at N words whatever the read size; once faulted it returns 0 without calling the
inner port, which is what a device that has stopped does. State that only the source thread
touches (`reads_`, `seen_`) is plain; what the monitor thread reads (`delivered_`, `dropped_`,
`faulted_`) is atomic.

The counter is named `rejected_injected`. `assess_integrity` treats a detector counter as a loss
only if it is `packets_lost`, `sequence_resyncs` or starts with `rejected_`; a counter named
`injected_drops` would be reported in the status and ignored by the verdict, and the run with
dropped words would be called complete. The last test catches that. It is also a review
question for every new adapter: does its loss counter reach the verdict?

A decorator keeps the real data path (the simulator's words, the real pipeline) and scripts
only the failure, so the test checks the behavior around a realistic stream. A fake that makes
everything up is simpler when the data does not matter. A mock with expectations (GoogleMock's
`EXPECT_CALL`) fits when the test is about the interaction itself: that `close()` is called
exactly once, after the last `write()`, for example. Mocks check how the code talks to a port;
fakes and decorators check what the code does with what the port says.
