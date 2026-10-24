# Exercise 6.4: notes on the reference solution

- **Consume by index, compact rarely.** `next()` advances `start_`; `feed()` drops the
  consumed prefix only when it is at least half the buffer. Each byte is then moved at most
  a constant number of times on average, so the cost is linear. On the book's machine
  (`release`), the whole test, including building 7.5 MB of input, takes about 0.1 s. A version that erases each frame from the front took 2.5 s for 200,000 frames at
  `-O2`, and did not finish the test's two runs within the 30 s watchdog: 4x the frames cost
  16x the time.
- **Check the length first.** A peer (or a corrupted packet) that announces 4 GiB must not
  make you allocate or wait for 4 GiB. The header alone decides, and the reader fails at
  once.
- **Failure is permanent.** After an impossible length, the next frame boundary is unknown;
  any byte could be the start of a header. Close the connection. `LineFramer` makes the same
  choice for overlong lines.
- **Big-endian by hand.** Building the value from bytes with shifts is portable and has no
  alignment or aliasing questions; `ntohl` on a `memcpy`'d value is equivalent.
- **Next step.** This reader is the shape of a fuzz target: a function that takes arbitrary
  bytes. Chapter 7 fuzzes MiniDAQ's parsers exactly this way.
