# Exercise 19.2: notes on the solution

With `k = (z_a + z_b)^2 / n` the condition `n (r - 1) = (z_a + z_b) sqrt(n (1 + r))` becomes
`(r - 1)^2 = k (1 + r)`, a quadratic with the root `r = (2 + k + sqrt(k^2 + 8k)) / 2`. The
starter's formula, `1 + z_a sqrt(2 / n)`, has two errors that partly cancel: it leaves out the
power (it gives the difference found half of the time), and it uses `sqrt(2n)` for the standard
deviation, which is right only at `r = 1`.

The simulation at the computed ratio rejects in about 90% of trials, as it should; without a
difference it rejects in about `alpha` of them, and at 40 counts the exact test rejects less
often than `alpha` (a discrete test cannot hit its level exactly and errs on the safe side).

The golden run of seed 1 counted 229,415 prompts and 2,235 delayed coincidences. At `0.001` and
90% power, the prompt comparison finds a rate change of 1.35%, the delayed comparison only one of
14.15%. A defect that changed the randoms rate by 10%, for example a delayed window opened at the
wrong offset, passes the delayed comparison more often than it fails it. The threshold is not the
lever: at `0.01` the delayed comparison still needs about a 12% change. The lever is the count.
The minimum detectable difference falls as `1 / sqrt(n)`, so a 5% change needs about eight times
the delayed counts: a longer golden run (8 s instead of 1 s), or a configuration that makes more
randoms (a higher rate or a wider delayed window) for that one comparison. The system test plan
should state what each comparison can see, so a reviewer does not read a pass as more than it is.
