# Exercise 13.3: notes

- **Why the DAQ software is IIa.** Implementing rule 3.3 of Annex VIII says that software
  which drives a device or influences its use falls in the same class as the device. The DAQ
  software is part of the scanner, and the scanner is class IIa by Rule 10 ("intended to image
  in vivo distribution of radiopharmaceuticals"). Rule 11, which would look at the impact of a
  wrong decision, applies to software classified in its own right. The seriousness of a wrong
  count still matters: not for the class, but for the risk analysis (Chapter 15) and the
  software safety class of IEC 62304 (Chapter 14), which are separate decisions.
- **Standalone reconstruction software.** Sold on its own for another scanner, it is
  independent of any one device and is classified in its own right, by Rule 11. Its images
  inform diagnostic decisions, so it is at least IIa; whether a wrong image can cause a serious
  deterioration (IIb) is the question for the regulatory team, together with whether it still
  "influences the use" of a scanner it is sold for, which would bring rule 3.3 back (verify:
  MDCG 2019-11 and MDCG 2021-24 on software and on classification).
- **The December 2025 proposal.** The Commission's proposal to revise the MDR would rewrite
  Rule 11 and lower the class of much decision-support software (verify: the text adopted, if
  any). Rule 10 and implementing rule 3.3 are what decide your scanner's DAQ software, and the
  proposal is not expected to apply before 2027.
