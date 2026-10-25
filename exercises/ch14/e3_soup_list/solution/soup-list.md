# MiniDAQ SOUP list (Exercise 14.3)

For MiniDAQ 0.3.0. Pins from `cmake/Dependencies.cmake` as of Chapter 14.

## Shipped

| Field | nlohmann/json |
|---|---|
| Identification | nlohmann/json 3.11.3, archive `json.tar.xz`, SHA-256 `d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d` |
| Supplier and license | Niels Lohmann and contributors; MIT |
| Purpose | Reads configuration files and control requests, writes status, audit records and run records. Not on the hot path. |
| Requirements | Parses any byte sequence without undefined behavior; reports malformed input as a catchable exception or a discarded value; round-trips the values MiniDAQ writes; replaces invalid UTF-8 on output when asked. |
| Used by | Items `config`, `service`, `protocol`, `output`, `audit`, `server` (class B) |
| Known anomalies | Release notes of 3.12.0 (2025-04-11) reviewed: one fix concerns a feature MiniDAQ uses, integers parsed as floats when `errno` holds `EINTR` (#4506). MiniDAQ's reader rejects a non-integer where it needs an integer, so the effect is a refused request, not a wrong setting. |
| Risk | A wrong setting (HZ-3) or a crash during a run (HZ-2). Controlled by MiniDAQ's own validation of every value, the effective configuration in the status and run record, caught exceptions, and fuzzing under sanitizers. |
| Last review | 2026-10-25, for MiniDAQ 0.3, against the release notes of 3.12.0 |

## Development and verification only

| Item | Version and pin | License | Use |
|---|---|---|---|
| GoogleTest | 1.15.2, commit `b514bdc898e2951020cbdca1304b75f5950d1f59` | BSD-3-Clause | Unit tests |
| Google Benchmark | 1.9.1, commit `96afad55c79e02f5dfca1374e772c2be72ba631b` | Apache-2.0 | Benchmarks |
