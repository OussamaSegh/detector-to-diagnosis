#!/usr/bin/env bash
# Runs the gated benchmark set (Chapter 5) and writes one Google Benchmark JSON
# file with every repetition, the input of tools/perf_gate.py.
#   tools/perf_suite.sh out.json [build-dir] [cpu]
# Defaults: build/release, CPU 2. Build first: cmake --build --preset release
set -euo pipefail
out=$1
dir=${2:-build/release}
cpu=${3:-2}
reps=${REPS:-10}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# binary:filter. Keep this list short and stable: every entry costs CI time,
# and renaming one makes the gate report it as missing.
suite=(
  "bm_decode:^BM_DecodePacked/65536$"
  "bm_energy_filter:^BM_EnergyFilter/[13]/50/0/4096$"
  "bm_sort:^BM_SortFunctor/4096/0$"
  "bm_histogram:^BM_HistogramRecord$"
  "bm_pipeline:^BM_Pipeline/4096/64/real_time$"
)
for entry in "${suite[@]}"; do
  bin=${entry%%:*}
  filter=${entry#*:}
  pin=(taskset -c "$cpu")
  [ "$bin" = bm_pipeline ] && pin=()  # five threads: let the scheduler place them
  "${pin[@]}" "$dir/benchmarks/$bin" --benchmark_filter="$filter" --benchmark_repetitions="$reps" \
    --benchmark_out="$tmp/$bin.json" --benchmark_out_format=json >/dev/null 2>"$tmp/$bin.err" \
    || { cat "$tmp/$bin.err" >&2; exit 1; }
done
python3 - "$out" "$tmp"/*.json <<'PY'
import json, sys
out, files = sys.argv[1], sys.argv[2:]
merged = None
for f in files:
    d = json.load(open(f))
    if merged is None:
        merged = {"context": d["context"], "benchmarks": []}
    merged["benchmarks"] += d["benchmarks"]
json.dump(merged, open(out, "w"), indent=1)
PY
echo "wrote $out"
