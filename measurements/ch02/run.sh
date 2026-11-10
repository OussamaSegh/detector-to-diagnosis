#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Chapter 2's benchmarks, three repetitions each, as Google Benchmark JSON in this directory.
# Usage: measurements/ch02/run.sh BUILD_DIR   (a release build of tag ch02 or later)
# Run it on a quiet machine: nothing else may build or test while it runs.
set -euo pipefail
build="${1:?usage: run.sh BUILD_DIR}"
here="$(cd "$(dirname "$0")" && pwd)"
for bm in bm_latency bm_layout bm_alloc bm_decode bm_false_sharing; do
  "$build/benchmarks/$bm" --benchmark_repetitions=3 \
    --benchmark_out="$here/$bm.json" --benchmark_out_format=json > /dev/null
done
