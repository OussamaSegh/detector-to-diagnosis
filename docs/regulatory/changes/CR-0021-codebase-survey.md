# CR-0021: A survey of the codebase for an engineer who takes it over

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-04, by the software lead |
| Source | improvement: the first 90 days with a data acquisition codebase (Chapter 34) |
| Decision | approved, 2026-11-04, software lead |
| Commits | none yet |

## Description

1. **The survey** `tools/survey.py` (TL-43) puts side by side, for every software item of
   `docs/architecture/software-items.json`, what the documents say (safety class, hazards,
   requirements and how many of them a test names, problem reports and how many are open) and
   what the history says (files, code lines, commits and changed lines since a date); lists the
   file hotspots (commits times code lines); and checks the item map: files that no item claims,
   files that two items claim with prefixes of the same length (both fail), files that two items
   claim with nested prefixes, and prefixes that claim no file (both reported).
2. **The item map** loses two prefixes that claimed no file, found by the first survey:
   `minidaq/src/metrics/` (item `metrics`) and `minidaq/src/processing/count_rates` (item
   `processing`). Both components are header-only; the prefixes were written for source files
   that were never created.

## Reason

An engineer who takes over a codebase reads its documents and its history separately, and the
questions that matter come from the two together: an item of the highest class that changes every
week, an item with open problem reports and few tests, a file that every second commit touches.
The survey makes that view in a second from the files the project already keeps, and its checks
of the item map find what a reader of the map would not: the first run found two prefixes that
claim nothing and a header file in one item's directory owned by another item through a longer
prefix.

## Impact analysis

### Requirements

Added (SRS version 23): SRS-SVY-001 (the history per file), SRS-SVY-002 (the owner of each file
and the checks of the map), SRS-SVY-003 (the report per item and the hotspots). None changed or
withdrawn. These three are the differences from the requirements baseline that this request
names.

### Software items and safety class

No item of the product changes. The item map changes by two prefixes that matched no file: no
file changes owner and no class changes (`tools/check_items.py` passes before and after). The
survey is a tool (TL-43, class T1: its output informs priorities and is neither in the product
nor verification evidence).

### Risk

No hazard and no estimate changes. The survey adds no risk control.

### SOUP

None added. The survey uses git and the Python standard library.

### Interfaces and data formats

None of the product. New output: the survey's Markdown and JSON, for people.

### Documents

The SRS, version 23; the tool list (TL-43) and `tools.md`; the software items (two prefixes);
ADR 0029; the trace matrix; the CHANGELOG. The threat model is reviewed: the survey runs on a
developer's checkout and reads only tracked files and git's history (no new element of the
running system).

### Regulatory

The intended use of MiniDAQ does not change. IEC 62304's maintenance process asks that a
modification be analyzed for its effect before it is made; the survey helps a new maintainer find
where to look, and decides nothing (assumption: confirm with team).

## Verification

`tools/test_survey.py` (the test `tools.survey`), on strings for the numstat parsing and the
ownership rule and on a repository made for the test for the whole report; `docs.trace`;
`docs.baseline`; the whole ctest. The survey of the repository at the chapter's commit is kept in
`measurements/ch34/`.

## Decision

Approved on 2026-11-04 by the software lead: a tool for people, with checks of the item map that
the project's own map passes.
