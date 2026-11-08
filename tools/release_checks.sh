#!/usr/bin/env bash
# The release checks of SDP section 6 that are not run on every change, in order, on one commit:
# all presets, static analysis, starters, the stress run, the performance requirements and the
# regression gate, the system test report, the soak and the end-to-end run, and 10 minutes of
# fuzzing per target.
# Run it on the reference machine, quiet, from a clean checkout. Each check writes its output to
# OUT; the release record cites the files.
#
#   tools/release_checks.sh OUT [FUZZ_SECONDS] [PART]
#
# PART is all (the default) or one of four parts, each under 45 minutes on the reference machine:
# 1 the six presets, static analysis and the starters; 2 the stress run, the wide property
# search, coverage and the benchmarks; 3 the regression gate, the system tests, the soak and the
# end-to-end run; 4 the fuzzing. Run the parts in order, on the same commit and into the same OUT,
# when one session cannot hold the whole run (MDQ-PR-041: a machine that restarts within the
# hour). Parts 2 to 4 use the builds that part 1 made.
#
# The exit status is 0 only if every check passed (CAPA-0004: a check that cannot run fails), and
# 3 if the run stopped before the last check (MDQ-PR-029).
set -uo pipefail
out=${1:?usage: tools/release_checks.sh OUT [FUZZ_SECONDS]}
fuzz_seconds=${2:-600}
part=${3:-all}
case "$part" in all | 1 | 2 | 3 | 4) ;; *) echo "PART is all, 1, 2, 3 or 4" >&2; exit 2 ;; esac
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
mkdir -p "$out/fuzz"
out=$(cd "$out" && pwd)
work=$(mktemp -d)
# A run that ends before the last check fails, whatever ended it (MDQ-PR-029).
finished=no
on_exit() {
  local status=$?
  rm -rf "$work"
  if [ "$finished" != yes ] && [ "$status" -ne 2 ]; then
    echo "FAIL  the release checks stopped before the last check (status $status)"
    exit 3
  fi
}
trap on_exit EXIT
failed=()
in_part() { [ "$part" = all ] || [ "$part" = "$1" ]; }
stamp() { echo "# $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD) $*"; }
# Every result also goes to OUT/release-checks.txt, one section per part, which
# tools/acceptance.py reads (Chapter 33); a part run again appends a new section.
check() {  # name status
  local line
  if [ "$2" -eq 0 ]; then line="pass  $1"; else line="FAIL  $1"; failed+=("$1"); fi
  echo "$line"
  echo "$line" >> "$out/release-checks.txt"
}
summary() {
  finished=yes
  if [ ${#failed[@]} -gt 0 ]; then
    echo "${#failed[@]} release checks failed (part $part)" | tee -a "$out/release-checks.txt" >&2
    exit 1
  fi
  echo "all release checks passed (part $part)" | tee -a "$out/release-checks.txt"
  exit 0
}

commit_file=$out/commit.txt
case "$part" in 2 | 3 | 4) commit_file=$out/commit-part-$part.txt ;; esac
{ echo "commit $(git rev-parse HEAD)"; git status --porcelain; } > "$commit_file"
if [ -n "$(git status --porcelain)" ]; then
  echo "the working tree is not clean; the release checks need one commit" >&2
  exit 2
fi
if [ "$commit_file" != "$out/commit.txt" ] && ! cmp -s "$out/commit.txt" "$commit_file"; then
  echo "part $part must run on the commit of part 1 ($out/commit.txt)" >&2
  exit 2
fi
echo "## part $part" >> "$out/release-checks.txt"

if in_part 1; then
{ stamp "ci/run_all.sh (all six presets)"; ci/run_all.sh; } > "$out/run_all.txt" 2>&1
check "build and tests, six presets" $?

{ stamp "tools/static_analysis.sh build/clang-release"
  tools/static_analysis.sh build/clang-release; } > "$out/static-analysis.txt" 2>&1
check "static analysis" $?

listed='^[[:space:]]*[0-9]+ - .*\(.*\)$'  # a test in ctest's lists of failed and skipped tests
{ stamp "starters: ctest -L starter (every starter fails at least one test, none hangs)"
  # Ninja, as the presets use: Exercise 32.3's tests need its dry run (MDQ-PR-053).
  cmake -S . -B build/starters -G Ninja -DCMAKE_BUILD_TYPE=Release -DMINIDAQ_BUILD_STARTERS=ON \
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
fi
[ "$part" = 1 ] && summary

if in_part 2; then
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
# A subshell, not a { } group: an exit in a group ends the whole script, with status 0, which
# is how the gate, the system tests and the fuzzing never ran after this step (MDQ-PR-029).
( stamp "hardened writer_throughput, fsync=close, 200 M coincidences, 3 runs (SRS-PERF-021)"
  status=0
  for _ in 1 2 3; do
    build/hardened/benchmarks/writer_throughput --dir /var/tmp/minidaq-bench \
      --coincidences 200000000 --fsync close 2>&1 || status=1
    rm -f /var/tmp/minidaq-bench/*
  done
  exit $status ) > "$out/perf-writer.txt"
check "writer benchmark ran" $?
fi
[ "$part" = 2 ] && summary

if in_part 3; then

# The regression gate. It used to run only in perf.yml, on a runner that did not exist
# (MDQ-PR-014); here it runs on the reference machine, and a failure fails the release checks.
# Since CR-0025 it compares the candidate with the previous release, both built here and run
# interleaved on this machine in this session (tools/perf_ab.sh): the reference machine's speed
# drifts from day to day by more than the gate's threshold, and a baseline recorded on another
# day failed releases 0.8.0 and 0.9.0 with no change to the code. The comparison with the
# recorded baseline (benchmarks/baseline/book-vm.json) is kept as the trend, perf-trend.txt, and
# judged by the release record, not by this script; the drift a release-to-release gate cannot see
# is bounded by SRS-PERF-020 and SRS-PERF-021, which part 2 measures against fixed limits.
# The builds' own output stays in perf-suite.txt: a build that fails says why (MDQ-PR-058).
# PERF_BASE names the previous release (default: the newest book-v* tag before this commit).
perf_base=${PERF_BASE:-$(git describe --tags --abbrev=0 --match 'book-v*' HEAD 2>/dev/null)}
{ stamp "perf: release build of $(git rev-parse --short HEAD) and of $perf_base, interleaved"
  [ -n "$perf_base" ] && git rev-parse --verify -q "$perf_base^{commit}" >/dev/null &&
  cmake --preset release && cmake --build --preset release -j"$(nproc)" &&
  git worktree add --detach "$work/perf-base" "$perf_base" &&
  (cd "$work/perf-base" && cmake --preset release -DMINIDAQ_BUILD_EXERCISES=OFF &&
    cmake --build --preset release -j"$(nproc)") &&
  echo "base $perf_base = $(git rev-parse "$perf_base^{commit}")" &&
  tools/perf_ab.sh "$work/perf-base/build/release" build/release "$out/perf-ab" 5 2
} > "$out/perf-suite.txt" 2>&1
status=$?
cp "$out/perf-ab/gate.txt" "$out/perf-gate.txt" 2>/dev/null || echo "the gate did not run" > "$out/perf-gate.txt"
git worktree remove --force "$work/perf-base" 2>/dev/null
check "performance regression gate, against $perf_base interleaved" $status
python3 tools/perf_gate.py benchmarks/baseline/book-vm.json "$out/perf-ab/head.json" \
  > "$out/perf-trend.txt" 2>&1
echo "trend against benchmarks/baseline/book-vm.json (not a check, CR-0025): status $?" \
  >> "$out/perf-trend.txt"

# Chapter 19: the system test report of the release build (system test plan, section 8), and the
# soak of SRS-SYS-003 on the same programs.
python3 tools/test_report.py build/release "$out/system-test-report.md" > "$out/system-tests.txt" 2>&1
check "system test report" $?
python3 tools/soak.py build/release/minidaq/apps "$out/soak" --minutes 30 > "$out/soak.txt" 2>&1
check "soak, 30 minutes at 1 M singles/s" $?
# Chapter 33: the chain end to end on the same programs, against the offline reference, with the
# daily QC report and the reconstruction of a phantom (SRS-SYS-006 to SRS-SYS-008).
MINIDAQ_RECON_CPP=build/release/recon python3 tools/e2e.py build/release/minidaq/apps "$out/e2e" \
  > "$out/e2e.txt" 2>&1
check "end to end: the reference's records, every count balanced, QC, image" $?
fi
[ "$part" = 3 ] && summary

if in_part 4; then

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
targets=(config decoder raw16 protocol packet sorter listmode calibration)
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
fi

echo "After the last part, evaluate the acceptance specification: tools/acceptance.py $out"
summary
