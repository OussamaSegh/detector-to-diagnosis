# Exercise 36.1: notes

The starter fails all four tests (nine cases): it takes a `Review:` line from the middle of a
message, a subject that reads `Fix: the sorter`, a URL (`https` is a key and `//example.org/a`
its value) and a `Note:` in the body; it drops a continuation and compares keys with their case.

Design choices:

- Find the last paragraph first and decide about it as a whole: one line of prose in it and it
  is not a trailer block. The question is "is this paragraph a block of trailers?", not "is this
  line a trailer?".
- A paragraph with no blank line before it is the subject's, and the subject is never a
  trailer.
- The tests ask git, not a list of expected answers written by the same person as the code; the
  oracle is the tool every other reader of the history uses.
- Git's whole rule also takes a block in which a quarter of the lines are trailers if one of them
  is a line git writes itself (`Signed-off-by:` or `(cherry picked from commit`), and keys
  configured with `trailer.<key>.key`. `tools/check_commits.py` implements the first part; a
  team that configures keys should test against its own configuration.
- To the questions: git saw only the co-author lines; `git log --format=%(trailers:key=Review)`
  printed nothing for 191 commits, and nothing checked it until Chapter 36's measurement. A line
  `Key: value` is common prose ("Note: ...", a URL), so git asks for the shape of a block at the
  end. `Fixes:` in the middle of the body is not a trailer; a tool that closed reports from it
  would also close them from a sentence that says what a change does not fix.
