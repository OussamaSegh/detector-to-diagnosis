Trace review of the change to minidaq/tests/unit/test_coincidence_sorter.cpp

3. Risk control verification weakened: minidaq/tests/unit/test_coincidence_sorter.cpp, line 403 (in TEST(CoincidenceSorter, EverySingleIsAccountedFor), tagged `// REQ: SRS-SRT-009`).
- What changed: the assertion `EXPECT_EQ(st.singles_in, energy_rejected + out_of_order + singles_alone + 2*pair_windows + singles_in_multiples)` became `EXPECT_GE`.
- Why it matters: the test now passes when singles go missing from the counters. That is exactly the failure SRS-SRT-009 forbids (docs/regulatory/srs.md line 116: the counters "shall account for every single it receives").
- Risk control affected: SRS-SRT-009 is one of the requirements of risk control RC-03 in docs/regulatory/risk/hazards.json ("Every loss is counted where it happens: ... in the sorter"). The trace matrix lists RC-03 against it (docs/regulatory/trace-matrix.md line 251).
- What is left: the test is fixed mode (the default, coincidence_sorter.hpp line 75) with the take_all_goods multiples policy. In that case the identity is no longer checked exactly. The other test on SRS-SRT-009, Properties.EverySingleIsAccountedFor in test_properties.cpp line 429, still checks equality, but only for the policies its generator picks. I did not check whether those include take_all_goods.
- Fix: restore `EXPECT_EQ`; if the identity really fails for take_all_goods, change SRS-SRT-009, RC-03 and the code instead.

No findings of type 1, 2 or 4. The change adds no requirement and no new test. The test it changes still names SRS-SRT-009, which the SRS defines and has not withdrawn. It changes no code of a class B item.

What I read: docs/regulatory/srs.md (the SRS-SRT-009 row), docs/regulatory/trace-matrix.md (the SRS-SRT rows), RC-03 in docs/regulatory/risk/hazards.json, the changed test in context, Properties.EverySingleIsAccountedFor, and the counter identity comment and default mode in minidaq/include/minidaq/processing/coincidence_sorter.hpp.

What I could not check:
- I ran no tests, so I don't know whether the exact identity currently fails for take_all_goods (which may be why the assertion was loosened).
- I did not read the sorter source or the property generator's `sorter_case`.
- I did not read tools/trace_matrix.py or docs/architecture/software-items.json; they were not needed because the test's tag is unchanged and no item code changed.
- RC-03's effectiveness evidence in hazards.json names only SequenceTracker.AccountsForEveryPacketThroughAFaultyLink, so the sorter part of the control relies on the trace-matrix link alone.
