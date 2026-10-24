# Exercise 6.4 (M): Framing a binary protocol

**Goal.** MiniDAQ's control protocol frames messages with newlines (`LineFramer`). Readout
boards and many binary protocols use a length prefix instead. Write the reader for one,
robust against every way a byte stream can be cut, against a hostile length, and against
the quadratic slowdown that most first versions have.

**Time.** 2 hours.

**Specification.** A frame is a 4-byte unsigned length in network byte order (big-endian),
followed by that many payload bytes. `FrameReader(max_payload)`:
- `feed(bytes)` appends received bytes; `next()` returns the next complete payload or
  `nullopt`.
- A header announcing more than `max_payload` bytes makes the reader `failed()` at once,
  before any payload arrives, and permanently: after a bad length nothing can be trusted.
- `buffered()` is the number of bytes received and not yet returned.
- `encode_frame(payload)` builds a frame.

**Acceptance tests** (`tests/test_frame_reader.cpp`): big-endian encoding; one byte at a
time; many frames per read and empty frames; 2,000 random frames through random chunk sizes;
too-large lengths (including 0xFFFFFFFF) detected from the header alone; and decoding
1,000,000 frames from one read takes less than 8 times as long as 250,000 (linear cost).

**Hints.** Removing each consumed frame with `vector::erase(begin(), ...)` moves the rest of
the buffer every time: with many small frames in one read that is quadratic. Consume by
advancing an index and compact occasionally. Why must the length check happen before you
wait for the payload?
