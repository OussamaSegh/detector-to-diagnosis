#!/usr/bin/env bash
# Runs the same gates as the CI pipeline, locally. Usage:
#   ci/run_all.sh            # all presets
#   ci/run_all.sh debug tsan # selected presets
set -euo pipefail
cd "$(dirname "$0")/.."

presets=("$@")
if [ ${#presets[@]} -eq 0 ]; then
  presets=(debug clang-release gcc-cxx23 hardened asan-ubsan tsan)
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
echo "=== all gates passed: ${presets[*]} ==="
