# 0029. A codebase survey from the project's own records, with hotspots and checks of the item map

Date: 2026-11-04
Status: Accepted

## Context

Chapter 34 is about the first ninety days of an engineer who takes over a data acquisition
codebase. Such an engineer has two sources that are rarely read together: the documents (the
software items and their safety classes, the requirements, the hazards, the problem reports) and
the history (which files change, how often, how much). A question such as "which class B item
changes most and has open problem reports?" needs both. MiniDAQ keeps both in machine-readable
form, so a tool can put them side by side.

## Options

1. **What to measure.** Size alone; complexity metrics (cyclomatic complexity per function); or
   change frequency times size, the "hotspot" of A. Tornhill's work, with size measured in code
   lines.
2. **Where the item of a file comes from.** A new mapping in the survey; or the existing software
   items with the rule `tools/check_items.py` already applies (the longest prefix wins).
3. **What the tool decides.** A score that ranks the items and recommends work; or a report with
   the numbers side by side and checks only where a rule exists.
4. **Dependencies.** A code analysis package (lizard, a static analyzer's metrics); or git and the
   standard library.

## Decision

- **Commits times code lines** per file (option 1, the third). It needs no parser for C++ or
  Python, is the same for every language, and its two factors are both explainable to a reader:
  a large file that never changes is read once, a small file that changes often is cheap to
  read, and a large file that changes often is where defects and misunderstandings gather.
- **The existing item map and its rule** (option 2, the second). A second mapping would disagree
  with the first; the survey uses the rule of `check_items.py` and reports what that rule hides:
  nested claims and prefixes that claim nothing.
- **A report, not a score** (option 3, the second). The items are ordered by class, open problem
  reports and commits, and every number is shown. The tool fails only on what the project's rules
  forbid (a file without an owner, an ambiguous owner).
- **git and the standard library** (option 4, the second). No new SOUP for a tool of class T1.

## Consequences

### Positive

- A new engineer gets in a second the view that otherwise takes a week of reading: which items
  matter most, which change, which have open problems, and where the map of the code is unclear.
- The first run found two prefixes in the item map that claimed no file (removed by CR-0021) and
  a header in `config`'s directory owned by `hw`.
- The tool reads only what the project already keeps; it adds no record to maintain.

### Negative

- Code lines are a rough measure of complexity; a long table of constants scores like a long
  function. The report shows both factors so that a reader can judge.
- The history counts commits, not their reasons: a reformatting commit counts like a fix. A
  window (`--since`) after a mass change, or reading the commits, corrects for it.
- The hotspots of a young repository, or one whose history was rewritten, say little: MiniDAQ's
  history starts in October 2026.
