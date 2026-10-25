# Exercise 13.1 (E): The standards map

**Goal.** Draw, as one Graphviz diagram, how the regulations and standards that apply to a
PET scanner's software depend on each other: which standard *requires* another (a normative
reference), which only *references* it, which harmonised standards give *presumption* of
conformity with the EU MDR, and which technical report is *guidance* for a standard.

**Time.** 45 minutes.

**Starter.** `starter/standards.dot`, drawn from memory by a colleague: some documents are
missing, editions are not named, and several edges are wrong or point the wrong way.

**Acceptance** (`tests/test_standards_map.py`, run by CTest as
`ch13/e1_standards_map/<variant>/unittest`):
- Every document of the chapter's map is drawn, and its label names its edition (for example
  `ISO 14971:2019`, `IEC 62304:2006+A1:2015`).
- Every edge carries exactly one of the labels `requires`, `references`, `presumption` and
  `guidance`, and no pair is drawn twice.
- The ten dependencies the chapter states are present with the right label, for example
  IEC 62304 *requires* ISO 14971 and only *references* ISO 13485.
- Three edges a colleague drew are gone: ISO 13485 does not require IEC 62304, ISO 14971
  does not require it either, and the MDR names no standard.
- Only the regulation gives presumption, and `dot -Tsvg` renders the file (skipped if
  Graphviz is not installed).

Then write two sentences in a comment at the top of the file: why is the arrow between
IEC 62304 and ISO 13485 only "references", and what does a team without an ISO 13485
certificate have to show instead?

**Hints.** Normative references are listed in clause 2 of each standard. A harmonised
standard is listed in the EU's Official Journal against a regulation, not named by it. Check
the editions against the copies your organization holds: this exercise uses the editions in
force when the chapter was written.
