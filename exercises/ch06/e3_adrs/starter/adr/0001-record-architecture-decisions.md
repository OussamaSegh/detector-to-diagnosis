# 0001. Record architecture decisions

Date: 2026-10-24
Status: Accepted

## Context

MiniDAQ is meant to live as long as the scanner it serves: ten years or more, with several
generations of developers. Most of what a newcomer needs to know about the design is not in
the code but in why the code looks the way it does: which alternatives were considered, what
was measured, and what the team accepted as the price. In regulated development this
reasoning is also evidence: the software architecture must be documented and its design
decisions must be traceable (Chapter 14).

## Options

1. **Nothing written; the reasoning lives in people's heads and in review comments.** Free
   today, lost the first time someone leaves.
2. **A single, continuously edited design document.** Good for the current state, but edits
   erase history, and nobody can tell which paragraph was a decision and which a description.
3. **Architecture decision records (ADRs)**, as described by Michael Nygard (2011): one short,
   numbered, immutable file per decision, kept in the repository next to the code.

## Decision

We use ADRs (option 3) in `docs/adr/`. Each record has a title line `# NNNN. Title`, a
`Date:` line, a `Status:` line (Proposed, Accepted, Rejected, Deprecated, or Superseded by
NNNN), and the sections Context, Options (at least two), Decision and Consequences, the last
with Positive and Negative subsections. A record is written in the same change as the code
that implements it, and is reviewed with it. The architecture description
(`docs/architecture/architecture.md`) states the current design and links the records that
explain it.

## Consequences

### Positive

- The history of the design is in version control, reviewed like code, and survives people.
- A reviewer can challenge a decision against its stated context instead of against taste.
- Changing a decision is cheap and visible: a new record supersedes the old one.

### Negative

- Writing a record costs 30 to 60 minutes per decision, and someone has to judge what is a
  decision worth recording.
- Records describe the context at the time; a reader must check the Status line and follow
  "Superseded by" links.
