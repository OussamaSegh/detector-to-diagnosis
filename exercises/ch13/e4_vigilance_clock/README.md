# Exercise 13.4 (M, extra): The vigilance clock

**Goal.** Turn the reporting deadlines for a device incident into code that a complaint
handling tool could use: the three clocks of MDR Article 87, the 30-day and 5-work-day
reports of 21 CFR 803, and the interval of the EU periodic safety update report (PSUR).
Then use it to plan the reports for one incident in both markets.

**Time.** 1 hour.

**Starter.** `starter/vigilance.py`: one EU clock for every incident, work days counted as
calendar days, a PSUR every year for every class, and a plan in the order it was built.

**Acceptance** (`tests/test_vigilance.py`, run by CTest as
`ch13/e4_vigilance_clock/<variant>/unittest`):
- EU, counted in calendar days from the day the manufacturer becomes aware: 2 days for a
  serious public health threat, 10 days for a death or an unanticipated serious deterioration
  of health, 15 days for any other serious incident; an unknown kind is an error.
- US: 30 calendar days for a death, a serious injury or a malfunction that would be likely to
  cause one if it recurred; 5 work days when remedial action is needed to prevent an
  unreasonable risk of substantial harm, or when FDA asks for it. Weekends and the federal
  holidays you pass do not count as work days.
- The PSUR is due at least every 24 months for class IIa and every 12 months for IIb and III;
  class I has no PSUR.
- `report_plan` lists every report that applies, earliest first.

Then write in `NOTES.md` the plan for this incident: on Thursday 7 January 2027 a hospital in
Germany reports that a brain PET acquisition ended without an error, but a quarter of the
coincidences were missing from the list-mode file and the scan was read as normal. Is it a
serious incident? Which clock starts, and when? What would make it a five-day report in the US?

**Hints.** The clock starts when the manufacturer becomes aware, not when the investigation
ends; an initial report can be followed by a complete one. Whether an incident is "serious"
is a judgment your procedure defines, with the regulatory team.
