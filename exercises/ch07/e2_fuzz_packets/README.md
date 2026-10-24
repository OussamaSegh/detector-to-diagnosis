# Exercise 7.2 (M): Fuzz a parser, then fuzz the decoder for an hour

**Goal.** `starter/packet.cpp` parses the header of a readout packet, the
first code a network receiver (Chapter 9) runs on bytes from outside. It passes
a quick read and the happy-path test. Write a libFuzzer target for it, let the
fuzzer find what is wrong, fix every crash, and keep each crash input as a
regression test. Then run MiniDAQ's own decoder fuzzer for one hour and record
what it did.

**Time.** 2 hours, plus the hour of fuzzing (unattended).

**Part 1: the packet parser.**

1. Fill in `starter/fuzz/fuzz_packet.cpp`: parse the input; if it is accepted,
   read every word it claims; for a plain 2-word header, check that
   `encode_packet` of the result gives back the input. Call `std::abort()`
   when a property fails, so that libFuzzer saves the input.
2. Build with the `fuzz` preset and starters on, and run it:

   ```
   cmake --preset fuzz -DMINIDAQ_BUILD_STARTERS=ON && cmake --build --preset fuzz
   mkdir -p /tmp/packets && build/fuzz/exercises/ch07/ch07_fuzz_packet_starter \
       -artifact_prefix=/tmp/packets/ /tmp/packets exercises/ch07/e2_fuzz_packets/tests/corpus
   ```
3. For each crash: read the AddressSanitizer report, fix `parse_packet`,
   copy the input to `tests/crashers/`, and run the fuzzer again until it runs
   for 10 minutes without a crash.

**Part 2: the decoder.** Run `build/fuzz/fuzz/fuzz_decoder -max_total_time=3600
-print_final_stats=1 CORPUS_DIR fuzz/corpus/decoder` and record in your notes: the
number of executions, executions per second, coverage (`cov:`), the corpus size, and
any crash. Fix any crash found, with a regression test.

**Acceptance.**
- `tests/test_packet.cpp` passes, including every input in `tests/crashers/`.
- The CTest `ch07/e2_fuzz_packets/<variant>/fuzz` (20 s from the seed corpus) passes.
- Your notes for Part 2 give the five numbers above and say what the run does and
  does not show.

**Hints.** How many bytes does the header promise, and how many arrived? Which field
is multiplied by 8, and can the product exceed the packet? What should a reserved
field contain, and why check it?
