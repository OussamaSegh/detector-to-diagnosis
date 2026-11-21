# Chapter 6: how long the out-of-order fault test takes

Chapter 6 says that `AcquisitionService.OutOfOrderSinglesAreAFault` exercises the sort stage's
late-single counter, the service's monitor, the state machine and the status report "in 10 ms".
`run.sh` runs it 20 times in the release and the debug build and writes the times GoogleTest
reports to `fault-test.txt`:

    measurements/ch06/run.sh

Every run took 8 ms or less (median 5 ms in release, 2.5 ms in debug). The debug build is not
slower because the test's time is spent waiting for the service's monitor and the run's end,
not computing. GoogleTest reports whole milliseconds.
