# Exercise 36.3: notes

The starter fails seven of the ten tests. With an insertion on one side every later index is
shifted, so it compares line 5 of one file with line 4 of another and calls the result a merge;
and it reports conflicts without markers, so the file it writes compiles, maybe, and says nothing.

Design choices:

- The stable points are the lines of the base that both sides keep. Between two of them there is
  one region per side; the four cases (neither changed, one changed, both changed equally, both
  changed differently) are the whole algorithm. This is the classic diff3 structure.
- `SequenceMatcher` with `autojunk=False`: its heuristic otherwise treats frequent lines (in a
  file of more than 200 lines, a line such as `}` or a blank line) as junk and finds a different
  matching. Git's own diff (Myers by default, histogram or patience if configured) can match
  ambiguous lines differently; the tests use lines that are unique, where every diff agrees.
- Adjacent changes conflict because no line of the base separates them: there is no stable point
  between the two regions, so they are one region that both sides changed. Git does the same; a
  merge that guessed would be guessing about code that sits next to code.
- A side whose last line has no newline gets one inside the markers, so that `=======` is a line
  of its own. Git does the same.
- To the questions: one side renames a function and the other adds a call to the old name, in
  another part of the file; or one side changes a unit (microseconds to nanoseconds) and the
  other adds a comparison with a constant in the old unit. Both merge cleanly. That is why
  MiniDAQ's merge commit runs the whole CI and why a reviewer reads the merged result of a long
  branch, not only its diff against its own base.
