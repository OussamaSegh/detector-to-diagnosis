# Exercise 14.4 (H): Generate the trace matrix from the code

**Goal.** Build the tool that produces a traceability matrix from requirements to tests out of
the SRS and the `REQ:` tags in the tests, and that fails the build when the trace has a gap.

**Time.** 3 hours.

**Starter.** `starter/trace_matrix.py` parses the SRS and finds C++ tags, but takes only the
first ID of a tag, ignores Python tests, accepts tags for requirements that do not exist or
are withdrawn, and does not ask for evidence when a requirement is verified other than by
test.

**Acceptance** (`tests/test_trace.py`, run by CTest as `ch14/e4_trace_matrix/<variant>/unittest`;
`tests/fixture/` is a small repository with an SRS and two test files):
- `find_tags()` assigns each tag to the C++ `TEST`, `TEST_F` or `TEST_P` or the Python
  `def test_...` above it, and splits a tag that lists several IDs.
- `check()` reports a requirement verified by test without a test, a tag for an unknown or a
  withdrawn requirement, a requirement verified by A, I, D or M without an evidence entry, and
  an ID defined twice. On the fixture it reports nothing.
- `render()` has one row per requirement that is not withdrawn, names tests by file and name
  (never by line number) and evidence by its reference, and is the same whatever order the
  files were scanned in.

Then answer in `NOTES.md`: why does the matrix name tests and not lines, and why is it
committed and checked instead of generated only at release time?

**Hints.** MiniDAQ runs the same tool on itself: `tools/trace_matrix.py . --check` is the test
`docs.trace`, and `docs/regulatory/trace-matrix.md` is its output.
