#!/usr/bin/env bash
# A/B performance comparison of two builds on one machine (Chapter 20). The gate of Chapter 5
# compares a run with a baseline recorded earlier, which holds only on the machine and in the
# conditions of that recording: on a shared CI runner the next job may land on a different CPU
# model or next to a noisy neighbor. Here the base and the candidate run on the same machine, in
# the same job, interleaved round by round (A B, then B A, ...), so that a drift of the machine
# during the job affects both alike. Then tools/perf_gate.py decides as before.
#
#   tools/perf_ab.sh BASE_BUILD HEAD_BUILD OUT [ROUNDS] [CPU]
#
# Each round runs the gated benchmarks of tools/perf_suite.sh twice per build (REPS=2), so the
# gate sees 2 x ROUNDS repetitions of each side (default ROUNDS 5). OUT receives base.json,
# head.json and gate.txt. Exit status: the gate's (0 no regression, 1 regression).
set -euo pipefail
base=${1:?usage: tools/perf_ab.sh BASE_BUILD HEAD_BUILD OUT [ROUNDS] [CPU]}
head=${2:?usage}
out=${3:?usage}
rounds=${4:-5}
cpu=${5:-1}
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$out/rounds"

# [snippet:interleave]
for ((r = 1; r <= rounds; r++)); do
  if ((r % 2)); then order=(base head); else order=(head base); fi
  for side in "${order[@]}"; do
    dir=$base
    [ "$side" = head ] && dir=$head
    REPS=2 "$root/tools/perf_suite.sh" "$out/rounds/$side-$r.json" "$dir" "$cpu" >/dev/null
  done
done
# [/snippet:interleave]

python3 - "$out" "$rounds" <<'PY'
import json, sys
out, rounds = sys.argv[1], int(sys.argv[2])
for side in ("base", "head"):
    merged = None
    for r in range(1, rounds + 1):
        d = json.load(open(f"{out}/rounds/{side}-{r}.json"))
        merged = merged or {"context": d["context"], "benchmarks": []}
        merged["benchmarks"] += [b for b in d["benchmarks"] if b.get("run_type", "iteration") == "iteration"]
    json.dump(merged, open(f"{out}/{side}.json", "w"), indent=1)
PY
status=0
python3 "$root/tools/perf_gate.py" "$out/base.json" "$out/head.json" --strict \
  --threshold "${THRESHOLD:-0.05}" --alpha "${ALPHA:-0.01}" | tee "$out/gate.txt" || status=$?
exit $status
