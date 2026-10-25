#!/usr/bin/env bash
# Checks that the shipped build is reproducible (Chapter 20): checks a commit out twice, in two
# directories of different names and lengths, builds the shipped programs in each with the
# preset `hardened`, packages each with tools/release_bundle.py and compares the two product
# archives byte for byte. A difference is listed file by file from the two manifests.
#
#   tools/repro_check.sh OUT [COMMIT]
#
# OUT receives repro.txt (the two archives' SHA-256 and the result) and the first product
# archive. The dependencies are fetched in each checkout, so that their paths differ too.
# Exit status 0 if the two archives are identical.
set -euo pipefail
out=${1:?usage: tools/repro_check.sh OUT [COMMIT]}
commit=$(git rev-parse "${2:-HEAD}")
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$out"
out=$(cd "$out" && pwd)
work=$(mktemp -d)
a=$work/a
b=$work/second-checkout/with-a-longer-path
cleanup() {
  git -C "$root" worktree remove --force "$a" 2>/dev/null || true
  git -C "$root" worktree remove --force "$b" 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT

# [snippet:twice]
for dir in "$a" "$b"; do
  git -C "$root" worktree add --quiet --detach "$dir" "$commit"
  (cd "$dir" &&
    cmake --preset hardened -DMINIDAQ_BUILD_TESTS=OFF -DMINIDAQ_BUILD_BENCHMARKS=OFF \
      -DMINIDAQ_BUILD_EXERCISES=OFF >"$work/$(basename "$dir").configure.log" 2>&1 &&
    cmake --build --preset hardened --target minidaq_server minidaq_ctl >"$work/$(basename "$dir").build.log" 2>&1 &&
    python3 tools/release_bundle.py make build/hardened "$dir/out") ||
    { tail -30 "$work"/*.log; echo "build in $dir failed" >&2; exit 1; }
done
# [/snippet:twice]
pa=$(ls "$a"/out/*.tar)
pb=$(ls "$b"/out/*.tar)
{
  echo "# $(date -u +%FT%TZ) reproducibility of commit $commit, preset hardened"
  echo "first checkout:  $a"
  echo "second checkout: $b"
  sha256sum "$pa" | sed "s|$a/out/|first  |"
  sha256sum "$pb" | sed "s|$b/out/|second |"
  if cmp -s "$pa" "$pb"; then
    echo "identical: the product archive is reproducible"
    status=0
  else
    echo "DIFFERENT: files whose SHA-256 differ:"
    mkdir -p "$work/xa" "$work/xb"
    tar -xf "$pa" -C "$work/xa"
    tar -xf "$pb" -C "$work/xb"
    diff <(cat "$work"/xa/*/MANIFEST.sha256) <(cat "$work"/xb/*/MANIFEST.sha256) || true
    status=1
  fi
  echo "programs:"
  python3 "$root/tools/release_bundle.py" programs "$pa"
  exit $status
} | tee "$out/repro.txt"
status=${PIPESTATUS[0]}
cp "$pa" "$out/"
exit "$status"
