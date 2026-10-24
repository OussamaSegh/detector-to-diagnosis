#!/usr/bin/env bash
# Records a CPU profile of a command with perf and renders a flame graph (Chapter 5).
#
#   tools/flamegraph.sh out.svg build/profile/minidaq/apps/minidaq_latency --seconds 5
#
# Build with the `profile` preset (frame pointers, -g) for complete stacks.
# Environment:
#   PERF            perf binary (default: perf; on Ubuntu with a custom kernel,
#                   /usr/lib/linux-tools-<version>/perf works too)
#   FREQ            sampling frequency in Hz (default 999: not a multiple of the tick)
#   FLAMEGRAPH_DIR  Brendan Gregg's FlameGraph scripts (default .deps/FlameGraph,
#                   cloned at a pinned commit if missing)
#   EVENT           perf event (default cpu-clock: works in VMs without hardware counters)
set -euo pipefail
if [ $# -lt 2 ]; then
  sed -n '2,13p' "$0"; exit 2
fi
out=$1; shift
perf=${PERF:-perf}
freq=${FREQ:-999}
event=${EVENT:-cpu-clock}
fg=${FLAMEGRAPH_DIR:-$(dirname "$0")/../.deps/FlameGraph}
fg_commit=41fee1f99f9276008b7cd112fca19dc3ea84ac32

if [ ! -x "$fg/flamegraph.pl" ]; then
  git clone -q https://github.com/brendangregg/FlameGraph.git "$fg"
  git -C "$fg" checkout -q "$fg_commit"
fi

data=$(mktemp --suffix=.perf.data)
trap 'rm -f "$data"' EXIT
"$perf" record -e "$event" -F "$freq" -g -o "$data" -- "$@"
"$perf" script -i "$data" 2>/dev/null \
  | "$fg/stackcollapse-perf.pl" \
  | tee "${out%.svg}.folded" \
  | "$fg/flamegraph.pl" --title "$(basename "$1") ($event, ${freq} Hz)" --width 1000 > "$out"
echo "wrote $out and ${out%.svg}.folded"
