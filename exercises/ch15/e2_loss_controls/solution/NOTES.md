# Exercise 15.2: notes

| Control | Type | Requirement | Implementation verified by | Effectiveness verified by |
|---|---|---|---|---|
| Acquisition invalidation | Protective | The acquisition service shall report a run with any nonzero loss counter, or a fault, as incomplete, and list the nonzero counters. | `Assess.EveryLossCounterInvalidatesTheRun`, `Assess.AFaultInvalidatesTheRunWithoutALossCounter` | A run with a real loss through the whole service is marked incomplete in its record (MiniDAQ: `AcquisitionService.ALossMakesTheRunIncomplete`). |
| Loss alarm | Protective | When more than the configured fraction of packets is lost between two status updates, the acquisition service shall raise a loss alarm that stays raised until acknowledged. | `LossAlarm.*` | An operator in a usability test notices the alarm and acts on it (IEC 62366-1); a unit test cannot show that. |

The invalidation is MiniDAQ's RC-01: it acts on the data, which outlives the run, and does
not depend on anyone watching the screen. The alarm reduces the probability further by letting
the operator repeat a scan while the patient is still there, but its effectiveness depends on
a person, so its evidence is a usability evaluation, not a unit test.

Both are protective measures: they detect the loss and do not prevent it. The inherent control
for the same hazard is backpressure in the sink (RC-04), which removes one cause of loss.
