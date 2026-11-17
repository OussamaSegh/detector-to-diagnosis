# Exercise 35.4: notes on the solution

## 1. What the starter accepted

`re.match(r"[0-9.]+", u)` only asks that the string start with a digit or a dot: it accepted
`1..2`, `1.2.`, `.1`, `1.02`, `01.2`, `1.2.a`, `1.2 `, `1.2\n` and `1.2\x00`, and an empty string
only failed because nothing matched. Its `from_uuid` wrote `2.25.f81d4fae...`, letters in a UID.

A pattern anchored as `^...$` and used with `re.match` looks like a whole-string check and is not:
Python's `$` also matches just before a final newline. `tools/dicom/uid.py` had exactly that, so
`valid("1.2.3\n")` was true and the export accepted an order whose study UID ended in a newline,
which SRS-DCM-005 and RC-47 say it refuses. The encoder's CS and UI checks and the version check of
`tools/make_update.py` had the same pattern. Writing this exercise found it: MDQ-PR-084, fixed with
`fullmatch` in all four places, with a test of a trailing newline for each.

## 2. The separator

`"\x1f".join(str(p) for p in parts)` is unambiguous only while no part contains `\x1f`:
`derived("a\x1fb")` and `derived("a", "b")` give the same UID. It also cannot tell `1` from `"1"`.
The callers pass a fixed word, the study UID (digits and dots, checked), a SHA-256 hex digest, a
slice number, the acquisition's start time and its run name. The run name is the only free text;
it comes from the acquisition's metadata, and a control character in it would be unusual but is
not refused. The cheap protection that keeps every existing UID is to refuse a part that contains
the separator, not to change the encoding.

## 3. Why the encoding cannot change

The derived UIDs are an interface with every archive that has received a MiniDAQ series. The
idempotence the chapter relies on, a series sent again after a failure replacing itself instead of
becoming a second series, holds only while the same content gives the same UIDs in every version.
With a new encoding, a series exported by 2.0 and sent again by 2.1 would get new series and
instance UIDs: the archive would store a second, identical series of the same study, and a reader
would see two. That is why `NAMESPACE` is "fixed forever", and the encoding with it; a change would
need a change request that weighs the duplicates against the collision it prevents, and a release
note for every site.
