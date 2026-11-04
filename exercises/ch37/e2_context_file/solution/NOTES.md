# Exercise 37.2: notes

The starter fails all five tests: it takes `a/b`, `items 1/6` and a URL as paths, reports every
placeholder as missing, never looks inside a fenced block and does not know what a test is.

Design choices:

- A reference is a word under a top-level entry of the repository. That one rule removes most
  false positives (prose with a slash, URLs, options) without a list of exceptions.
- Placeholders become regular expressions over every path of the repository, computed once. A
  pattern is fine if one path matches it: the file says "each exercise is like this", not "this
  file exists".
- Tests are checked against `add_test(NAME ...)` in the CMake files, not against `ctest -N` of a
  build: the check runs without a build directory, as an assistant reads the file without one.
- To the questions: on this repository's `HANDOFF.md` (at Chapter 37) the solution reports six
  lines, and none is a stale reference. Five name build outputs (`build/starters`, `book/build/kdp`,
  the cover PDF), which exist only after a build, and one uses a placeholder the rules do not know
  (`eK_name`). A real check needs a list of build outputs and the team's placeholders; until it has
  them, it is a report for a person, not a gate. What it cannot see is worse: a rule the team
  dropped, a number that changed, a decision reversed. Those stay true-looking, and an assistant
  follows them. The context file is a controlled document in effect: it has an owner, it is
  reviewed with the change that makes it stale, and a reviewer reads its diff as carefully as the
  code's.
