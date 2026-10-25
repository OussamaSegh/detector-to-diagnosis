# Exercise 18.3: notes on the solution

The two starter tests bin one prompt and validate the default configuration, which leaves 41 of
the 70 branches open: every rejection rule of `validate()`, every outcome of `locate()` except
`binned`, the time-of-flight bins, delayed coincidences, the Michelogram's two conditions and
`collapsed()`. Almost all of them need the same kind of test: one input on the wrong side of
one rule, for each rule. A test of the "normal" path covers the lines of a function and leaves
its decisions half open.

Ten tests take 69 of the 70 branches. Three things needed care:

- `fov_radius_mm` is checked as `!(r > 0.0) || !(r < R)`, so that NaN fails both; a NaN radius
  needs its own case, or the second condition is never shown to matter on its own.
- The time-of-flight rejection has two sides, `tau < -1500` and `tau >= 1500` for three bins of
  1000 ps. Which side a coincidence lands on depends on which crystal is endpoint a, so the test
  swaps the crystals instead of the times to reach the upper side. The edges are half open: a tau
  of exactly -1500 is in bin 0, a tau of exactly 1500 is outside.
- The ring-difference cut has to be reached from both orders of the rings, or the conditional
  `ring_a > ring_b ? ... : ...` stays half open.

The open branch is the `switch (p.outcome)` value that matches no case. It cannot be reached:
`locate()` returns one of the six enumerators, and every one has a case. Adding a `default:` to
cover it would trade a branch nobody can take for the loss of `-Wswitch`, which reports a new
enumerator without a case. That is the kind of branch the review accepts with a reason.

Coverage did not show that any of these tests checks the right thing. A test that called
`locate()` and asserted nothing would reach the same 98.6%; the assertions are what make each test
evidence. Mutation testing (Exercise 18.5) is the check of that.
