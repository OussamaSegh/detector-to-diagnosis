# Exercise 21.4: notes on the solution

**What the simulator shows.** With one stage slowed to 30% at 30 s (the poller jitters by up to
20 ms), the slow stage's onset is at about 31 s whichever stage it is. The stages after it
starve one interval later each. The stages before it slow only when the queue in front of the
slow stage is full: 4000 items filling at about 550 items a second take about 7 s, so each stage
upstream slows 5 to 7 s after the next one. With the writer slowed, the source slows at 53 s and
begins to drop at 52 s, 22 s after the cause. The stage that is slow when someone looks is
rarely the stage that slowed first.

**"The writer stopped keeping up at 14:32."** Before agreeing, ask for: the snapshots of every
stage from well before 14:32 (the baseline, to compare rates with), the times they were taken
(not their sequence number: a missed poll doubles an interval), the restarts in the window, and
the queue depths. Then check the order of the onsets. If the writer's rate fell first, the report
is right; if the pair stage's rate fell a second earlier, the writer was starved, not slow.

**What the flight recorder adds.** The snapshots are a sample once a second of counters. The
flight recorder holds the events themselves, with nanosecond times from the process: the
command that started the run, the state changes, the first link gap and the fault, in the order
they happened. A `diagnostics` call at 14:33 or the crash report would have said what happened
in the second the counters average away.
