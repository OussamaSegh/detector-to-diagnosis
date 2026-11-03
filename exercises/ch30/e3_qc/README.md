# Exercise 30.3 (M): Acceptance limits and a trend

**Goal.** Review a series of weekly image quality results against limits from the acceptance
baseline, and find a shift that is too small to leave the limits but never goes away.

**Time.** 45 minutes.

**Starter.** `starter/qc.py` runs. `limits` takes the mean plus and minus `k` population standard
deviations. `review` computes the limits from the baseline and the results together, and reports
only results outside them.

**Acceptance** (`tests/test_qc.py`, a baseline of six results of mean 1.00 and sample SD 0.018):
- The limits are the mean plus and minus 3 sample standard deviations (n - 1), and a baseline of
  fewer than five results is refused with `ValueError`.
- Results within the limits that cross the mean pass with no finding.
- One result outside is reported at its index, and only it.
- A drift of 0.45 SD a week is reported from week 7, when it leaves the baseline's limits.
- A shift of one SD that stays within the limits is reported once, at the seventh result in a row
  below the mean.

**Then, by hand.**
1. Why did the starter miss the drift, and what would it have done to the limits after a year of
   weekly results?
2. With seven in a row, how often does a stable process give a false finding? Simulate it.
3. Section 4 of `measurements/ch30/quality.txt` gives six realizations of the protocol. Set the
   limits for the 12 mm rod's CRC from them, compare them with SRS-IQ-004's, and say what the
   six results can and cannot tell you about the spread. Answer in `NOTES.md`.

**Hints.** The baseline is fixed when the scanner is accepted; the results under review must not
move it. A run counts results on the same side of the baseline's mean and starts again when one
falls on the other side.
