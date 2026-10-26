# MiniDAQ code review checklist

Version 1 (MiniDAQ 0.4.0-dev, Chapter 21). Status: draft for review.

The compilers, clang-tidy, cppcheck, the sanitizers and the documentation tests check what a
machine can check (the [coding standard](coding-standard.md) says which rule each one enforces).
This checklist is for the rest: what only a person who reads the change can see. Use it on every
change, before the change control checklist of the
[change control procedure](regulatory/changes/README.md), which asks whether the documents still
agree. A reviewer who has gone through a section and found nothing says so in one line; a
finding is written as section 7 says.

## 1. Before the code

1. The description says what changes and why, in words a reviewer outside the change follows.
2. A change to a requirement, a risk control, a class, a SOUP item, an interface or a data format
   names its approved change request.
3. The change is one thing. A refactoring and a behavior change in one commit hide each other.

## 2. Correctness

1. Every error path: what the caller sees, and whether the state is unchanged after a failure.
2. Boundary values: empty, one, the maximum, one past it; the wrap of every counter and sequence
   number; a negative time difference.
3. Units and types: time in picoseconds or nanoseconds as the type says, energies in keV, sizes in
   bytes or in elements, and no silent narrowing the warnings do not catch (a `static_cast`).
4. Input from outside (the network, a file, a configuration) is checked before use, against the
   rules of the coding standard, section 3.
5. Ownership and lifetime: who frees what, and nothing that refers to an object after it ends
   (a lambda that captures a reference, a `string_view` of a temporary, a thread that outlives
   its data).

## 3. Concurrency

1. For each shared variable: which threads write it, which read it, and what orders the accesses
   (a mutex, an atomic with its memory order, a join). If the answer is not in the code or its
   comment, ask for it.
2. Every relaxed or acquire/release atomic has a comment that names what it pairs with.
3. Nothing the pipeline waits on can block for a time nobody bounded: no lock held across I/O,
   no allocation on the hot path (coding standard, sections 5 and 6).
4. A signal handler, and anything it calls, uses only async-signal-safe functions and static
   memory (Chapter 21).

## 4. Tests

1. A test fails without the change and passes with it. For a fix, the test reproduces the
   reported failure; ask the author to show the failing run.
2. The test names the requirement it verifies (`// REQ:`), and the requirement says what the
   test checks.
3. The test waits for conditions, never for fixed times (coding standard, rule 5.5), and its
   numbers do not depend on the machine (MDQ-PR-020, MDQ-PR-022).
4. A test that is skipped somewhere says where and why, and the skip is not where the risk is.
5. A counter or condition defined as "A and B" has a test with A and not B, and one with B and
   not A: a test of one fault at a time cannot tell the halves apart (MDQ-PR-019).

## 5. The regulated parts

1. The trace still holds: requirements, tests, the risk file, the software items and their paths.
2. A class B item's new branch is taken both ways by some test, or the review accepts it with a
   reason (the coverage review of the release).
3. A new tool whose output is evidence is in the tool list, with what shows it can fail.
4. Controlled documents that changed get a new version before the release.

## 6. Diagnosability

1. If this code fails in the field, what will the investigator see? A counter in the status, an
   event in the flight recorder, an error message with the values that caused it, or nothing.
2. Error messages name the value and the limit ("1025 events, at most 1024"), not only the rule.
3. A new fault or loss path records a flight-recorder event (SRS-DIAG-004) and is counted.

## 7. Writing a finding

A finding is one problem, at one place, with:

- its severity: **blocker** (wrong result, data loss, a hazard, or a broken build), **major**
  (a defect that needs a particular input or timing), **minor** (style, naming, a comment), or
  **question** (the reviewer does not know whether it is a problem);
- the place: file and line, or the requirement or document;
- what the reviewer observed, and why it matters, in one or two sentences;
- a suggestion, if there is one. The author decides how to fix it.

A blocker or major finding is resolved before the change is merged: fixed, or answered with a
reason the reviewer accepts. The resolution is recorded with the review (in a team, the pull
request; in MiniDAQ, the commit message's review line). A problem found after the merge becomes
a problem report (development plan, section 7).

## Changes

| Version | Change |
|---|---|
| 1 | First version (Chapter 21, CR-0007). |
