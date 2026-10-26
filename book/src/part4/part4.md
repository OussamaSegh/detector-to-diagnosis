# Part IV: Testing, verification and quality engineering {.part}

Part IV (four chapters, about 10% of the reading and exercise time) is about the evidence that the
software does what its requirements say. A DAQ engineer writes component and system tests and
collects test data, and as the lead of the DAQ system you will also review the tests of others and
diagnose what fails in the field. In an IEC 62304 project, tests are not a private safety net of the
developer: they are verification records that a reviewer reads, so they must be repeatable, traced
to requirements and honest about what they do not cover.

MiniDAQ has had tests since Chapter 1 and a release process since Chapter 14. Part IV asks how
good those tests are, how they extend from a function to a scanner, how the pipeline that runs
them becomes evidence, and what to do when something fails anyway.

- **Chapter 18** is unit and component testing in C++: test design, test doubles for hardware,
  property-based tests, coverage and mutation testing. MiniDAQ gains a property-based testing
  harness, interaction tests, a coverage report per software item and a mutation testing tool.
- **Chapter 19** is integration, system and hardware-in-the-loop testing: test levels, replayed
  data, soak tests, statistical comparison with golden data, and test protocols and reports a
  reviewer can sign.
- **Chapter 20** is continuous integration for regulated software: pipeline gates, reproducible
  builds, release bundles with their evidence, and the confidence a test tool needs.
- **Chapter 21** is code review, debugging and incident analysis: review checklists for real-time
  and safety-relevant code, debuggers, core dumps and record-and-replay, diagnosing from data,
  and root-cause analysis written up as a problem report.
