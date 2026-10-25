# Exercise 18.5 (H, extra): Kill the survivors

**Goal.** Run mutation testing on MiniDAQ's sequence tracker (the template part of
`minidaq/include/minidaq/format/readout_packet.hpp`, Chapter 9) with its own tests, then write a
test for each surviving mutant that a test can kill, and argue for each one left that it is
equivalent: that no input can tell it from the original.

**Time.** 3 hours, of which about 15 minutes per mutation run.

**Starter.** `starter/test_tracker_mutants.cpp` has a harness and one test; `starter/survivors.json`
argues for nothing.

**The run.** Configure a `Release` build with the exercises and starters (mutants run the tests
many times, so an optimized build saves most of the time), then run the tool on the tracker's
lines with MiniDAQ's tracker tests and yours:

    cmake --preset release -DMINIDAQ_BUILD_EXERCISES=ON -DMINIDAQ_BUILD_STARTERS=ON
    tools/mutation_test.py minidaq/include/minidaq/format/readout_packet.hpp --lines 186-330 \
        --build build/release --target minidaq_unit_tests ch18_e5_kill_survivors_starter \
        --test "build/release/minidaq/tests/minidaq_unit_tests \
                --gtest_filter='SequenceTracker.*:Properties.TheTrackerRestoresOrderAndCountsEveryPacket' \
                && build/release/exercises/ch18/ch18_e5_kill_survivors_starter" \
        --out exercises/ch18/e5_kill_survivors/starter/mutation-report.txt

(Replace `starter` by `solution` to run the solution.) The tool writes each mutant over the header
and puts the original back when it ends; check `git status` afterwards.

**Acceptance.** Your tests pass on the original (`ch18/e5_kill_survivors/<variant>/...`), and
`ch18/e5_kill_survivors/<variant>/survivors` passes: `tests/check_survivors.py` reads your recorded
report and checks that it is of the header as it is now (the report records the file's SHA-256)
and that `survivors.json` lists exactly the mutants that survived, each with a reason of at least
eight words. A test that kills a survivor removes it from the list; a reason does not.

Then answer in `NOTES.md`: which survivors did MiniDAQ's tests leave, which were real gaps and
which were equivalent, and how you convinced yourself that an equivalent mutant is equivalent.

**Hints.** For a survivor, first ask which input would tell the two versions apart, and only then
whether the specification in the class comment says what should happen for it. A mutant that
changes `>` into `>=` survives when no test sits exactly on the boundary. A mutant in code that only
runs under a condition the tests never create (a full window with nothing held, a wrap during a
resynchronization) survives for want of that condition, not of an assertion.
