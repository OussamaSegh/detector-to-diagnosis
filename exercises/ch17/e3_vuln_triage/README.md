# Exercise 17.3 (E): Triage a vulnerability scan

**Goal.** The CI job `vulnerability-scan` reported six findings for MiniDAQ's SBOM
(`tests/scan.json`; the advisories are in `tests/advisories.md`, with made-up identifiers).
Decide each one as `tools/vuln_triage.py` requires, and finish the rules that check decisions.

**Time.** 1 hour.

**Starter.** `starter/triage.py` is `tools/vuln_triage.py` as a module, without the rules for
`not_affected`, `exploitable` and `in_triage`. `starter/decisions.json` has one decision, which
breaks a rule.

**Acceptance** (`tests/test_triage.py`, run as `ch17/e3_vuln_triage/<variant>/unittest`):
- `check_decision()` requires a CycloneDX justification for `not_affected`, a response for
  `exploitable` and, for a high or critical finding, a `fix_by` date that has not passed
  (today is 2026-10-25 in the tests), and refuses `in_triage` for a high or critical finding.
- Your `decisions.json` decides every finding and passes the rules; the TLS 1.3 server defect
  and the host name defect are exploitable, the DTLS defect is not reachable, GoogleTest's is
  not present in the product, and the SAX decision says why the SAX defect does not reach
  MiniDAQ.

Then answer in `NOTES.md`: the critical finding is in nlohmann/json, and you marked it
not affected. What would you check before you sign that decision?

**Hints.** "Not present" and "not reachable" are different claims: a shared library that
contains the code makes it present. Read what MiniDAQ uses in the SOUP list before you decide.
