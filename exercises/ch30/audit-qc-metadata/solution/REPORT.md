# Audit report: the agent's read_metadata (Exercise 30.5)

Not mergeable. `int(...)` does not check a type, it converts one: some values become integers
they never were, and the others raise exceptions the tool does not catch. Both defects are
MiniDAQ's own: the QC report had them until the internal audit before release 2.0.0.

## Defect 1: a field of another type ends the report with a traceback (MDQ-PR-076)

`records` that is a list has no `.get` (AttributeError); a window or a crystal count that is a
list, an object or null makes `int()` raise TypeError; `scanner` that is a string makes
`["crystals"]` raise TypeError. None of these is `FormatError`.

- *Test:* `test_scanner_or_records_that_is_not_an_object_is_an_error`, and the list, object
  and null cases of `test_a_window_of_any_other_type_or_value_is_an_error`.
- *What the technologist sees:* a Python traceback instead of "error: records is not an
  object", and no QC result for the day. MDQ-PR-071 found the same class of defect in the
  analysis package's verify_run.
- *Correction:* check that each object is a dict before reading from it, and each integer's
  type, and raise `FormatError` naming the field.

## Defect 2: text, booleans and fractions are taken as integers (MDQ-PR-076)

`int("100000")` is 100000, `int(True)` is 1 and `int(2.5)` is 2. The specification says a
string of digits, a boolean or a fraction is not an integer. A writer that put the window in
quotes, or a damaged file with `true`, gives a report computed with a window nobody chose: a
delayed window of 1 ps estimates almost no randoms.

- *Test:* the string, true, false and fraction cases of
  `test_a_window_of_any_other_type_or_value_is_an_error` and its twin for the crystals.
- *Correction:* `type(value) is int` (a bool is an int subclass, so `isinstance` is not
  enough), then the range.

## Verdict

Request changes. The agent's five tests used only well formed metadata and missing keys: a
test set for a reader of a file must put every JSON type in every place the reader looks.
"Every path that can fail raises FormatError" was not checked by any of them.
