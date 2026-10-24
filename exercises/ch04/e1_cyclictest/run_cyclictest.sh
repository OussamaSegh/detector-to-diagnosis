#!/usr/bin/env bash
# Exercise 4.1: four cyclictest runs (normal/FIFO x idle/loaded) on CPU 1.
# Needs root (or CAP_SYS_NICE) and the rt-tests and stress-ng packages.
# Usage: ./run_cyclictest.sh [seconds] [outdir]
set -euo pipefail
secs=${1:-30}
out=${2:-cyclictest-results}
mkdir -p "$out"
common=(-m -t1 -a1 -i200 -D"$secs" -h20000 -q)

run() {  # name, policy options...
  local name=$1; shift
  echo "== $name"
  cyclictest "$@" "${common[@]}" > "$out/$name.txt" 2>&1 &
  local pid=$!
  sleep 1
  # Prove which policy the measuring thread really got (see the README).
  for t in /proc/$pid/task/*; do chrt -p "${t##*/}"; done | tee "$out/$name.policy"
  wait $pid
}

run idle_other --policy=other          # no -p: -p0 would silently mean SCHED_FIFO 2
run idle_fifo  --policy=fifo -p80
stress-ng --cpu "$(nproc)" --vm 2 --vm-bytes 256M --io 1 --timeout $((2 * secs + 20))s >/dev/null 2>&1 &
stress=$!
sleep 3
run load_other --policy=other
run load_fifo  --policy=fifo -p80
kill "$stress" 2>/dev/null || true
wait 2>/dev/null || true
echo "Raw outputs are in $out/; parse them with the test binary or your own tool."
