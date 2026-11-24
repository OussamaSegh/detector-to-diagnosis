#!/usr/bin/env bash
# Runs the same gates as the CI pipeline, locally. Usage:
#   ci/run_all.sh            # the six development presets
#   ci/run_all.sh product    # the product build without the simulator (CR-0029)
#   ci/run_all.sh debug tsan # selected presets
# CI runs all seven; the release checks run the six, then the product with its own record row.
set -euo pipefail
cd "$(dirname "$0")/.."

presets=("$@")
if [ ${#presets[@]} -eq 0 ]; then
  # The six presets of the release checks, from the file they share (CAPA-0007).
  read -r -a presets <<< "$(python3 -c 'import json; print(" ".join(json.load(open("tools/release_facts.json"))["presets"]))')"
fi

for p in "${presets[@]}"; do
  echo "=== preset: $p ==="
  cmake --preset "$p" >/dev/null
  mkdir -p build
  if ! cmake --build --preset "$p" >"build/$p.build.log" 2>&1; then
    tail -40 "build/$p.build.log"
    echo "=== build FAILED for preset $p ==="
    exit 1
  fi
  ctest --preset "$p" -LE starter | grep -E "tests passed|tests failed|\*\*\*|Failed|Exception"
done
# Chapter 16: controlled documents changed since the last release have a new version.
last="$(git describe --tags --abbrev=0 --match 'book-v*' HEAD 2>/dev/null || true)"
if [ -n "$last" ]; then
  python3 tools/design_file.py . --check --since "$last"
fi
echo "=== all gates passed: ${presets[*]} ==="
