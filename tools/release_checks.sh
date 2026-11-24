#!/usr/bin/env bash
# The release checks of SDP section 6 that are not run on every change, in order, on one commit:
# all presets, static analysis, starters, the stress run, the performance requirements and the
# regression gate, the system test report and the end-to-end run, 10 minutes of fuzzing per
# target, and the soak of the candidate interleaved with the previous release's (CR-0038).
# Run it on the reference machine, quiet, from a clean checkout. Each check writes its output to
# OUT; the release record cites the files.
#
#   tools/release_checks.sh OUT [FUZZ_SECONDS] [PART]
#
# PART is all (the default), resume, or one of five parts, the first four each under 45 minutes on
# the reference machine: 1 the six presets, static analysis and the starters; 2 the stress run,
# the wide property search, coverage and the benchmarks; 3 the regression gate, the system tests
# and the end-to-end run; 4 the fuzzing; 5 the soak, about 3.5 hours, in blocks that a stopped
# run keeps (tools/soak_ab.py: run it again and it continues at the block it was in). Run the
# parts in order, on the same commit and into the same OUT,
# when one session cannot hold the whole run (MDQ-PR-041: a machine that restarts within the
# hour). Parts 2 to 4 use the builds that part 1 made. PART resume runs, in order, every part
# that OUT/release-checks.txt does not record as passed ("all release checks passed (part N)"),
# and stops at the first part that fails: after a restart, run it again with the same OUT and it
# continues where the run stopped (roadmap 2.0.0, Theme D). A failed part runs again in full,
# but only once for a release and only when OUT/rerun-part-N.md holds the investigation that
# allows it (SDP section 8); resume refuses otherwise, with status 4 (MDQ-PR-077).
#
# The exit status is 0 only if every check passed (CAPA-0004: a check that cannot run fails), and
# 3 if the run stopped before the last check (MDQ-PR-029).
set -uo pipefail
out=${1:?usage: tools/release_checks.sh OUT [FUZZ_SECONDS]}
# The soak's length, the fuzz targets and their default seconds come from one file that the
# release record reads too (CAPA-0007).
fact() { python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print(" ".join(map(str, v)) if isinstance(v, list) else v)' "$(dirname "$0")/release_facts.json" "$1"; }
soak_minutes=$(fact soak_minutes) || exit 2
soak_blocks=$(fact soak_blocks) || exit 2
fuzz_seconds=${2:-$(fact fuzz_seconds)} || exit 2
part=${3:-all}
case "$part" in all | resume | 1 | 2 | 3 | 4 | 5) ;; *) echo "PART is all, resume, 1, 2, 3, 4 or 5" >&2; exit 2 ;; esac
if [ "$part" = resume ]; then
  mkdir -p "$out"
  for p in 1 2 3 4 5; do
    if grep -qxE "all release checks passed \(part ($p|all)\)" "$out/release-checks.txt" 2>/dev/null; then
      echo "part $p: passed before, skipped"
      continue
    fi
    # A part that failed runs again only after its investigation is written, and only once for
    # a release (SDP section 8, MDQ-PR-077); a part that stopped without a verdict runs again.
    # Only the part's own verdicts count: a whole run writes one per part (MDQ-PR-082).
    fails=$(grep -cxE "[0-9]+ release checks failed \(part $p\)" "$out/release-checks.txt" 2>/dev/null)
    if [ "${fails:-0}" -ge 2 ]; then
      echo "part $p has failed twice for this release: no third run; the failure is a problem report against the commit (SDP section 8)" >&2
      exit 4
    fi
    if [ "${fails:-0}" -eq 1 ] && [ ! -s "$out/rerun-part-$p.md" ]; then
      echo "part $p failed: write its investigation to $out/rerun-part-$p.md before it runs again (SDP section 8, MDQ-PR-077)" >&2
      exit 4
    fi
    "$0" "$out" "$fuzz_seconds" "$p" || exit $?
  done
  echo "every part has passed"
  exit 0
