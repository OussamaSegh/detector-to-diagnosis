# Exercise 16.5 (E): Document control between two releases

**Goal.** `tools/design_file.py --since` asks git whether a controlled document changed without a
new version. Write the same check for two releases given as files, with the rules that git
alone does not see.

**Time.** 45 minutes.

**Starter.** `starter/doc_control.py` reads a document's version and its history table and only
reports documents without a version.

**Acceptance** (`tests/test_doc_control.py`, run by CTest as
`ch16/e5_document_control/<variant>/unittest`). `problems(old, new)`, for two releases given as
`{path: text}` (the fixtures in `tests/old/` and `tests/new/`), reports:
- a document without a version, and one whose version is not the last row of its history;
- history rows that are not numbered 1, 2, 3 ... without gaps;
- a document that changed but kept its version, and one whose version went down;
- a history row of the old release that the new one changed or removed;
- a new document that does not start at version 1, and a document that disappeared.

Two versions in one release are allowed (the SDP of the fixture goes from 1 to 3), and an
unchanged document keeps its version. The fixture release has no problems.

Then answer in `NOTES.md`: why may a history row never be corrected, even for a typo?

**Hints.** Compare texts, not dates: a document that is byte-for-byte the same has not changed.
The history of the new release must contain every row of the old one, unchanged.
