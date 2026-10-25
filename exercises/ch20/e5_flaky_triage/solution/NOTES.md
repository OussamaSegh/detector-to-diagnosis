# Exercise 20.5: notes on the solution

**Numbers.** No failure in 10 runs bounds the failure rate only below 31% (95% two-sided); it
takes 299 clean runs to claim "below 1% with 95% confidence". Eight failures in eight runs, as
MDQ-PR-019 failed under load, put the rate above 63%. Fisher's test of 8 of 8 against 0 of 8 gives
p = 1/12,870: the correction changed the behavior, not chance.

**One retry.** A rule that reruns a failed test once reports a test that fails with probability
p as passed with probability 1 - p^2. MDQ-PR-019 failed in about one run of the coverage report
before it was understood, and in every run with the CPUs loaded; on CI machines between the two,
a failure rate of 30% per run would pass 91% of the time with one retry and 97% with two. The
defect, a wrong counter in shipped code, would have stayed. MDQ-PR-020 failed on every GitHub run
and no retry would have hidden it; what hid its cause was a log without the test's output.

**Instead.** Keep the rule that a failure is a failure. A test that fails now and then gets a
problem report, as any defect does, with its measured failure rate and its interval; it is
fixed, or quarantined by a recorded decision that names who fixes it and by when, with the gate
still running it and reporting it. To close the report, the rerun count of task 2 tells how many
clean runs the claim "fixed" needs.
