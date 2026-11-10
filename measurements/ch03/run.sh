#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Chapter 3's benchmarks as Google Benchmark JSON in this directory: bm_spsc with ten
# repetitions, bm_pipeline with five.
# Usage: measurements/ch03/run.sh BUILD_DIR   (a release build of tag ch03)
# Run it on a quiet machine: nothing else may build or test while it runs.
set -euo pipefail
build="${1:?usage: run.sh BUILD_DIR}"
here="$(cd "$(dirname "$0")" && pwd)"
"$build/benchmarks/bm_spsc" --benchmark_repetitions=10 \
  --benchmark_out="$here/bm_spsc.json" --benchmark_out_format=json > /dev/null
"$build/benchmarks/bm_pipeline" --benchmark_repetitions=5 \
  --benchmark_out="$here/bm_pipeline.json" --benchmark_out_format=json > /dev/null
