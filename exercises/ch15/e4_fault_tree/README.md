# Exercise 15.4 (M, extra): The minimal cut sets of the data-loss fault tree

**Goal.** Compute the minimal cut sets of a fault tree, apply it to the tree of hazard H-01
(`docs/regulatory/risk/fault-tree-data-loss.dot`), and find what the drawing hides.

**Time.** 1.5 hours.

**Starter.** `starter/cutsets.py` multiplies the tree out: it keeps duplicates, counts a
repeated event twice, keeps sets that contain smaller cut sets, loops forever on a cycle and
treats any gate that is not "or" as "and".

**Acceptance** (`tests/test_cutsets.py`, run by CTest as `ch15/e4_fault_tree/<variant>/unittest`):
- `minimal_cut_sets()` returns each minimal cut set once, as a sorted tuple, sorted by order and
  then by name; a repeated event counts once; supersets of a cut set are absorbed; a cycle or
  an unknown gate type raises `ValueError`.
- The data-loss tree (`tests/data-loss.json`) has 15 minimal cut sets of order 2 and no single
  point of failure; drawn with the dependency that E5 also causes E6, it has one: E5.

Then answer in `NOTES.md`: what does the single point of failure mean for MiniDAQ's controls,
and which control acts on it?

**Hints.** Expand the tree top-down: an OR gate gives the union of its inputs' cut sets, an AND
gate the combinations of one set from each input. Minimize at the end with frozensets.
