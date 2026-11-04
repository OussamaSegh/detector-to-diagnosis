# Exercise 37.1: notes

The starter fails four of the five tests. It removes the two attributes everyone thinks of and
keeps the other eight that identify the patient in this header alone: the birth date, other IDs,
a comment, the institution, the referring physician, the accession number, a description with the
patient's first name, and a private attribute whose name says nothing and whose value is the
patient's name.

Design choices:

- A list of what to keep. A list of what to remove is always one attribute short: private
  attributes, a vendor's comment field, a description someone typed. An unknown attribute is
  dropped, and a person who needs it adds it to the list after looking at what it holds.
- A keyed hash (HMAC), not a plain hash: a patient ID has few possible values, and anyone can hash
  every one of them and look the result up. Without the key, the pseudonym says nothing; with it,
  the site can map back if it must, and the key is managed like any other secret.
- One shift per patient for every date, derived from the same HMAC: the decay between the study
  and the acquisition, the days between two scans and the order of series stay right; the
  calendar dates do not. The birth date is dropped, since an age is rarely what a defect needs.
- UIDs are remapped, not dropped: a series must still refer to its study and its frame of
  reference, and a consistent mapping keeps every reference consistent.
- To the questions: DICOM part 15's Basic Application Level Confidentiality Profile works the
  same way, with a table of every attribute and an action for each, and options to retain dates
  or UIDs. Pixels can carry burned-in text (screenshots, scanned forms), a face can be rebuilt
  from a head CT, and a rare combination (a tracer, a site, a date) can identify a person in a
  small population. The test of an export is whether the data still identifies someone, not
  whether the attributes are gone. A team's guidance on AI tools names where data may go; if it
  does not mention patient data in prompts and context, ask.
