# Exercise 13.2: notes

- **"Nothing changed" is the claim to avoid.** The source code is the same, but the program
  that runs is not: a new compiler, new libraries and a new kernel make new binaries with new
  timing. IEC 62304 treats the platform as SOUP, and the risk analysis has to say why each
  hazard that the platform could cause is still controlled.
- **Where the risk is.** For a DAQ, the platform hazards are real and specific: a changed
  network driver or a smaller default receive buffer drops packets; a scheduler change adds
  latency; a file system change alters what survives a power cut. Chapters 4, 9 and 12 built
  tests for exactly these. That is why verification is the system and performance regression,
  not the unit tests.
- **EU.** Under the MDR, the notified body must approve changes to an approved device that could
  affect its safety and performance or the conditions of use (verify: Annex IX, section 4.10,
  and your notified body's change notification procedure). Whether this change needs approval
  before release is the regulatory team's decision; updating the technical documentation is
  not optional either way.
- **US.** FDA's 2017 guidance on software changes walks through questions such as whether the
  change could significantly affect safety or effectiveness and whether it is a change to
  the operating environment. A documented "no new 510(k)" decision is an acceptable outcome;
  an undocumented one is not.
- **Switzerland.** Switzerland recognizes the CE marking; the Swiss authorized representative
  keeps the documentation, and the device's registration in swissdamed must stay correct
  (verify: whether this change touches registered data).
- **The decision.** An engineer prepares the impact analysis; the organization decides through
  its change control process (Chapter 16). The brief makes that decision fast by asking the
  right questions up front.
