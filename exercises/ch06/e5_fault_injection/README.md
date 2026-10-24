# Exercise 6.5 (H): Inject faults through the detector port

**Goal.** A DAQ's fault handling is the code that runs least often and matters most. Prove
MiniDAQ's: write an adapter that wraps any `DetectorPort` and makes it fail like real readout
does, then watch the service react, end to end, without hardware.

**Time.** 3 hours.

**Tasks.** Implement `ex::FaultyDetector::read` and `fault()` following `ex::FaultPlan`:
1. **Link down:** after `link_down_after_words` words, deliver nothing and report
   `"link down after N words"` from `fault()`.
2. **Corruption:** replace the crystal id of every `corrupt_every`-th word with 32767, which
   no scanner has. Count them in `FaultCounts::corrupted`.
3. **Stall:** after `stall_after_words` words, deliver nothing for `stall_for`. The inner
   source keeps its schedule, so a backlog builds up, as in a real link that hiccups.
4. **Reordering:** after `reorder_after_words` words, hold back one read's words and deliver
   them only after `reorder_delay_words` newer words.

`fault()` is called from the service's monitor thread while `read()` runs on the source
thread: make the link-down flag safe to share.

**Acceptance tests** (`tests/test_fault_injection.cpp`, using the real `AcquisitionService`
with `make_default_detector` wrapped by your adapter): a clean run completes; link down puts
the service in fault with your message and requires a reset; exactly the corrupted words are
filtered by decode; a 60 ms stall loses nothing yet shows as at least 50 ms of end-to-end
latency; reordered data faults the run as out of time order.

**Think about it.** The stall test passes only because latency is measured from when data
was *due* (Chapter 4). What would the test show if latency were measured from when the
source read the data? And which of these four faults would you also want to inject in a
hardware-in-the-loop test (Chapter 19), because the simulation cannot reproduce it?