fi
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
# The failures of each part, so that a whole run also records each part's verdict (MDQ-PR-082).
part_failed=(0 0 0 0 0 0)
current=0
in_part() { if [ "$part" = all ] || [ "$part" = "$1" ]; then current=$1; return 0; fi; return 1; }
stamp() { echo "# $(date -u +%FT%TZ) commit $(git rev-parse --short HEAD) $*"; }
# Every result also goes to OUT/release-checks.txt, one section per part, which
# tools/acceptance.py reads (Chapter 33); a part run again appends a new section.
check() {  # name status
  local line
  if [ "$2" -eq 0 ]; then
    line="pass  $1"
  else
    line="FAIL  $1"
    failed+=("$1")
    part_failed[current]=$((part_failed[current] + 1))
  fi
  echo "$line"
  echo "$line" >> "$out/release-checks.txt"
}
summary() {
  finished=yes
  # A whole run records each part's verdict too, so that resume asks for an investigation, and
  # counts a run again, only for the part that failed (SDP section 8, MDQ-PR-082).
  if [ "$part" = all ]; then
    local p
    for p in 1 2 3 4 5; do
      if [ "${part_failed[p]}" -gt 0 ]; then
        echo "${part_failed[p]} release checks failed (part $p)"
      else
        echo "all release checks passed (part $p)"
      fi >> "$out/release-checks.txt"
    done
  fi
  if [ ${#failed[@]} -gt 0 ]; then
    echo "${#failed[@]} release checks failed (part $part)" | tee -a "$out/release-checks.txt" >&2
    exit 1
  fi
  echo "all release checks passed (part $part)" | tee -a "$out/release-checks.txt"
  exit 0
}

commit_file=$out/commit.txt
case "$part" in 2 | 3 | 4 | 5) commit_file=$out/commit-part-$part.txt ;; esac
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

# CR-0029: the product (preset product, no simulator) and its own tests: the refusals, the
# symbol check, the UDP readout and the hardening of its programs.
{ stamp "ci/run_all.sh product (the product build without the simulator)"; ci/run_all.sh product; } \
  > "$out/product.txt" 2>&1
check "product build and its tests" $?

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
# branches is written into the release record from coverage/summary.txt and coverage/uncovered.txt,
# every class B line with a gap, which the next release's review compares line by line.
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

# Chapter 19: the system test report of the release build (system test plan, section 8). The
# soak of SRS-SYS-003 is part 5's.
python3 tools/test_report.py build/release "$out/system-test-report.md" > "$out/system-tests.txt" 2>&1
check "system test report" $?
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
read -r -a targets <<< "$(fact fuzz_targets)"
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

[ "$part" = 4 ] && summary

if in_part 5; then

# CR-0038: the soak of SRS-SYS-003 and SRS-PERF-022, of the candidate and of the previous
# release's programs built here, in blocks interleaved on this machine in this session
# (tools/soak_ab.py, as tools/perf_ab.sh runs the benchmarks): a soak of the candidate alone
# could not tell a slow spell of the machine from a slower program (MDQ-PR-096). soak.txt is the
# candidate's blocks as one soak (ACC-03, ACC-04); soak-compare.txt the comparison (ACC-10). The
# blocks and the previous release's source stay in OUT/soak-ab until the part ends, so a run
# stopped by a time limit continues at the block it was in.
soak_base=${PERF_BASE:-$(git describe --tags --abbrev=0 --match 'book-v*' HEAD 2>/dev/null)}
base_src=$out/soak-ab/base-src
{ stamp "soak: release builds of $(git rev-parse --short HEAD) and of $soak_base, $soak_blocks blocks of $((soak_minutes / soak_blocks)) minutes each, interleaved"
  [ -n "$soak_base" ] && git rev-parse --verify -q "$soak_base^{commit}" >/dev/null &&
  cmake --preset release && cmake --build --preset release -j"$(nproc)" &&
  { [ -d "$base_src" ] || git worktree add --detach "$base_src" "$soak_base"; } &&
  [ "$(git -C "$base_src" rev-parse HEAD)" = "$(git rev-parse "$soak_base^{commit}")" ] &&
  (cd "$base_src" && cmake --preset release -DMINIDAQ_BUILD_EXERCISES=OFF &&
    cmake --build --preset release -j"$(nproc)") &&
  echo "base $soak_base = $(git rev-parse "$soak_base^{commit}")" &&
  python3 tools/soak_ab.py "$base_src/build/release/minidaq/apps" build/release/minidaq/apps \
    "$out/soak-ab" --blocks "$soak_blocks" --block-minutes "$((soak_minutes / soak_blocks))"
} > "$out/soak-ab.txt" 2>&1
cp "$out/soak-ab/head/summary.txt" "$out/soak.txt" 2>/dev/null || echo "the soak did not run" > "$out/soak.txt"
cp "$out/soak-ab/compare.txt" "$out/soak-compare.txt" 2>/dev/null ||
  echo "the comparison did not run" > "$out/soak-compare.txt"
grep -qx "result: PASS" "$out/soak.txt"
check "soak, $soak_minutes minutes at 1 M singles/s, in $soak_blocks blocks" $?
grep -qx "result: PASS" "$out/soak-compare.txt"
check "soak against $soak_base interleaved: the candidate not worse (ACC-10)" $?
git worktree remove --force "$base_src" 2>/dev/null
fi

echo "After the last part, evaluate the acceptance specification: tools/acceptance.py $out"
summary
