# Exercise 15.5: notes

**Releasing 0.3 with H-08 open.** The justification can be written because of what MiniDAQ 0.3
is, not because the risk is small: "MiniDAQ 0.3 is a development release for use with the
simulator and test benches, not at a scanner with patients. H-08 (an unauthorized party
controls the acquisition) cannot lead to harm in that use, because there is no patient.
Authentication of control clients (MDQ-PR-008) is planned for Chapter 17 and is required
before any clinical use." For a release intended for clinical use, the same sentences cannot be
written: an open hazard with an unacceptable risk and no benefit that needs it is a reason not
to release.

**What the matrix shows.** Before control, seven of the nine hazards sit in the unacceptable
S2/P4 cell; H-06 and H-09 are acceptable at S2/P3 and are still reduced as far as possible.
After control, all but H-08 move to P2 or P1. The matrix does not show that every severity is
S2: that is the classification's assumption (class B), and the one judgment that, if wrong,
moves the whole file.
