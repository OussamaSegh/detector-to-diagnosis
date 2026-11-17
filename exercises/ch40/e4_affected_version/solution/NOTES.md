# Exercise 40.4: notes on the solution

## 1. A real package version

The book's reference container (Ubuntu 24.04) has `libssl3t64` and `openssl` at
`3.0.13-0ubuntu3.16`. Its upstream part, 3.0.13, is inside every upstream range of an advisory
fixed in 3.0.14 and later, so the upstream ranges alone call it affected; the question is answered
by `debian_compare` against the version the distribution's advisory names. The starter compares
package versions as strings, and as strings `3.0.13-0ubuntu3.16` sorts before `3.0.13-0ubuntu3.5`
(the character `1` before `5`): against a fix in `-0ubuntu3.5` it would have called the installed
package affected, eleven updates after it was fixed. The opposite mistake is as easy: string order
puts `0ubuntu1.9` after `0ubuntu1.10`, so a package still missing a fix in `.10` would pass.

The comparison was checked against `dpkg --compare-versions` (dpkg 1.22.6) on 400 random pairs of
versions built from digits, letters, `~`, `+`, `.` and epochs: no disagreement.

## 2. A lead, not a verdict

`affected-upstream` says that the project's own version would be affected. Whether the installed
package is depends on what the distribution did, which only its advisory says: a backported fix, a
build without the affected feature, or "not affected" because the vulnerable code is not compiled
in. The review records the distribution's advisory (for Ubuntu, the USN and the package version it
names, or the CVE tracker's status for the release), the installed version, and the comparison;
without them the item stays open as `affected-upstream`, never closed as not affected by default.

## 3. Trusting distro_fixed

It comes from the distribution's security notices, which Chapter 40's plan for OpenSSL now reads
first. It is only as good as the distribution's support for that release: after the standard
support ends, fixes stop or move to a paid channel (Expanded Security Maintenance), and a missing
`distro_fixed` then means nobody will fix it, not that nobody has looked. The `Support ends` row is
what makes that date visible at every review, so that the verdict function is not trusted past the
point where its input stopped arriving.
