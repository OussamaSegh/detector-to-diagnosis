# Sorter requirements (fixture for Exercise 15.3, copied from docs/regulatory/srs.md)

| ID | Requirement | Item | Method |
|---|---|---|---|
| SRS-PIPE-010 | The acquisition pipeline shall produce the same coincidences as the single-threaded reference implementation for the same input. | pipeline | T |
| SRS-PIPE-011 | When a downstream stage cannot keep up, the acquisition pipeline shall drop data only at the source, by the configured overflow policy, and count every dropped word. | pipeline | T |
| SRS-PIPE-012 | When a stop is requested, the acquisition pipeline shall process all data already read by the source before its stages finish. | pipeline | T |
| SRS-SRT-001 | The coincidence sorter shall pair two singles whose time difference is less than or equal to the coincidence window, and report the earlier single first. | sorter | T |
| SRS-SRT-002 | The coincidence sorter shall support a fixed window, opened by the first single and not extended, and a window per single, as configured. | sorter | T |
| SRS-SRT-003 | The coincidence sorter shall resolve windows with more than two singles by the configured multiples policy: kill all, take all good pairs, take the good pair with the highest summed energy, or keep the good pair only if it is the only one. | sorter | T |
| SRS-SRT-004 | The coincidence sorter shall reject a pair whose crystals are fewer than the configured minimum of sectors apart, or whose line of response passes outside the configured field-of-view radius in mm. | sorter | T |
| SRS-SRT-005 | The coincidence sorter shall pass only singles inside the inclusive energy window in keV, and count singles that arrive out of time order and drop them. | sorter | T |
| SRS-SRT-006 | When a nonzero delay is configured, the coincidence sorter shall form delayed coincidences from a second window opened at the configured delay in ps after each opening single, using the same window width and multiples policy as the prompt window. | sorter | T |
| SRS-SRT-007 | The coincidence sorter shall reject a configuration with a window outside 1 to 1,000,000 ps, a nonzero delay that does not exceed the window, an energy window that is empty or not finite, a sector difference above 12 sectors, or a field-of-view radius that is not inside the ring. | sorter | T |
| SRS-SRT-008 | The coincidence sorter shall produce the same coincidences whatever the sizes of the batches it receives. | sorter | T |
| SRS-SRT-009 | The coincidence sorter's counters shall account for every single it receives: rejected by energy, out of order, alone, or in a window of a counted size. | sorter | T |
| SRS-SRT-010 | When configured like the simulator's reference counter, the coincidence sorter shall find exactly the prompts that the reference counter finds in the simulator's ground truth. | sorter | T |
| SRS-SRT-011 | The coincidence sorter's delayed window shall estimate the randoms among the prompts to within 15% at 40 MBq. | sorter | T |
| SRS-CFG-011 | The configuration reader shall accept only sorter settings that form a valid coincidence sorter configuration, and apply them to the sorter. | config | T |
| SRS-CTL-012 | When the sort stage counts singles that arrived out of time order, the acquisition service shall end the run in the fault state and report the number of late singles. | service | T |
| SRS-CTL-030 | The acquisition service shall report in its status whether the run's data is complete, list every nonzero loss counter, and report a run with a fault as incomplete. | service | T |
