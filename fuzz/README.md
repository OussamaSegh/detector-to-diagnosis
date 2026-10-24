# Fuzz targets

libFuzzer targets for every MiniDAQ function that reads bytes or text from outside
the process (Chapter 7).

| Target | Code under test | Properties checked besides "no crash" |
|---|---|---|
| `fuzz_decoder` | `packed::StreamDecoder` | every word accounted for; decoded singles in range and re-encode to the same word; chunked `decode_bytes` equals one `decode` |
| `fuzz_raw16` | 16-byte raw format | serialize round trip |
| `fuzz_config` | `config::parse_config` | a rejection always has an error; an accepted configuration survives `to_json` and `parse_config` unchanged and converts to a pipeline configuration |
| `fuzz_protocol` | `LineFramer` and `handle_request` | every response is one line of JSON with `api` and a boolean `ok` |
| `fuzz_packet` | `readout::parse_packet` and `SequenceTracker` (Chapter 9) | accepted packets re-encode to the same bytes; every packet offered is delivered or stale; delivered sequence numbers increase by at most the maximum gap between resyncs; delivered words match |
| `fuzz_sorter` | `CoincidenceSorter` and `StreamMerger` (Chapter 10) | output and counters independent of how the input is split; every single in exactly one window (fixed mode); prompts within the window, delayed pairs within [delay, delay + window], every pair good; merging boards gives back the input times in order, nothing late |

## Build and run

```
cmake --preset fuzz && cmake --build --preset fuzz
ctest --preset fuzz -L fuzz                         # 20 s per target from the seeds
mkdir -p /tmp/corpus-decoder
build/fuzz/fuzz/fuzz_decoder -max_total_time=3600 -timeout=5 -rss_limit_mb=2048 \
    -print_final_stats=1 -artifact_prefix=/tmp/ /tmp/corpus-decoder fuzz/corpus/decoder
```

The first directory is the working corpus (grows), the second the seeds (read only).
Seeds live in `fuzz/corpus/<target>/`; add every crash input there, minimized
(`-minimize_crash=1 -runs=10000 CRASH_FILE`), together with a unit test.

## Campaigns

Clang 18.1.3, `-fsanitize=fuzzer,address,undefined`, `-timeout=5 -rss_limit_mb=2048`,
starting from `corpus/<target>/`, on the book's 4-vCPU VM (2026-10-24, tag `ch07`). The
decoder and protocol runs were in parallel, each pinned to its own vCPU. Log summaries:
`measurements/ch07/fuzz/`.

| Target | Time | Executions | Per second | Coverage, start to end | Last new coverage | Corpus at end | Crashes |
|---|---|---|---|---|---|---|---|
| `fuzz_config` | 30 min | 13,457,603 | 7,472 | 976 to 1,756 | at 13.1 M executions | 2,222 inputs, 503 KB | 0 |
| `fuzz_decoder` | 60 min | 102,580,804 | 28,486 | 83 to 101 | at 7,755 executions | 85 inputs, 25 KB | 0 |
| `fuzz_protocol` | 60 min | 3,432,666 | 953 | 1,468 to 2,412 | at 3.3 M executions | 3,605 inputs, 635 KB | 0 |
| `fuzz_sorter` (Chapter 10, own run, `measurements/ch10/fuzz_sorter.txt`) | 10 min | 3,874,747 | 6,447 | 282 to 313 | at 845,905 executions | 321 inputs, 63 KB | 0 |

The `6e688` crash in the Findings table below was found by a 20-second smoke run of the
configuration target, before the fix; these campaigns ran after it.

## Findings

| Date | Target | Input | Defect | Fix |
|---|---|---|---|---|
| 2026-10-24 | `fuzz_config` (20 s smoke run) | `6e688` (`corpus/config/regress-number-overflow`) | `json::out_of_range` escaped `parse_config` and terminated the program | catch `json::exception`; test `Config.NumberOverflowIsAnErrorNotACrash` |
| 2026-10-24 | `fuzz_packet` (first 2-minute run, after about 240,000 executions) | a sequence number 2^31 ahead (`corpus/packet/crash-jump-2pow31`) | the tracker counted a jump into the undefined half of serial arithmetic as two billion lost packets, and then delivered out of sequence order | a jump beyond `max_gap_packets` (2^24) is a resync; test `SequenceTracker.AJumpBeyondTheMaximumGapIsARestart`; 3.7 M executions clean after the fix |
