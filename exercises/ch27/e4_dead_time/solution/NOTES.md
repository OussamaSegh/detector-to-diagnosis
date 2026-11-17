# Exercise 27.4: notes on the solution

**The starter's two mistakes** (Then, by hand, 1). On the paralyzable series it found tau
164 ns, 18% low, and n0 1.5% low. The last point, 77 k true events per second, still loses 1.5%
to dead time, so taking it as the true rate made n0 low, and every `1/m - 1/n` after it was
computed against a wrong `n`. Its tau then came from the non-paralyzable formula on a paralyzable
unit, which needs a smaller tau to explain the same losses at low rates and fails at high ones.
The solution leaves `n0` free and asks for the one tau, per kind, that makes every point agree:
the last point is one equation among thirty, not the anchor of all of them.

**How much the kinds disagree** (2). With tau 200 ns, the paralyzable inverse against the
non-paralyzable one: at 1 M recorded per second, 1.30 M against 1.25 M (4%); at 1.5 M, 2.45 M
against 2.14 M (14%); at 1.8 M, 4.03 M against 2.81 M (43%). Below about 0.1 / tau, a few hundred
thousand per second, the two agree to a percent and the kind hardly matters; near the
paralyzable maximum it is everything. The fit can tell them apart only because the series reaches
those rates: its spread was 0.06% with the right kind and 1.7% with the wrong one.

**1.8 M per second** (3). Below the maximum 1 / (e tau) = 1.84 M, so there are two true rates:
4.03 M on the lower branch, and 6.11 M on the upper. The recorded rate cannot say which; and near
the maximum, a 1% error in the recorded rate is a 6% error in the true rate. A scanner is run
well below the peak of its count-rate curve, and the corrections are validated up to the highest
rate the protocol allows (NEMA NU 2's count-rate test measures that curve).
