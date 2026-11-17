# Exercise 28.4: notes on the solution

Measured with the acceptance tests' data: a 14 mm disc with a 3 mm rod of four times its
activity, 36 views, Poisson counts, the background mask the inner 10 mm without the rod.

## 1. Where the starter stopped

At iteration 1, for every number of subsets. The CoV of the whole image includes the zeros
outside the disc and the rod: after one MLEM iteration it is already 29%, against 6.4% for the
background, and after one iteration of 6 subsets 90% against 9.8%. The starter measured the
contrast of the object, not the noise, and the object is there from the start: any target below
it stops at once, and the image it returns has a rod CRC of 0.16 with MLEM. Because it stops at
the first iteration at or above the target, even with the right mask it would return an image
past the target, one iteration too far.

## 2. Granularity

With 1, 2, 3 and 4 subsets the stop is at 24 updates and 19.6 to 19.8% noise. With 6 subsets the
reconstruction can stop only at 18 or 24 updates, and 24 is at 20.1%, just past the target: it
stops at 18, with 16.5% noise and a CRC of 1.03 against 1.02. The image is a little less noisy
than it could have been, which is the safe side. A target of 25% stops MLEM at 34 updates
(24.6%), 3 subsets at 33, 4 at 32 and 6 at 30 (23.3%), each at the last step of its own size
below the target, with CRCs of 1.00 to 1.02: where a stop falls depends on the step, not on
anything wrong with 6 subsets. The coarser the steps, the further below the target a stop
can be: with 36 subsets of 1 view, the first stop is at 40% noise.

## 3. The smallest subset

At 24 updates, 6 subsets of 6 views have 20.1% noise and a CRC of 1.03, against 19.6% and 1.02
for MLEM: the same image. 12 subsets of 3 views have 21.4% and 1.08, and 18 subsets of 2 views
28.5% and 1.11 at 36 updates: the image is no longer MLEM's. On MiniDAQ's 192 views the same
happened between 16 subsets of 12 views (the same as MLEM) and 32 of 6 (starting to part), with
64 of 3 clearly wrong. What matters is not the count of views but whether a subset still samples
the object fairly from every direction, which depends on the object, the counts and the
geometry. So 6 is a validated number for this test object, not a law: the limit is measured for
the device, as Chapter 28 does, and written into the validated settings.
