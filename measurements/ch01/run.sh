#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Builds costs.cpp with the project's release flags (-O2, C++23) and writes costs.txt here.
# Usage: measurements/ch01/run.sh [CXX]   Run it on a quiet machine.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cxx="${1:-c++}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
"$cxx" -std=c++23 -O2 -DNDEBUG -o "$work/costs" "$here/costs.cpp"
{
  echo "Machine: $(uname -m), $(nproc) CPUs; $("$cxx" --version | head -1); -O2, C++23."
  echo
  "$work/costs"
} > "$here/costs.txt"
cat "$here/costs.txt"
