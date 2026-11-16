# Exercise 40.2 (M): The support matrix

**Goal.** Say which release lines are supported on a given day, which release of a line is the
newest, and which SOUP items need an end-of-support plan, by the rules of MiniDAQ's maintenance
plan (sections 3 and 5).

**Time.** 2 hours.

**What to write** (`support.py`), with releases as a list of `(version, "YYYY-MM-DD")` in any
order:
- `supported(releases, on, months=24)`: the minor lines (`"1.3"`) supported on the date `on`. A
  line is supported from the date of its `.0` release for `months` calendar months; a patch
  release does not extend it. A month runs to the same day of the month, or to the month's last
  day when it has none. Lines sort as numbers (`1.3` before `1.10`). A line without its `.0`
  release raises ValueError.
- `latest(releases, line)`: the newest release of a line, by version number. ValueError when the
  line has none.
- `needs_plan(items, review, months=24)`: `items` maps a SOUP item to the date its supplier's
  support ends, or None for no announced end. Return, sorted, the items whose support ends before
  `months` calendar months after the review date.

**Starter.** `starter/support.py` measures a line's support from its newest patch, counts a month
as 30 days, sorts versions as text and keeps an item whose support ends on the horizon itself.

**Acceptance** (`tests/test_support.py`): lines that start, a patch three years later that does
not keep its line alive, the end of a month, `1.10` after `1.3`, `1.3.10` after `1.3.2`, and five
SOUP items over two support periods.

**Then, by hand.**
1. Why does a patch release not extend the support of its line? What would a site on 1.3 expect
   if it did?
2. OpenSSL 3.0's project support ended on 2026-09-07, but Ubuntu 24.04 keeps patching its package
   until 2029. Which date belongs in the SOUP list, and what does the SOUP list say about the other?
3. Three lines supported at once, each with its own maintenance branch: what does each fix of a
   problem relevant to safety cost, and how would you choose the support period?
