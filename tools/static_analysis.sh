#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Static analysis gate (Chapter 7): clang-tidy with the curated .clang-tidy and
# cppcheck with tools/cppcheck-suppressions.txt, over the library and the
# applications. Exit status 0 only if both report nothing.
#
#   tools/static_analysis.sh [BUILD_DIR]     default BUILD_DIR: build/clang-release
#
# BUILD_DIR must hold compile_commands.json (every preset exports it). Tests,
# benchmarks and exercises are not gated: test code uses patterns on purpose
# (raw loops being measured, defects planted in exercise starters).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
build="${1:-$root/build/clang-release}"
tidy="${RUN_CLANG_TIDY:-run-clang-tidy-18}"      # the parallel driver
tidy_bin="${CLANG_TIDY:-clang-tidy-18}"          # the analyzer it runs
jobs="${JOBS:-$(nproc)}"
[[ -f "$build/compile_commands.json" ]] || { echo "no compile_commands.json in $build; configure a preset first" >&2; exit 2; }

status=0
echo "== clang-tidy ($("$tidy_bin" --version | grep -o 'version [0-9.]*'))"
# [snippet:tidy]
log="$(mktemp)"
if ! "$tidy" -clang-tidy-binary "$tidy_bin" -p "$build" -quiet -j "$jobs" "$root/minidaq/(src|apps)/" >"$log" 2>&1 \
   || grep -qE '(error|warning): ' "$log"; then
  grep -E '(error|warning): ' "$log" | sort -u || cat "$log"
  status=1
fi
rm -f "$log"
# [/snippet:tidy]

echo "== cppcheck ($(cppcheck --version))"
cppcheck --std=c++20 --language=c++ --enable=warning,performance,portability,style \
  --inline-suppr --suppress=missingIncludeSystem \
  --suppressions-list="$root/tools/cppcheck-suppressions.txt" \
  -I "$root/minidaq/include" -j "$jobs" --error-exitcode=1 --quiet \
  --template='{file}:{line}: {severity}: {message} [{id}]' \
  "$root/minidaq/src" "$root/minidaq/apps" || status=1

if [[ $status -eq 0 ]]; then echo "static analysis: clean"; else echo "static analysis: findings above" >&2; fi
exit $status
