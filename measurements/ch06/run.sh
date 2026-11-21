#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Chapter 6 says the out-of-order test exercises the sorter's fault handling "in 10 ms".
# Runs it 20 times in each build given (default: release and debug) and writes the times,
# as GoogleTest reports them, to fault-test.txt here.  Usage: measurements/ch06/run.sh [PRESET...]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
test=AcquisitionService.OutOfOrderSinglesAreAFault
{
  echo "Machine: $(uname -m), $(nproc) CPUs. Test: $test, 20 runs per build."
  echo
  echo "| Build | Times in ms, sorted | Median | Max |"
  echo "|---|---|---:|---:|"
  for preset in "${@:-release debug}"; do
    for p in $preset; do
      bin="$root/build/$p/minidaq/tests/minidaq_unit_tests"
      ms=$("$bin" --gtest_filter="$test" --gtest_repeat=20 | sed -n 's/.*OK \].*(\([0-9]*\) ms)/\1/p' | sort -n)
      list=$(echo $ms | tr ' ' ',' | sed 's/,/, /g')
      median=$(echo "$ms" | sed -n '10,11p' | awk '{s+=$1} END {print s/2}')
      max=$(echo "$ms" | tail -1)
      echo "| $p | $list | $median | $max |"
    done
  done
} > "$here/fault-test.txt"
cat "$here/fault-test.txt"
