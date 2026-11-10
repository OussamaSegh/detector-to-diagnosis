# Chapter 3: concurrency benchmarks

The tables of Chapter 3 were measured when the chapter was written (tag `ch03`) and those first
runs were not kept. This directory holds a rerun of the same benchmarks, built from tag `ch03`
with the release preset, on the same kind of machine: a 4 vCPU cloud VM on an Intel Xeon
(reported at 2.1 GHz), GCC 13.3, `-O2`, 2026-11-10. `bm_spsc` ran ten repetitions and
`bm_pipeline` five, as in the chapter.

```bash
git worktree add /tmp/ch03 ch03 && cd /tmp/ch03
cmake --preset release && cmake --build build/release --target bm_spsc bm_pipeline
measurements/ch03/run.sh /tmp/ch03/build/release      # from the main tree; writes bm_*.json here
```

Book value against the rerun, millions of items (or words) per second, min / median / max:

| Variant | Book | Rerun |
|---|---|---|
| `std::mutex` + `std::deque` | 4.9 / 5.2 / 5.6 | 4.7 / 5.2 / 5.6 |
| Ring, `seq_cst`, no cached indices | 5.5 / 7.1 / 7.6 | 5.9 / 6.3 / 6.7 |
| Ring, acquire/release, no cached indices | 36.4 / 61.7 / 140.4 | 47.6 / 68.7 / 92.4 |
| `SpscRing` (cached indices) | 39.8 / 51.6 / 63.7 | 52.2 / 62.5 / 127.2 |
| `MpmcQueue`, one producer and one consumer | 25.7 / 28.7 / 35.0 | 26.7 / 39.0 / 49.8 |
| `SpscRing`, batches of 16 | 142.3 / 159.0 / 227.6 | 196.8 / 224.0 / 248.0 |
| `SpscRing`, batches of 256 | 363.7 / 386.8 / 462.7 | 333.3 / 350.3 / 400.5 |
| Pipeline, batch 64, 64 per channel | 40.1 / 42.6 / 43.6 | 37.4 / 38.1 / 40.7 |
| Pipeline, batch 512, 64 per channel | 45.5 / 47.3 / 48.3 | 43.9 / 45.9 / 47.5 |
| Pipeline, batch 4,096, 64 per channel | 32.6 / 33.1 / 33.7 | 25.6 / 28.7 / 30.4 |
| Pipeline, batch 4,096, 8 per channel | 34.4 (one run) | 33.3 / 33.6 / 35.7 |

The chapter's three robust conclusions hold: acquire/release is about ten times the `seq_cst`
ring, batching is the biggest lever, and the multi-producer queue costs against the SPSC ring.
So does what it calls unanswered: the two acquire/release rings overlap, with the cached one
ahead this time. The pipeline is again fastest at 512 and slowest at 4,096 with 64 batches per
channel, where the sort stage limits it.
