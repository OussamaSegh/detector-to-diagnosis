# Exercise 13.1: notes

- **IEC 62304 and ISO 13485.** IEC 62304 asks for a quality management system and names ISO
  13485 as one way to show it, in a note. So the arrow is "references": a team can conform to
  IEC 62304 with another QMS that covers the same ground, but must then show that it does.
- **IEC 62304 and ISO 14971.** IEC 62304 requires a risk management process that complies with
  ISO 14971 (its clause 4.2). That is a normative dependency: "requires".
- **IEC 60601-1.** For programmable electrical medical systems (PEMS), IEC 60601-1 makes the
  software life cycle of IEC 62304 apply, and its risk management clause applies ISO 14971
  (verify: the clause numbers in your edition).
- **IEC 81001-5-1.** It adds security activities to the software life cycle that IEC 62304
  defines, and its process requirements are based on IEC 62443-4-1. The test accepts
  "requires" or "references" for the edge to IEC 62304, because whether that reference is
  normative depends on which clauses you read (verify: clause 2 of your copy).
- **Presumption.** The MDR (Article 8) gives presumption of conformity to devices that meet
  harmonised standards whose references are published in the Official Journal. The list
  changes by implementing decision; at the time of writing it contained EN ISO 13485, EN ISO
  14971 and EN 60601-1, and not EN 62304 or EN IEC 81001-5-1 (verify: the current list on the
  Commission's harmonised standards page). A standard that is not harmonised is still the
  state of the art, and notified bodies expect it.
- **What the test cannot check.** Whether an edge is right depends on the edition. When a new
  edition of IEC 62304 is published (the IEC expects late 2028, verify), redraw the map.
