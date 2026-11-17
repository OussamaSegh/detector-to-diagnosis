# Exercise 40.4 (M): Is the version we ship affected?

**Goal.** Chapter 40 found that MiniDAQ's OpenSSL is supplied by the distribution, not by the
project: Ubuntu backports fixes into `3.0.13-0ubuntu3.N` without changing the upstream 3.0.13. So
an advisory's upstream range says 3.0.13 is affected, and the package installed may not be. Decide
it as a known-anomaly review must: compare OpenSSL's own versions, letters included, compare
package versions as dpkg does, and let the distribution's advisory decide when it has spoken.

**Time.** 1 hour.

**Starter.** `starter/affected.py`, with `openssl_key`, `upstream_affected`, `debian_compare`,
`upstream_of` and `verdict(package_version, ranges, distro_fixed)`. It drops OpenSSL's letters,
compares package versions as strings and never reads the distribution's fix.

**Acceptance** (`tests/test_affected.py`, run by `ctest --test-dir build/debug -R ch40/e4`):
- `1.0.2zh < 1.1.1 < 1.1.1a < 1.1.1s < 1.1.1t < 1.1.1w < 1.1.1z < 1.1.1za < 3.0.0 < 3.0.9 <
  3.0.13 < 3.0.14`, all distinct; malformed versions are refused.
- With the ranges [1.1.1, 1.1.1t) and [3.0.0, 3.0.14): 1.1.1s and 3.0.13 are affected; 1.0.2zh,
  1.1.1t, 1.1.1w and 3.0.14 are not; an open range has no end.
- dpkg's order: `3.0.13-0ubuntu3.5 < 3.0.13-0ubuntu3.16`, `1.9 < 1.10` in a revision, `~rc1`
  before the release, an epoch above everything else, a letter before `+`, no revision before
  `-0ubuntu1`.
- `3.0.13-0ubuntu3.5` is not affected when the distribution fixed it in `-0ubuntu3.4`, and
  `-0ubuntu3.1` is; without the distribution's advisory the verdict is `affected-upstream`, a
  lead for a person to confirm.

**Then, by hand.**
1. On an Ubuntu 24.04 machine, `dpkg-query -W -f '${Version}\n' libssl3t64`. Which of your
   functions does that version need, and what would the starter have said of it against a
   distribution fix in `-0ubuntu3.5`?
2. Why is `affected-upstream` not the same as `affected`, and what must the review record to turn
   it into one or the other?
3. Where does `distro_fixed` come from, and what does the SOUP list's `Support ends` row (Chapter 40)
   have to do with trusting it in five years?

**Hints.** OpenSSL letters: no letter first, then by the number of letters, then alphabetically.
dpkg: split `epoch:upstream-revision` at the first colon and the last hyphen; compare alternating
runs of non-digits (`~` before the end, the end before letters, letters before other characters)
and of digits (as numbers).
