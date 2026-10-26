# Exercise 25.2: notes on the solution

**Parse from the outside in.** Build metadata starts at the first `+` and the pre-release at the
first `-` before it; a hyphen inside an identifier (`x-y`) is then just a character. What is left
must be exactly three numbers. Each rule that the specification states, such as no leading zero and
no empty identifier, has a test, because each is a way for two people to write the same version
differently.

**Comparing numeric identifiers without converting them.** A numeric identifier has no leading zero,
so a longer one is larger, and two of the same length compare as text. That also works for numbers
larger than 64 bits, which the specification does not forbid in identifiers.

**A release is higher than its pre-releases.** `1.0.0-rc.1 < 1.0.0`: the pre-release comes first in
time. The comparison `a.pre.empty() <=> b.pre.empty()` says it in one line, because `true` is
greater than `false`: the side without a pre-release is the greater.

**MiniDAQ's simplification.** `update::Version` compares `rc.10` with `rc.2` as strings and finds
`rc.10` lower, so `0.5.0-rc.10` would be refused as a downgrade of `0.5.0-rc.2`. It is acceptable
while two rules of the release process hold: pre-release labels are only `rc.N` with N from 1 to 9
(the comment in `bundle.hpp` says so), and a pre-release is never installed on a clinical system,
only on test systems (a rule the release procedure has to state; assumption: confirm with team). The
day either rule changes, `update::Version` must get this exercise's comparison, with its tests,
under a change request, because the downgrade check is a risk control. A simplification that is safe
only under a rule is a design decision: write the rule down where the code is, as MiniDAQ does, and
in the release procedure.

**Build metadata.** Two builds of the same version with different `+` metadata have the same
precedence, so they cannot tell the updater which is newer. MiniDAQ records the commit in the
manifest instead, and a reproducible build makes the same commit give the same bytes.
