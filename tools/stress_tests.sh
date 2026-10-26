#!/bin/sh
# SPDX-License-Identifier: MIT
# Stress run of the threaded tests (Chapter 16, CAPA-0001): twice as many busy
# loops as CPUs, ctest with 16 jobs, every test repeated until it fails.
# A test that depends on timing fails here long before it fails in CI.
# Usage: tools/stress_tests.sh BUILD_DIR REPEATS OUT [TEST_REGEX]
set -eu
build=$1
n=$2
out=$3
tests=${4:-'(^|/)(Pipeline|AcquisitionService|ControlServer|ControlProtocol|ListModeSink|UdpDetector|PacedSource|ReplaySource)\.'}
hogs=""
for _ in $(seq $((2 * $(nproc)))); do
  sh -c 'while :; do :; done' &
  hogs="$hogs $!"
done
log=$(mktemp)
trap 'kill $hogs 2>/dev/null; rm -f "$log"' EXIT
# The exit status is ctest's: a failed test fails the stress run. It used to be the status of the
# grep that filtered ctest's output, so a failure was written to OUT and the run still passed
# (MDQ-PR-032).
status=0
ctest --test-dir "$build" -R "$tests" -j 16 --repeat until-fail:"$n" --timeout 120 --output-on-failure \
  >"$log" 2>&1 || status=$?
{
  echo "# $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD) build $build"
  echo "# $(nproc) CPUs, $((2 * $(nproc))) busy loops, ctest -j 16 --repeat until-fail:$n -R '$tests'"
  grep -E "tests passed|Failed|Expected|Which is|Value of|Actual" "$log" || true
  echo "# ctest exit status $status"
} >"$out"
exit "$status"
