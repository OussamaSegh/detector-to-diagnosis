# Exercise 3.3 (H): A four-stage pipeline that reports on itself

**Goal.** Build `ex::run_pipeline()`: four threads (decode, sort, pair, write) connected by
bounded queues, processing a buffer of MDQ-P1 words into coincidences. Every stage reports
items in, items out, items dropped and busy time, so you can see which stage limits
throughput and where data was lost.

**Time.** 4 to 6 hours.

**Specification.**
- *Decode* reads `batch_size` words at a time from the input span (it plays the role of the
  network receiver) and decodes them with `minidaq::packed::StreamDecoder`. Invalid words are
  removed and counted as `filtered`. If its output queue is full: with `Overflow::block` it waits; with
  `Overflow::drop` it drops the whole batch of words and counts them as `dropped`.
- *Sort* sorts each batch with `minidaq::time_order` (time, then crystal).
- *Pair* walks the sorted stream and pairs consecutive singles whose time difference is at most
  `window`; a paired single is not reused; an unpaired single is carried to the next batch.
  A single that finds no partner (including the last one of the run) counts as `filtered`.
- *Write* calls `on_write` for each batch of coincidences (after an optional `write_delay`, to
  simulate a slow disk) and appends them to the result.
- Queues are bounded (`queue_batches` batches of `batch_size` items) and nothing is allocated
  per batch after start-up. Stages after decode never drop.
- Conservation. Decode: `in == out + dropped + filtered`. Sort and write: `in == out`.
  Pair: `in == 2 * out + filtered`. Between stages: `next.in == previous.out`.
  Keep `dropped` (data lost because the system was too slow) apart from `filtered` (data the
  stage removed by design): they mean very different things in a service report.
- `busy_seconds` is time spent processing, not waiting. `throughput()` is `in / busy_seconds`.

You may use `minidaq::SpscRing`, `minidaq::Channel` and `minidaq::Backoff`, or your ring from
Exercise 3.1.

**Acceptance tests** (`tests/test_pipeline.cpp`):
- With `Overflow::block`, the output equals a single-threaded reference exactly.
- Conservation holds for every stage, with both policies.
- With `Overflow::drop` and a slow writer, drops are counted and `delivered + dropped == input`.
- Busy times are positive and no larger than the run's wall time.
- Runs clean under TSan.

**Then measure.** Print the reports for 8 M words and batch sizes 64, 512 and 4096. Which
stage limits throughput, and why does the answer change with batch size? (The book's
measurement is in Section 3.4.)
