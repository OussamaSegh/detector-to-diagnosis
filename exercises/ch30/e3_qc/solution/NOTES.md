# Exercise 30.3: notes on the solution

**The drift** (Then, by hand, 1). The starter pooled the results under review with the baseline,
so every week of the drift widened the limits it was judged against: twelve weeks falling 0.45 SD
a week took the pooled SD (the starter's, n in the denominator) from 0.018 to 0.032, and the last
result, 0.911 and 4.95 baseline SDs low, was inside the widened limits, which went down to 0.874. After a year of weekly results the limits would describe the history,
drift included, and nothing short of a step change would leave them. The baseline is fixed at
acceptance, and is set again only by decision, after a change that is itself accepted (a new
calibration, a software update), never by the results it judges.

**False findings** (2). For a stable process, each result is above or below the mean with equal
chance, so a run of seven is a run of seven heads or seven tails: the expected wait for one is
2^7 - 1 = 127 results (a simulation of 20,000 sequences gave 127.9). With weekly checks that is
one false finding in about two and a half years. A run of seven of a process whose mean has
shifted by one SD is far more likely: each result is below the mean with probability 0.84, and
the run comes in about 15 weeks on average (a simulation gave 14.9). The limits alone, at 3 SD, alarm for 0.27% of the
results of a stable process with normal noise and see a one-SD shift in about one result in 44.
Run rules of this kind come from statistical process control (the Western Electric rules use
eight in a row, Nelson's rules nine; verify); the length trades false findings against the time
to see a shift, and is part of the protocol.

**Six realizations** (3). The protocol's 12 mm rod gave a mean CRC of 0.976 and a sample SD of
0.027, so mean plus and minus 3 SD is 0.895 to 1.057. SRS-IQ-004's 0.90 to 1.10 is close below and
looser above, where a higher contrast with the same noise is not a degradation. Six results say
little about the spread: the 95% interval for the true SD is 0.624 to 2.45 times the sample SD
(from the chi-square distribution with 5 degrees of freedom), here 0.017 to 0.066. Limits from six
results are a start; more baseline results narrow them, and a trend rule catches what the wide
limits let through.
