#!/usr/bin/env bash
# Chapter 5, "The compiler as a tool": the same benchmarks built five ways.
# Usage: measurements/ch05/flags/run_flags.sh   (from the repository root, takes ~25 min)
# RUN_ONLY=1 skips the builds and only re-runs the benchmarks.
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=measurements/ch05/flags
targets=(bm_decode bm_pipeline bm_energy_filter bm_sort)
filter='BM_DecodePacked/65536|BM_Pipeline/4096/64|BM_EnergyFilter/[01]/50/0/4096|BM_Sort(Lambda|FunctionPointer)/4096/0'

build() {  # name, extra cmake args...
  local name=$1; shift
  local dir=build/flags-$name
  cmake -S . -B "$dir" -G Ninja -DCMAKE_CXX_COMPILER=g++ -DCMAKE_BUILD_TYPE=Release \
        -DFETCHCONTENT_BASE_DIR="$PWD/.deps" -DFETCHCONTENT_UPDATES_DISCONNECTED=ON \
        -DMINIDAQ_BUILD_EXERCISES=OFF "$@" >/dev/null
  cmake --build "$dir" --target "${targets[@]}" >/dev/null
}
run() {  # name, round
  local dir=build/flags-$1
  for t in "${targets[@]}"; do
    local pin=(taskset -c 2)
    [ "$t" = bm_pipeline ] && pin=()  # five threads
    "${pin[@]}" "$dir/benchmarks/$t" --benchmark_filter="$filter" --benchmark_repetitions=5 \
      --benchmark_out="$out/$1-r$2-$t.json" --benchmark_out_format=json >/dev/null
  done
}

if [ "${RUN_ONLY:-0}" != 1 ]; then
build O2      -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG"
build O3      -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG"
build native  -DCMAKE_CXX_FLAGS_RELEASE="-O2 -march=native -DNDEBUG"
build lto     -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG" -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON
# PGO: instrument, train on the same benchmarks, rebuild with the profile. Both
# steps use the same build directory: GCC finds a profile by the object file's
# path, and a profile that is not found is silently ignored.
prof=$PWD/build/flags-pgo-data
rm -rf "$prof" build/flags-pgo; mkdir -p "$prof"
build pgo -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG -fprofile-generate -fprofile-update=atomic -fprofile-dir=$prof" \
          -DCMAKE_EXE_LINKER_FLAGS="-fprofile-generate"
for t in "${targets[@]}"; do
  build/flags-pgo/benchmarks/$t --benchmark_filter="$filter" --benchmark_min_time=0.2s >/dev/null
done
cmake -S . -B build/flags-pgo -DCMAKE_EXE_LINKER_FLAGS="" \
      -DCMAKE_CXX_FLAGS_RELEASE="-O2 -DNDEBUG -fprofile-use -fprofile-partial-training -fprofile-dir=$prof -Wno-error=missing-profile" >/dev/null
cmake --build build/flags-pgo --target "${targets[@]}" > "$out/pgo-build.log" 2>&1
echo "PGO: $(grep -c 'missing-profile' "$out/pgo-build.log" || true) translation units without a profile"
fi

# Two rounds, interleaved, so that drift of the machine affects every variant alike.
for r in 1 2; do
  for v in O2 O3 native lto pgo; do run "$v" "$r"; done
done
python3 "$out/summarize.py" "$out" > "$out/summary.md"
cat "$out/summary.md"
