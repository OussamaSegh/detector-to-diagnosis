# Exercise 13.2 (M): What a software change triggers

**Goal.** Write a one-page brief, "What a software change in NeuroLF triggers, regulatory-wise",
for one concrete change: moving the acquisition PC from Ubuntu 22.04 to Ubuntu 24.04. The DAQ's
source code does not change; everything below it does.

**Time.** 2 hours.

**Starter.** `starter/brief.md`: a first draft that a reviewer would send back. It says the
change has no regulatory impact, lists no affected items, and verifies it with unit tests.

**Acceptance** (`tests/test_brief.py`, run by CTest as
`ch13/e2_change_brief/<variant>/unittest`). The tests check structure and the questions a
reviewer asks first, not whether your reasoning is right; compare that with the solution's
`NOTES.md`.
- Ten sections, in order: Change, Software items affected, Software safety class, Risk,
  Verification, EU, US, Switzerland, Documents to update, Decision; none empty.
- At most 700 words.
- The affected items include the SOUP; the risk section names ISO 14971 and the hazards; the
  verification plans regression and latency measurements; the EU section deals with the
  notified body and the technical documentation; the US section applies FDA's guidance
  "Deciding When to Submit a 510(k) for a Software Change to an Existing Device"; the Swiss
  section relates the change to the CE marking; the documents include the SOUP list and the
  release notes.
- None of the claims "no regulatory impact", "only the operating system" or "no need to
  retest".
- The decision names who decides: regulatory affairs, quality or the change control board.

**Hints.** Read the brief as the notified body's software reviewer would, with the question
"how do you know this change is safe?". The answer is never "nothing changed".
