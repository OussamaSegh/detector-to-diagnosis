# Exercise 37.1 (E): Nothing of the patient leaves

**Goal.** Before an image header goes into an assistant's context, a bug report or a test
fixture, take the patient out of it: keep what the problem needs (geometry, units, timing),
replace what identifies a person with values that are consistent but not the person's, and drop
everything else. An assistant's context is data sent outside the device; patient data does not go
there.

**Time.** 1 hour.

**What to write** (`deidentify.py`), for a header given as a dictionary of DICOM keywords to
string values:
- `deidentify(header, key)`: a new dictionary that holds only the keywords of `KEEP` (unchanged),
  of `PSEUDONYMS`, `DATES` and `UIDS`; everything else is dropped, whatever it is called.
  - `PatientName` and `PatientID` become `ANON^` and `ANON-` followed by the first 10 hexadecimal
    characters of the HMAC-SHA256 of the patient ID with `key`: the same patient gets the same
    pseudonym in every file, and nobody without the key can go back.
  - Every date of `DATES` (`YYYYMMDD`) moves back by the same number of days for one patient,
    from 1 to 365, derived from the same HMAC: intervals between dates stay exact. `PatientBirthDate`
    is dropped, not shifted.
  - Every UID of `UIDS` becomes `2.25.` followed by the decimal value of the first 16 bytes of the
    HMAC-SHA256 of the UID with `key`: the same UID gives the same new UID, so a series still
    refers to its study.
- `KEEP`, `PSEUDONYMS`, `DATES`, `UIDS`: the lists, given in the starter.

**Starter.** `starter/deidentify.py` deletes `PatientName` and `PatientID` and keeps the rest.

**Acceptance** (`tests/test_deidentify.py`):
- No value of the original that identifies (name, ID, birth date, institution, physician,
  accession number, other IDs, comments, the original UIDs and dates) appears anywhere in the
  output, and a keyword the lists do not name is dropped.
- The kept attributes are unchanged; pseudonyms are stable for one patient and key and differ
  for another patient or key; the days between two dates are the same; UIDs are valid (digits and
  dots, at most 64 characters) and the same input UID gives the same output.

**Then, by hand.**
1. Why a list of what to keep and not a list of what to remove?
2. What in an image header can still identify a person after this (think of the pixels, burned-in
   text, a rare tracer at a small site, the date of an unusual scan)?
3. Where does your team's guidance say patient data may and may not go? Does it name AI tools?
