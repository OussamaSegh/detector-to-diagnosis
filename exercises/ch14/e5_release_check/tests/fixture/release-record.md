# Release record

## Release

MiniDAQ 0.3.0, commit 0123456789abcdef0123456789abcdef01234567, tag book-v0.3.0

## Verification

| Check | Result | Evidence |
|---|---|---|
| build debug | pass | logs/build.log |
| build clang-release | pass | logs/build.log |
| build gcc-cxx23 | pass | logs/build.log |
| build hardened | pass | logs/build.log |
| build asan-ubsan | pass | logs/build.log |
| build tsan | pass | logs/build.log |
| tests debug | pass | logs/tests-debug.log |
| tests clang-release | pass | logs/tests-clang-release.log |
| tests gcc-cxx23 | pass | logs/tests-gcc-cxx23.log |
| tests hardened | pass | logs/tests-hardened.log |
| tests asan-ubsan | pass | logs/tests-asan-ubsan.log |
| tests tsan | pass | logs/tests-tsan.log |
| static analysis | pass | logs/static-analysis.log |
| fuzzing | pass | logs/fuzz.txt |
| performance | pass | logs/perf.txt |
| trace matrix | pass | logs/trace.txt |

## Known anomalies

MDQ-PR-005 and MDQ-PR-007, evaluated in known-anomalies.md; neither is relevant to safety.

## SOUP review

nlohmann/json 3.11.3 reviewed 2026-10-25 for MiniDAQ 0.3.

## Build

```
cmake --preset hardened
cmake --build --preset hardened
```

## Archive

minidaq-v0.3.0.zip with the git history, the book files and the SBOM, in the project files.
