# Release 2.3.0 structural coverage review

The review that the development plan asks of a release (SDP section 6, structural coverage): every
branch and condition that the tests never took both ways on a line of a class B file changed since
release 2.2.0 (tag `book-v2.2.0`). The totals per software item are in `coverage.txt`, from the
`coverage` build of the release checks (commit 1926017).

## Lines changed since 2.2.0

`git diff book-v2.2.0 1926017` changes no class B source. The only shipped-tree source change is
the indentation of two lines of `minidaq/src/sim/synthetic_source.cpp` (MDQ-PR-102), in `sim`,
which is not shipped and has no class; the version string of `recon/python/pyproject.toml` is
not code. The release's changes are in the tools, the tests, the book and its figures.

## Finding

No class B line changed, so no untaken branch is to review.
