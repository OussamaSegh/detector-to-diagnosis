# Chapter 7 measurements: cost of hardening

Google Benchmark JSON, one file per build, benchmark and round: `<build>.<bench>.<round>.json`.
Builds (GCC 13.3, `-O2`, 4-vCPU Xeon VM at 2.3 GHz): `hard-off` (all protections off,
including Ubuntu's defaults), `release` (preset, distribution defaults), `hardened` (preset).
Five rounds; within a round the three builds ran one after another. Summary in Chapter 7
("What it costs") and in `docs/performance-budget.md`.
