# Exercise 35.4 (M): UIDs that are valid, and derived UIDs that cannot collide

**Goal.** The export refuses an order whose study UID is not valid, and derives the series and
instance UIDs from the content, so that the same image gives the same UIDs. Write the three pieces
that rest on: the syntax check, the UID of a UUID under 2.25, and a derived UID that no two
different lists of parts can share.

**Time.** 1 hour.

**Starter.** `starter/uids.py`, with `valid(u)`, `from_uuid(u)` and `derived(*parts)`. It checks
the characters with `re.match(r"[0-9.]+", u)`, writes the UUID in hexadecimal, and joins the parts
with dots before hashing them into a name-based UUID.

**Acceptance** (`tests/test_uids.py`, run by `ctest --test-dir build/debug -R ch35/e4`):
- Valid: a transfer syntax, `0.0`, a 64-character UID. Invalid: empty, `1..2`, `1.2.`, `.1`,
  `1.02`, letters, leading or trailing whitespace, a trailing newline, a NUL, 65 characters, and
  anything that is not a `str`.
- `from_uuid` gives the example of ITU-T X.667,
  `2.25.329800735698586629295641978511506172918`, and `2.25.10` for a UUID whose value is 10.
- `derived` gives the same valid UID, of at most 44 characters, for the same parts, and different
  UIDs for `("1.2", "3")` and `("1", "2.3")`, for `("a", "b")`, `("ab",)` and `("a", "", "b")`,
  for `"1"` and `1`, and for every list of up to three parts from a small alphabet.
- 500 slices of a series get 500 different valid UIDs.
- A part that is a float, `None`, bytes, a bool or a tuple raises `TypeError`; no parts at all,
  `ValueError`.

**Then, by hand.**
1. Which invalid UIDs did the starter accept, and which one does a pattern written `^...$` with
   `re.match` still accept? Look for that pattern in `tools/dicom/`.
2. `tools/dicom/uid.py` joins its parts with the character `\x1f`. When can two different lists
   of parts give the same UID there, and does any caller pass such a part?
3. Why can MiniDAQ not simply replace its `derived()` with yours? What would a series exported by
   2.0 and sent again by 2.1 become?

**Hints.** `re.fullmatch`. Write each part as its type, its length and its text, so that the
concatenation can be read back in only one way. A float's `str` depends on how it was computed.
