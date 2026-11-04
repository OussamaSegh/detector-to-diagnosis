# Exercise 33.3: notes

The starter fails 7 of the 9 tests. Its digest covers the raw row, so a rewrapped or padded row is
a change (and every later comparison of the same row fails with it); it never reports a removed
requirement; and it lets a proposed or rejected request cover a change.

Design choices:

- The digest is taken over the cells after normalizing each one, joined with a separator that
  cannot appear inside a cell. Joining the raw row would make a change of padding a change of
  requirement, and a freeze that cries wolf on every reformatting is a freeze people learn to
  retake without reading.
- A removed requirement is a difference like any other. Deleting a row is the quietest way to
  drop a verified obligation; IEC 62304 expects a withdrawn requirement to be traced, so the
  project marks it "withdrawn" in the SRS rather than deleting it, and the tool reports both.
- Only approved and implemented requests count. A proposed request is an intention and a
  rejected one is a decision against the change: neither authorizes it.

By hand:

1. A digest keeps the baseline small and makes the comparison exact, but the baseline alone
   cannot show what the old text was. The reviewer recovers it from version control at the
   baseline's commit (the baseline's name says which release), so nothing is lost as long as the
   history is kept.
2. Yes: a mention covers a change. Two ways without parsing English: require the request to name
   the change in a structured place (a table "Requirement | added/changed/withdrawn"), or record
   in the request the digest it expects after the change, so a later edit of the same
   requirement is not covered by the old request.
3. At a release, after the review of every difference, by a person. A tool that retook the
   baseline when the check failed would turn the freeze into a record of whatever was last
   written.
