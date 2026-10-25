# Exercise 17.4 (M): Compute what an attack tree says

**Goal.** An attack tree is only as useful as the questions it answers: with the controls in
place, which attacks are left, and which single control, if it failed, would open a new one?
Write the evaluator, check it against the tree of `threat-model.md` (section 4), then draw a
tree of your own.

**Time.** 2 hours.

**Starter.** `starter/attack_tree.py` with TODOs for `leaf_open()`, `minimize()`, `attacks()`
and `critical()`. `tests/stop_scan.json` is the tree of the threat model as data.
`starter/tamper_data.json` is the root of your tree: change a scan's data without it being
noticed.

**Acceptance** (`tests/test_attack_tree.py`, run as `ch17/e4_attack_tree/<variant>/unittest`):
- `attacks()` returns the minimal sets of open leaves that reach a node: OR takes any child, AND
  one attack of every child, and no set contains another.
- On `stop_scan.json`, with every requirement verified and the site's assumptions held, the
  only attack left is filling the disk (3.2); without the assumptions, the operator's account
  appears (1.1.1 with 1.2.8); `critical()` names the requirements whose failure alone opens an
  attack, and SRS-SEC-005 is among them only once the assumptions are dropped.
- `tamper_data.json` has at least five leaves under AND and OR nodes, names SRS-LMF-006 and an
  assumption of the site, is closed with every control in place, and open without the
  assumptions.

Then answer in `NOTES.md`: the tree says the disk can be filled by anyone. Is that a security
problem, a safety problem, or both, and who should fix it?

**Hints.** `itertools.product` gives one attack of every child of an AND node. Minimize after
every node, not only at the root, or the sets grow quickly.
