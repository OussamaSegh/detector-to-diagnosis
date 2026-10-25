# Exercise 13.3 (E, extra): Which class is it?

**Goal.** Encode the few EU MDR classification rules that decide a PET scanner's class, and
its software's, as a small Python model, then use it to explain why the NeuroLF's DAQ
software is class IIa even though a wrong count could feed a serious diagnosis.

**Time.** 45 minutes.

**Starter.** `starter/classify.py`: a version written in a hurry. It stops at the first rule
that matches, puts all software in class IIa, and forgets that software which drives a device
takes that device's class.

**Acceptance** (`tests/test_classify.py`, run by CTest as
`ch13/e3_classification/<variant>/unittest`):
- A brain PET scanner is class IIa by Rule 10; a CT scanner is class IIb; a PET/CT is IIb,
  and both Rule 10 indents are reported (implementing rule 3.5: the strictest applies).
- Software that drives or influences a device is in that device's class (implementing rule
  3.3), whatever Rule 11 would say about it alone.
- Software on its own follows Rule 11: IIa for information used in decisions, IIb if the
  decision can cause a serious deterioration, III if it can cause death or an irreversible
  deterioration; monitoring software is IIa, or IIb when the patient can be in immediate
  danger; all other software is class I.
- An active device that no special rule covers is class I (Rule 13).

Then answer in `NOTES.md`: the NeuroLF's reconstruction software is sold separately as
standalone software for a second scanner. Which rule now decides its class, and which
question would you ask the regulatory team?

**Hints.** Read Annex VIII of the MDR, implementing rules 3.3 and 3.5 and Rules 10, 11 and
13, and MDCG 2019-11 on software. The model ignores everything that does not matter for a
PET scanner, so it is not a classification tool.
