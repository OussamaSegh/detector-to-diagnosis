# Task given to the agent

Implement `problems(version, subject, released)` in `version_rules.py`. `version` is the text
of the file VERSION, already stripped of the newline that ends the file; `subject` is the
commit's subject; `released` the versions with a release record. The rules (SDP, the release
procedure of Chapter 20):

1. VERSION is exactly `X.Y.Z` or `X.Y.Z-dev`, three numbers, nothing before or after.
2. `X.Y.Z-dev` must be later than the newest release.
3. `X.Y.Z` is allowed only in the release commit, whose subject starts `Release X.Y.Z`, and in
   the commit after it that lists its tag, whose subject starts `Tag book-vX.Y.Z `. In any
   other commit a release version is a problem: the commit after a release sets the next -dev
   version.

Why it matters: the crash report of a build names its version, and an investigator reads the
code of that version.

Add tests.
