# Exercise 36.3 (H): A merge that knows when to stop

**Goal.** Merge two versions of a file that both started from a common base, as git does for
each file of a merge: take every change that only one side made, take a change both made once,
and stop with a conflict where the two sides changed the same lines differently. A merge that
picks a side silently is a change nobody reviewed.

**Time.** 3 hours.

**What to write** (`merge3.py`):
- `merge3(base, ours, theirs, labels=("ours", "theirs"))`: `(lines, conflicts)` for three lists of
  lines (each with its newline). Use a diff of `base` against each side (`difflib.SequenceMatcher`
  with `autojunk=False` is enough) to find the lines of `base` that both sides keep; between two
  such lines, a side that left the base's lines alone takes the other's, two equal changes are
  taken once, and two different ones are a conflict written as git writes it:
  `<<<<<<< ours`, our lines, `=======`, their lines, `>>>>>>> theirs`, each marker on a line of its
  own.

**Starter.** `starter/merge3.py` compares the three files line by line at the same index and lets
the side that changed win. It is right for a change of one line in place and wrong as soon as a
line is inserted or removed; on a conflict it keeps our line and counts, so the merged file has
no markers.

**Acceptance** (`tests/test_merge3.py`), with `git merge-file -p` as the oracle:
- Clean merges equal git's output: changes far apart; an insertion on one side and a deletion on
  the other, which shift every later line; the same change on both sides; one side unchanged.
- Conflicts are as many as git counts, each between markers: two changes of one line (with the
  lines before and after it kept), a deletion against a change, two insertions at one place,
  changes of two adjacent lines, a conflict with a clean change elsewhere, and two conflicts.

**Then, by hand.**
1. Why do changes of two adjacent lines conflict, when neither side touched the other's line?
2. A clean merge is not a correct program. Write two changes to a C++ file that merge without a
   conflict and do not compile, or compile and are wrong.
3. Who reviews the result of a merge in MiniDAQ's workflow, and what does CI run on it?
