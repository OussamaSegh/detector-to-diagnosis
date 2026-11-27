# Audit report: the agent's loss counter (Exercise 23.5)

Not mergeable. Two counters can say something false, and both defects are MiniDAQ's own,
from its sequence tracker.

## Defect 1: a jump of 2^31 is counted as two billion lost packets (MDQ-PR-002)

The signed distance is undefined in meaning at exactly 2^31: `static_cast<std::int32_t>` gives
INT32_MIN in both directions, which is neither "late" (> 0) nor "too far ahead" (> max_gap).
The code falls through to the gap branch and adds 2,147,483,648 to `lost`.

- *Test:* `Audit.AJumpOfExactlyTwoToThe31IsARestartNotTwoBillionLost`.
- *What the operator reads:* two billion packets lost, on a link that lost none and only
  restarted. A counter that absurd is ignored, and with it the real loss it hides; the
  evaluation of MDQ-PR-002 calls that safety relevant for this reason.
- *Correction:* work with the unsigned distance and decide the half explicitly: below 2^31 is
  ahead, 2^31 and above behind, and anything outside the window or the maximum gap, 2^31
  included, a restart. The agent's claim that `sequence_distance` "keeps the arithmetic defined
  everywhere" is the mistake: it is defined, and it has no meaning at 2^31.
- *How it was found in MiniDAQ:* `fuzz_packet` (Chapter 7's method on Chapter 9's code).

## Defect 2: a late copy of a received packet is counted as reordered (MDQ-PR-019)

The late branch counts `reordered` before it looks at the bitmap. A packet that the link both
delayed and duplicated lands in `reordered` and `stale`. The specification says reordered
means the packet filled its gap, and that each packet counts in one category.

- *Test:* `Audit.ALateCopyOfAPacketAlreadyReceivedIsStaleNotReordered`, and
  `ACopyIsStaleOnly`.
- *What the operator reads:* reordering that did not happen. In MiniDAQ the case became
  common under load, when packets were held longer, and the readout system test failed 8 of
  8 runs with the CPUs loaded.
- *Correction:* check for a copy first; count reordered only for a packet that is used.

## Verdict

Request changes. "No edge case left" is a claim about the tests, and the tests tried one copy
in order and one late packet, never both at once, and no distance at the type's edge.
