# Exercise 17.1 (M): Threat model a status page before it is built

**Goal.** The service team asks for a read-only status page that the scanner room's display can
show: `GET /status` over HTTPS, served by `minidaq_server`. Before anyone writes it, model its
threats with STRIDE, the way `docs/regulatory/security/threats.json` models the control API, and
finish the checker that keeps such a model honest.

**Time.** 2 hours.

**Starter.** `starter/threats_check.py` has the diagram check of `tools/check_threats.py`, and
TODOs for the coverage rule and the status rules. `starter/threats.json` has the elements of
`tests/dashboard.dot` and two threats, one of them wrong. `tests/requirements.txt` lists the
requirements DASH-001 to DASH-008 that the team proposes.

**Acceptance** (`tests/test_threats.py`, run by CTest as `ch17/e1_threat_model/<variant>/unittest`):
- `check_coverage()` reports every element without a threat for a STRIDE category that applies
  to its kind; `check_threats()` reports a mitigated threat without requirements or with one
  that is not proposed, an environment threat without its assumption, and an accepted or not
  applicable threat without a note.
- Your `threats.json` passes the checker against the diagram and the requirements, has at least
  10 threats, and mitigates these four with the right requirement: elevation through the page
  (DASH-002), disclosure on the wire (DASH-001), spoofing of the display (DASH-003), and denial
  of service by slow clients (DASH-005).

Then answer in `NOTES.md`: which proposed requirement would you drop, which is missing, and is
the page worth its threats at all?

**Hints.** An external entity has S and R, a process all six, a flow T, I and D. For each, ask
who would want to do it and what they would gain during a scan. The cross-site request is the
threat that people who have never written for a browser forget.
