# MiniDAQ corrective and preventive action

Version 1 (MiniDAQ 0.3.0-dev, Chapter 16). Status: draft for review.

How MiniDAQ finds the cause of a nonconformity and removes it, so that the problem does not
happen again (corrective action), and acts on a cause before it has produced a problem
(preventive action), following what ISO 13485 asks for both, for a teaching project. It is not
a procedure of any manufacturer's quality management system (assumption: confirm with team how the
NeuroLF's CAPA process works and who owns it).

## When a CAPA is opened

A problem report fixes one problem. A CAPA is opened when the cause may produce more of them:

- two or more problem reports with the same cause, or one whose cause is a gap in a procedure,
  a rule or a check rather than a single mistake in the code;
- a finding of an internal or external audit;
- a trend in the post-market data (at the scanner: complaints, service reports).

A problem that is fixed and cannot recur needs no CAPA; the problem report records why.

## Steps

1. **Open.** Copy [template.md](template.md) to `CAPA-NNNN-short-name.md` with the next free
   number. Name the problem reports or the audit finding it comes from, and mark each problem
   report with the CAPA's number (`"capa"` in `problem-reports.json`).
2. **Investigate.** Find every occurrence of the problem, not only the reported ones, and the
   cause: the reason the process let the problem through. "Human error" is not a cause; ask
   why the process allowed the error, and stop at something the organization can change.
3. **Plan the actions.** The correction removes the problems found. The corrective action
   changes the process (a rule, a check, a procedure) so that the cause cannot produce the
   problem again. The preventive action applies the same change where the cause could act but
   has not yet. Each action names the documents or checks it changes.
4. **Verify the actions.** Show that each action was done and that it does not weaken the
   ability to meet a requirement or a risk control.
5. **Check effectiveness.** State, before the actions, the criterion that will show that they
   worked and when it will be checked. A CAPA is closed only when the criterion is met; one
   that fails reopens the investigation.

`tools/check_capa.py` (test `docs.capa`) checks every CAPA: its fields and sections, that the
problem reports it names exist and point back to it, that the actions name files that exist,
that no root cause is "human error", and that a closed CAPA records its effectiveness result.

## Document history

| Version | Change |
|---|---|
| 1 | First version (Chapter 16). |
