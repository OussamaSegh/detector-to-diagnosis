# Exercise 7.3 (E): Generate an SBOM, then review a change to it

**Goal.** Generate MiniDAQ's CycloneDX SBOM and validate it. Then write the tool a
release reviewer wants: given the SBOM of the last release and the SBOM of this
one, list what changed in the software MiniDAQ depends on.

**Time.** 1 hour.

**Part 1.** Run `tools/make_sbom.py --validate` and `tools/make_sbom.py -o minidaq.cdx.json`.
Read the output. Which component is `"scope": "required"` and why are the others
`"excluded"`? What would you need to add for a dependency that is not in `KNOWN`?
Run it twice with the same `SOURCE_DATE_EPOCH`: are the files identical, and why does
that matter for a release?

**Part 2.** Implement `diff(old, new)` in `starter/sbom_diff.py`.

**Acceptance** (`tests/test_sbom_diff.py`, run against the real SBOM): no changes for
identical SBOMs; an upgrade is one `version` change, not a removal plus an addition;
license, scope and hash changes are reported; added and removed components are
reported; exit status 0 without changes and 1 with changes.

**Hint.** A component's `bom-ref` includes its version. What identifies "the same
component" across two releases?
