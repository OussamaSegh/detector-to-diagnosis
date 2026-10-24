"""Median items/s per benchmark and build variant, from the run_flags.sh JSON files.

Each cell is the median over both rounds (10 repetitions); the two per-round
medians are in brackets, so you can see whether a difference reproduces."""
import json, pathlib, statistics, sys

d = pathlib.Path(sys.argv[1])
variants = ["O2", "O3", "native", "lto", "pgo"]
vals = {}  # name -> variant -> round -> [values]
for v in variants:
    for f in sorted(d.glob(f"{v}-r*-bm_*.json")):
        r = f.name.split("-")[1]
        for b in json.loads(f.read_text())["benchmarks"]:
            if b.get("run_type") != "iteration":
                continue
            vals.setdefault(b["run_name"], {}).setdefault(v, {}).setdefault(r, []).append(b["items_per_second"] / 1e6)
print("| Benchmark (M items/s) | " + " | ".join(variants) + " |")
print("|---|" + "---|" * len(variants))
for name, per in vals.items():
    base = statistics.median([x for xs in per["O2"].values() for x in xs])
    cells = []
    for v in variants:
        rounds = per.get(v, {})
        allv = [x for xs in rounds.values() for x in xs]
        m = statistics.median(allv)
        rs = "/".join(f"{statistics.median(xs):.0f}" for _, xs in sorted(rounds.items()))
        cells.append(f"{m:.1f} [{rs}]" + ("" if v == "O2" else f" {m / base:.2f}x"))
    print(f"| {name} | " + " | ".join(cells) + " |")
