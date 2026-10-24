# Exercise 10.2: notes on the solution

**One list, four rules.** Every policy is a rule over the list of good pairs in the
window: none, all, exactly one, or the best by energy. Building the list once keeps the
four in step: they cannot disagree about which pairs are good.

**What the measurements show** (`measurements/ch10/validation.txt`, sectors at least 1
apart, 120 mm field of view, book VM, seed 21). At 40 MBq, take all goods finds 379,260
trues/s against 358,920 for kill all, about 6% more, but its prompts are 22.5% randoms
against 18.6%: most of what it adds from multiples is randoms, because a window of three
holds at most one true pair and two or more random ones. Take the winner of goods sits
between them (368,660 trues/s, 20.4%). At 1 MBq, where multiples are rare (16 windows per
second), the policies differ by less than counting noise.

**Why `keep_if_only_one_good` equals `kill_all` without cuts.** Without a geometry cut
every pair is good, so a window of three has three good pairs and never exactly one.

**The randoms estimate depends on the policy.** The delayed window counts randoms for
every opener, whatever its prompt window held. With kill all, a random that shares its
window with a true pair is discarded from the prompts but still counted in the delayed
window, so the estimate is high (+5.0 ± 1.9% at 40 MBq); with take all goods, such a
window adds two random pairs to the prompts, so the estimate is low (−8.1 ± 1.6%). A
randoms correction for an image has to model this, or use a policy and an estimator that
match (verify: Oliver and Rafecas, PLoS ONE 2016, compare estimators in the presence of
multiples).

**Choice.** For a brain scanner, where the activity in the field of view is moderate,
take the winner of goods is a reasonable default: it recovers some trues from multiples
with fewer added randoms than take all goods. The decision belongs to the physics team
together with the reconstruction's randoms model (assumption: confirm with team).
