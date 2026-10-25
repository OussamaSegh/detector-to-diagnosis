# Exercise 14.2 (M): Twenty testable requirements for the sorter

**Goal.** Write at least 20 software requirements for MiniDAQ's coincidence sorter that a
tester can verify without asking you what you meant, and finish the linter that catches the
usual faults of requirement text.

**Time.** 2 hours.

**Starter.** `starter/sorter-requirements.md` has five requirements of the kind a first draft
contains. `starter/req_lint.py` checks the ID, the subject, the optional words and the
verification method, but not the vague words, the units of numbers, or rows that hold more
than one requirement.

**Acceptance** (`tests/test_requirements.py`, run by CTest as
`ch14/e2_sorter_requirements/<variant>/unittest`):
- The linter reports a row with more than one "shall" or none, a vague word ("fast",
  "appropriately", "robust", "and/or", ...), an optional word ("should"), a number without its
  unit or counted noun (but not "24 sectors" or "schema version 1.3"), a missing or unknown
  verification method, and a duplicate ID.
- `sorter-requirements.md` has at least 20 requirements, every one passes the linter, at least
  80% are verified by test, and together they cover the window and its edge, both window
  modes, all four multiples policies, the energy gate, the sector and field-of-view cuts,
  delayed coincidences, out-of-order singles, independence of batch sizes, accounting of every
  single, configuration errors, throughput and latency.

**Hints.** Read `docs/adr/0010-coincidence-sorter-and-merger.md` and
`minidaq/include/minidaq/processing/coincidence_sorter.hpp`: a requirement states behavior
the code must have, so check each one against the code and the tests of Chapter 10. The
linter checks form only; ask a colleague whether each requirement is the right one.
MiniDAQ's own SRS is `docs/regulatory/srs.md`, checked by `tools/req_lint.py`.
