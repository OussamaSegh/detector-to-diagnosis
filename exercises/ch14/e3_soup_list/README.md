# Exercise 14.3 (M): A SOUP list that matches the build

**Goal.** Write MiniDAQ's SOUP list with version, purpose, requirements, known anomalies and
risk for each item, and a checker that proves the list identifies exactly what the build uses.

**Time.** 2 hours, half of it reading the supplier's release notes.

**Starter.** `starter/soup-list.md` is the list a hurried team writes: names, "latest", no
pins. `starter/soup_check.py` reads git pins only, accepts a branch name as a pin, and does
not check the fields or the review of shipped items.

**Acceptance** (`tests/test_soup.py`, run by CTest as `ch14/e3_soup_list/<variant>/unittest`;
`tests/Dependencies.cmake` is MiniDAQ's file as of Chapter 14):
- `pins()` returns the version and pin of every dependency: the git commit for GoogleTest
  and Google Benchmark, the archive's SHA-256 for nlohmann/json; a branch name is no pin.
- `check()` reports a pin or version that the list does not name, a shipped item without its
  own table, any of the fields Identification, Purpose, Requirements, Known anomalies, Risk and
  Last review missing, and a last review that is not dated `YYYY-MM-DD, for MiniDAQ X.Y` for
  the current minor version.
- `soup-list.md` passes `check()` for MiniDAQ 0.3.0, with nlohmann/json as the shipped item.

Then answer in `NOTES.md`: the team wants to add Eigen for a reconstruction prototype that runs
in the acquisition server. List what you would record and check before the first merge.

**Hints.** Read the supplier's release notes for every release after the pinned one, and
decide for each fix whether MiniDAQ uses the affected feature (`grep` the code). MiniDAQ's own
list is `docs/regulatory/soup-list.md`, checked by `tools/check_soup.py`.
