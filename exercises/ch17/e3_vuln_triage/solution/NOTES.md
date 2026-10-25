# Exercise 17.3: notes on the solution

| Finding | Decision | Why |
|---|---|---|
| EX-2026-0101, TLS 1.3 server, memory before authentication | exploitable, update, fix by 2026-11-08 | The server is exactly that; the token check comes after the handshake. Until the update, the site's network is the control (section 6). |
| EX-2026-0102, DTLS | not_affected, code_not_reachable | The code is in `libssl.so`, so it is present; MiniDAQ never creates a DTLS context, so it is not reachable. |
| EX-2026-0103, host name check in a client | exploitable, update | `minidaq_ctl` checks host names. The effect is a crash before the token is sent, so medium is right and no date is forced, but it is still exploitable. |
| EX-2026-0104, SM2 on ARM | not_affected, code_not_reachable | No SM2, no ARM. |
| EX-2026-0105, SAX handler that throws | not_affected, code_not_reachable, to be confirmed | MiniDAQ passes no SAX handler. |
| EX-2026-0106, GoogleTest | not_affected, code_not_present | Tests only; the SBOM says `excluded`. |

**Before signing the SAX decision.** `json::parse` is implemented with a SAX parser and an
internal handler that builds the DOM. So "we do not use SAX" is not the same as "the affected
code does not run". Read the advisory's affected function and the fix's diff: if the defect is
in the parser's handling of any handler that throws, ask whether the internal handler can throw
(it can, for example on an allocation failure or on a number it cannot store). A critical
finding marked `not_affected` is the decision an auditor will read first, so its detail must
show the reasoning, not the conclusion.

A triage is a decision with a date. When the next release of the platform fixes 0101 and 0103,
the scan stops reporting them, and `vuln_triage.py --strict` reports the decisions as stale: the
record of what was decided, and when, stays in git.
