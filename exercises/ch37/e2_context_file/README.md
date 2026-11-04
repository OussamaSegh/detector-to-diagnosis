# Exercise 37.2 (M): A context file that stays true

**Goal.** Check that a context file (the `HANDOFF.md`, `CLAUDE.md` or `AGENTS.md` that an assistant
reads first in a repository) names only paths that exist and commands that the repository
defines. An assistant follows a stale instruction exactly as faithfully as a true one; nobody
reads the file as closely as it does.

**Time.** 2 hours.

**What to write** (`context.py`):
- `references(text)`: the repository paths a Markdown text refers to, as
  `[(line, path)]`: every code span (text between single backquotes) and every word of a fenced
  code block whose first part is a top-level entry of the repository, given as the set `tops`
  (`references(text, tops)`), with a trailing `/`, a `:line` suffix and trailing punctuation
  removed. A code span in a fenced block is not a code span. URLs (`https://...`) are not paths.
- `problems(text, root)`: `[(line, message)]` for every reference that does not exist under
  `root`. A reference with a placeholder (`NN`, `X.Y.Z`, `<name>`, `*`) is a pattern: it is a
  problem only if no path matches it (`NN` is two digits, `X.Y.Z` a version, `<name>` and `*` one
  path component). Also a problem: a `ctest -R NAME` whose name no `add_test(NAME ...)` in the
  repository's CMake files defines.

**Starter.** `starter/context.py` takes every code span with a `/` in it, URLs and placeholders
too, and checks them with `os.path.exists`; it ignores fenced blocks and commands.

**Acceptance** (`tests/test_context.py`), on a small repository made by the tests:
- Existing paths, directories with a trailing slash and `path:line` pass; a missing file and a
  missing directory are reported with their line; a URL and a word that is not under a top-level
  entry are not references.
- `exercises/chNN/<exercise>/` matches an existing exercise and `docs/releases/X.Y.Z.md` a release
  record; the same patterns with nothing to match are reported.
- A path in a fenced block is checked; `ctest -R tools.dicom` passes when the test exists, and
  `ctest -R tools.gone` is reported.

**Then, by hand.**
1. Run your solution on this repository's `HANDOFF.md`. What does it find, and which of the
   findings are real?
2. What in a context file can a check like this not see: a rule that is no longer the team's, a
   number that changed, a decision that was reversed?
3. Who owns the context file in your team, and is a change to it reviewed like code?
