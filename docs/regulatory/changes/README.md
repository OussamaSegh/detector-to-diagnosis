# MiniDAQ change control

Version 1 (MiniDAQ 0.3.0-dev, Chapter 16). Status: draft for review.

How a change to MiniDAQ's design is requested, analyzed, decided and recorded, following what
ISO 13485 asks of the control of design and development changes and what IEC 62304 asks of
software change requests, for a teaching project. It is not a procedure of the manufacturer's quality
management system (assumption: confirm with team how the NeuroLF's change control works).

## When a change request is needed

- Every change to a released version, and every change to a requirement, a risk control, a
  software item's class, a SOUP item, an interface or a data format, even before a release.
- Code corrections that a problem report or a CAPA calls for. Changes only to tests, tools
  and procedures that a CAPA calls for are recorded in the CAPA instead.
- Not needed: a change inside one pull request that implements an approved change request, and
  editorial changes to documents (spelling, layout), which still get a new document version.

## Steps

1. **Request.** Copy [template.md](template.md) to `CR-NNNN-short-name.md` with the next free
   number. State what is to change and why, and link the problem report or CAPA if there is one.
2. **Impact analysis.** Fill in every section of the impact analysis, writing "none" with the
   reason where the change has no effect. The analysis is done before the decision, not after
   the code.
3. **Decision.** The software lead approves or rejects, with the date. A change that affects a
   risk control, a safety class or the intended use also needs the risk manager; one that may be
   significant for a notified body or the FDA needs regulatory affairs (Chapter 13).
4. **Implementation and verification.** The pull requests name the change request. The
   verification section lists the tests and checks that show the change works and broke
   nothing; the status becomes `implemented` with the commits.
5. **Record.** The change request stays in this directory for the life of the product.

## Review checklist

Every change, with or without a change request, is reviewed against these questions before it
is merged (SDP section 5):

1. Does the change do what its description, or its change request, says, and nothing else?
2. Do the requirements, the design documents, the tests and the trace matrix still agree? The
   `docs.*` tests answer most of this; the reviewer reads what they cannot check.
3. Is every new or changed behavior covered by a test that fails without the change?
4. Does any controlled document need a new version, and does its history row say what changed?
5. Does the change touch a risk control, a safety class, a SOUP item, an interface or a data
   format? Then it needs an approved change request.
6. Did a problem found while making the change get a problem report?

`tools/check_changes.py` (test `docs.changes`) checks every change request: its fields and
sections, that the requirements, hazards and risk controls it names exist, and that an
implemented change names its commits and tests that exist.

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 16). |
