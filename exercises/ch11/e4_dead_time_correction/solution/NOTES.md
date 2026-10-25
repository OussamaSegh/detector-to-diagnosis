# Exercise 11.4: notes on the solution

**The inverses.** Non-paralyzable: m = n/(1 + nτ) gives m + mnτ = n, so n = m/(1 − mτ),
which exists only for m < 1/τ (a unit cannot record more than one event per dead time).
Paralyzable: n e^(−nτ) = m has a solution only for m ≤ 1/(eτ), the value at n = 1/τ, and
below that it has two. The solution bisects on the chosen side of n = 1/τ, where the curve
is monotonic; 200 halvings are far more than double precision needs, and cost nothing.

**Error amplification.** A relative error ε in m becomes (m/n)(dn/dm) ε in n:
- non-paralyzable: dm/dn = 1/(1 + nτ)², m/n = 1/(1 + nτ), so the factor is 1 + nτ;
- paralyzable: dm/dn = e^(−nτ)(1 − nτ), m/n = e^(−nτ), so the factor is 1/(1 − nτ), which
  grows without bound at the maximum, where the measured rate no longer depends on the
  true one.
At nτ = 0.5 the factors are 1.5 and 2. An error in τ itself propagates too: differentiating
the same equations with respect to τ gives factors of nτ and nτ/(1 − nτ) for a relative
error in τ (0.5 and 1 at nτ = 0.5). A dead-time correction is only as good as the dead time
it assumes, and the error grows with the rate.

**Answer to "Afterwards".** With a 0.5% uncertainty in the measured rate, 1% needs a factor of at most 2:
nτ ≤ 1 for the non-paralyzable model (where half the events are lost) and nτ ≤ 0.5 for the
paralyzable one. Past that, the specification has to be met some other way: a shorter τ,
smaller units sharing it, or a measured correction curve (NEMA's count-rate test measures
one) instead of a model.

**On the high branch.** A paralyzable system past its maximum records less as the activity
rises. An operator who sees the count rate fall cannot tell from the rate alone which branch
they are on; the singles rate of a unit with less dead time, or the known activity, decides
it. That is why scanners publish the activity of the count-rate peak and are operated well
below it.
