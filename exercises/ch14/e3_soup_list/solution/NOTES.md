# Exercise 14.3: notes

**Adding Eigen to the acquisition server.**

- Identification: the exact release, pinned by commit or archive hash in
  `cmake/Dependencies.cmake`, its license (MPL-2.0 for most of Eigen; check the parts used) and
  supplier, and an entry in `KNOWN` of `tools/make_sbom.py` so the SBOM includes it.
- Purpose and requirements: which functions MiniDAQ uses and what it requires of them
  (numerical accuracy, no allocation on the hot path, thread safety of the parts used,
  behavior with non-finite input), and the hardware and compiler it needs (vectorization
  flags change results in the last bits).
- Classification: it runs in the server process, so its users are class B and nothing
  segregates it; the risk analysis says what a wrong result could cause.
- Known anomalies: the issue tracker and the release notes after the pinned release, evaluated
  against those requirements, dated, for this MiniDAQ version.
- Verification: tests of MiniDAQ's use of it (reference results, edge cases), under the
  sanitizer presets; static analysis treats it as a system header.
- An ADR that records why Eigen and not another library, and whether a prototype belongs in
  the acquisition server at all: a separate process would keep it out of the server's class.
