#!/usr/bin/env bash
# The release checks of SDP section 6 that are not run on every change, in order, on one commit:
# all presets, static analysis, starters, the stress run, the performance requirements and the
# regression gate, and 10 minutes of fuzzing per target. Run it on the reference machine, quiet,
# from a clean checkout. Each check writes its output to OUT; the release record cites the files.
#
#   tools/release_checks.sh OUT [FUZZ_SECONDS]
#
# The exit status is 0 only if every check passed (CAPA-0004: a check that cannot run fails).
set -uo pipefail
out=${1:?usage: tools/release_checks.sh OUT [FUZZ_SECONDS]}
fuzz_seconds=${2:-600}
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
mkdir -p "$out/fuzz"
out=$(cd "$out" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
failed=()
stamp() { echo "# $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD) $*"; }
check() {  # name status
  if [ "$2" -eq 0 ]; then echo "pass  $1"; else echo "FAIL  $1"; failed+=("$1"); fi
}

{ echo "commit $(git rev-parse HEAD)"; git status --porcelain; } > "$out/commit.txt"
if [ -n "$(git status --porcelain)" ]; then
  echo "the working tree is not clean; the release checks need one commit" >&2
  exit 2
fi

{ stamp "ci/run_all.sh (all six presets)"; ci/run_all.sh; } > "$out/run_all.txt" 2>&1
check "build and tests, six presets" $?

{ stamp "tools/static_analysis.sh build/clang-release"
  tools/static_analysis.sh build/clang-release; } > "$out/static-analysis.txt" 2>&1
check "static analysis" $?

listed='^[[:space:]]*[0-9]+ - .*\(.*\)$'  # a test in ctest's lists of failed and skipped tests
{ stamp "starters: ctest -L starter (every starter fails at least one test, none hangs)"
  cmake -S . -B build/starters -DCMAKE_BUILD_TYPE=Release -DMINIDAQ_BUILD_STARTERS=ON \
    -DMINIDAQ_BUILD_EXERCISES=ON >/dev/null &&
    cmake --build build/starters -j"$(nproc)" >/dev/null &&
    ctest --test-dir build/starters -L starter --timeout 60 2>&1 |
      grep -E "tests passed|tests failed|$listed"; } > "$out/starters.txt" 2>&1
# A test is named <chapter>/<exercise>/starter/<case>; each starter must have a failed case.
# Release build: the speed tests, the only failing tests of some starters, skip without it.
ctest --test-dir build/starters -L starter -N | sed -n 's|.*Test *#[0-9]*: \(.*/starter\)/.*|\1|p' |
  sort -u > "$work/starters"
grep -vE "\((Skipped|Not Run|Timeout)\)$" "$out/starters.txt" |
  sed -n 's|^[[:space:]]*[0-9]* - \(.*/starter\)/.* (.*)$|\1|p' | sort -u > "$work/failing"
comm -23 "$work/starters" "$work/failing" | sed 's/^/passes every test: /' >> "$out/starters.txt"
[ -s "$work/starters" ] && ! grep -qE "\(Timeout\)$|^passes every test" "$out/starters.txt"
check "starters fail" $?

tools/stress_tests.sh build/tsan 100 "$out/stress-tsan.txt"
check "stress run, tsan, 100 repetitions" $?

# Chapter 18: every property with 100 times its cases, from the clang-release build of run_all.
{ stamp "property-based tests, MINIDAQ_PROP_CASES=100"
  MINIDAQ_PROP_CASES=100 build/clang-release/minidaq/tests/minidaq_unit_tests \
    --gtest_filter='Properties.*'
} > "$out/properties-wide.txt" 2>&1
check "property-based tests, wide search" $?

# Chapter 18: structural coverage per software item; the review of the class B items' uncovered
# branches is written into the release record from coverage/summary.txt and the --uncovered lists.
{ cmake --preset coverage -DMINIDAQ_BUILD_STARTERS=ON >/dev/null &&
    cmake --build --preset coverage -j"$(nproc)" >/dev/null &&
    python3 tools/coverage.py build/coverage "$out/coverage"; } > "$out/coverage.txt" 2>&1
check "coverage report" $?
# Exercise 18.3 measures coverage, so it exists only in this build: its solution must pass there
# and its starter fail.
{ stamp "Exercise 18.3 in the coverage build"
  ctest --test-dir build/coverage -R '^ch18/e3_branch_coverage/solution/' --output-on-failure &&
    ! ctest --test-dir build/coverage -R '^ch18/e3_branch_coverage/starter/'; } > "$out/coverage-exercise.txt" 2>&1
check "Exercise 18.3, solution passes and starter fails" $?

{ stamp "hardened bm_pipeline, 5 repetitions (SRS-PERF-020)"; nproc
  build/hardened/benchmarks/bm_pipeline --benchmark_filter='BM_Pipeline/4096/64/real_time' \
    --benchmark_repetitions=5 2>&1; } > "$out/perf-pipeline.txt"
check "pipeline benchmark ran" $?

mkdir -p /var/tmp/minidaq-bench
{ stamp "hardened writer_throughput, fsync=close, 200 M coincidences, 3 runs (SRS-PERF-021)"
  status=0
  for _ in 1 2 3; do
    build/hardened/benchmarks/writer_throughput --dir /var/tmp/minidaq-bench \
      --coincidences 200000000 --fsync close 2>&1 || status=1
    rm -f /var/tmp/minidaq-bench/*
  done
  exit $status; } > "$out/perf-writer.txt"
check "writer benchmark ran" $?

# The regression gate. It used to run only in perf.yml, on a runner that did not exist
# (MDQ-PR-014); here it runs on the reference machine, and a failure fails the release checks.
{ cmake --preset release >/dev/null && cmake --build --preset release -j"$(nproc)" >/dev/null &&
  tools/perf_suite.sh "$out/perf-current.json" build/release 2; } > "$out/perf-suite.txt" 2>&1 &&
  python3 tools/perf_gate.py benchmarks/baseline/book-vm.json "$out/perf-current.json" --strict \
    > "$out/perf-gate.txt" 2>&1
check "performance regression gate" $?

cmake --preset fuzz >/dev/null &&
  cmake --build --preset fuzz -j"$(nproc)" > "$out/fuzz/build.txt" 2>&1
check "fuzz build" $?
new_cov='^#[0-9]+[[:space:]]+NEW[[:space:]]+cov'
run_fuzz() {  # target cpu
  local t=$1 cpu=$2 dir=$work/$1
  mkdir -p "$dir"
  { stamp "fuzz_$t $fuzz_seconds s on CPU $cpu from fuzz/corpus/$t"
    taskset -c "$cpu" build/fuzz/fuzz/fuzz_"$t" -max_total_time="$fuzz_seconds" -timeout=5 \
      -rss_limit_mb=2048 -print_final_stats=1 -artifact_prefix="$dir/" "$dir" \
      fuzz/corpus/"$t" 2>&1 |
      grep -E "INITED|DONE|stat::|ERROR|SUMMARY|crash-|Seed:|deadly|leak|timeout|$new_cov" |
      awk '/NEW/{if ($4!=last) {print; last=$4}; next} {print}'
    echo "crash files: $(ls "$dir"/crash-* "$dir"/leak-* "$dir"/timeout-* 2>/dev/null | wc -l)"
  } > "$out/fuzz/$t.txt"
}
targets=(config decoder raw16 protocol packet sorter listmode)
cpus=$(nproc)
i=0
while [ $i -lt ${#targets[@]} ]; do  # two targets at a time, each on its own CPU
  run_fuzz "${targets[$i]}" $((cpus > 2 ? 2 : 0)) & a=$!
  b=
  if [ $((i + 1)) -lt ${#targets[@]} ]; then
    run_fuzz "${targets[$((i + 1))]}" $((cpus - 1)) & b=$!
  fi
  wait $a; [ -n "$b" ] && wait $b
  i=$((i + 2))
done
for t in "${targets[@]}"; do
  grep -q "^crash files: 0$" "$out/fuzz/$t.txt" && grep -q "DONE" "$out/fuzz/$t.txt"
  check "fuzz_$t, $fuzz_seconds s" $?
done

echo "The pipeline and writer results are read against SRS-PERF-020 and SRS-PERF-021 by hand."
if [ ${#failed[@]} -gt 0 ]; then
  echo "${#failed[@]} release checks failed" >&2
  exit 1
fi
echo "all release checks passed"
