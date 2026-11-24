# Release 2.2.0 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage): every
branch and condition that the tests never took both ways on a line of a class B file changed since
release 2.1.0 (tag `book-v2.1.0`). The lines come from the `coverage` build of the release checks
(commit 5647d2e), `coverage/uncovered.txt`, restricted to the lines that
`git diff -U0 book-v2.1.0 5647d2e` adds or changes in class B source. The totals per software
item are in `coverage.txt`.

## Lines changed since 2.1.0

CR-0037 changed three class B items: `config` (`acquisition_config.hpp` and `.cpp`, 65 lines),
`merger` (`node_merge.hpp` and `.cpp`, 94 lines, new) and `readout` (`control/adapters.cpp`,
17 lines). The rest of CR-0037 is in `sim`, which is not shipped and has no class.

| Line | Untaken | Review |
|---|---|---|
| `acquisition_config.hpp:61` | the defaulted `operator==` of `NodeSettings` never finds the counts unequal | Generated comparison; it is used by `to_json` to omit the default, and the tests compare settings only with equal counts or with a default. No requirement depends on the branch. Accepted. |
| `acquisition_config.cpp:42` | `clock_offsets_ps` that is not an array never given | A refusal of SRS-CFG-017 with no test. **Test added**: an offset given as a number is refused (`ReadoutNodesAreRefusedOutOfRangeForUdpAndBefore22`). |
| `acquisition_config.cpp:52` | an offset below -1,000,000 ps never given | The lower half of SRS-CFG-017's range with no test. **Test added**: -1,000,001 ps is refused. |
| `acquisition_config.cpp:213-214` | the conditions after `type != "synthetic"` never false | Defensive: a document whose source type is not synthetic has passed the schema's object checks by then, so `doc` is an object with an object `source`. Accepted. |
| `node_merge.cpp:31` | `end()` of a node that does not exist never called | The explicit check of MDQ-PR-094 with no test. **Test added**: `end(2)` of a two-node merge throws `std::out_of_range` (`CountsALateSingleNeverDropsItSilently`). |

`adapters.cpp` and `node_merge.hpp` have no untaken branch on a changed line.

## Finding

Three refusals had no test; tests were added after the checks, in the commit that records this
review. They change test code only: no shipped source changes, so the checks' results stand.

## Totals

Lines 10,421 of 11,446 (91.0%) and branches 4,583 of 5,634 (81.3%), against 10,232 of 11,252
and 4,503 of 5,548 at 2.1.0; `merger` has 145 of 148 lines and 56 of 60 branches with the node
merge, `config` 547 of 550 lines and 278 of 350 branches.
