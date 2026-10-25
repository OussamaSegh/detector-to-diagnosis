# Exercise 13.4: notes

**The plan for the 7 January 2027 report.**

- **Serious?** A serious incident under the MDR is one that led, might have led or might lead
  to death, a serious deterioration of health or a serious public health threat. A normal read
  of a scan with a quarter of the data missing might have led to a missed diagnosis and delayed
  treatment, so the case must be assessed as a potential serious incident, even if no harm is
  known yet. That assessment, not the engineer's opinion, decides; when in doubt the MDR asks
  for a report within the deadline (verify: your procedure and MDCG 2023-3 on vigilance terms).
- **Which clock?** No death and no known serious deterioration: the 15-day clock of Article
  87(3), from the day the manufacturer became aware, 7 January: report by 22 January 2027. An initial
  report can go first and a complete one later.
- **US.** If the same software runs on scanners in the US, the event is assessed under 21 CFR
  803 too. A malfunction that would be likely to cause or contribute to a serious injury if it
  recurred is a 30-day report: 6 February 2027. It becomes a five-day report if remedial action
  is needed to prevent an unreasonable risk of substantial harm (for example, a field action
  to stop scanners until a fix is installed), or if FDA asks for one: by Thursday 14 January.
- **The engineering side.** The DAQ's counters and the run record decide this case quickly:
  were the coincidences lost in the link, in the sorter or in the writer, and did any stage
  count them? A loss that no counter saw is a defect in the risk controls of Chapter 15, and
  the problem report (Chapter 16) must say so.

**Design choices.** Dates, not datetimes: the regulations count days. Holidays are passed in,
because which days are federal holidays changes by year and law; a real tool reads them from a
maintained calendar.
