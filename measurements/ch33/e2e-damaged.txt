# MiniDAQ end to end: PASS

2026-11-04T07:42:32Z, commit 392e4ae, x86_64, 4 CPUs.

Command: `tools/e2e.py build/release/minidaq/apps measurements/ch33/e2e-damaged --loss 0.002 --reorder 0.002 --duplicate 0.002 --activity 2e6 --no-image`

## qc (point)

912,139 singles in 5,012 packets; 135,569 prompts and 335 delayed written; end-to-end latency p99 3.05 ms, max 15.83 ms.

| Check | Equation | Values | Result |
|---|---|---|---|
| server: exit status | exit status = 0 | 0 / 0 | pass |
| server: no fault | fault = none | None / None | pass |
| server: no stage dropped a batch | dropped batches = 0 | 0 / 0 | pass |
| server: no late single | late singles = 0 | 0 / 0 | pass |
| link: delivered or lost | delivered + lost = packets sent | 5012 / 5012 | pass |
| link: received is delivered or stale | received = delivered + stale | 5015 / 5015 | pass |
| decoder: every word delivered reached the sorter | sorter singles in = words delivered - invalid words | 909591 / 909591 | pass |
| sorter: every single is accounted for | energy rejected + alone + 2 x pair windows + in multiples = singles in | 909591 / 909591 | pass |
| sorter: every pair window is a prompt or rejected by geometry | prompts + geometry rejected = pair windows | 135577 / 135577 | pass |
| sink: every coincidence was written | written = prompts + delayed | 135904 / 135904 | pass |
| files: the records are the prompts and delayed counted | (prompts, delayed) in the files = (prompts, delayed) of the sorter | [135569, 335] / [135569, 335] | pass |
| sinograms: every record binned or set aside | binned + outside FOV + above ring difference + outside TOF + no angle + invalid = records | 135904 / 135904 | pass |
| integrity: the run says whether it is complete | complete = no damage injected | False / False | pass |
| integrity: the loss is named | packets_lost in the losses | /detector_counte... / ['/detector_coun... | pass |
| QC: the daily QC report passes | QC result = PASS (exit status 0) | PASS / PASS | pass |

Times: reference 1.3 s, acquisition 2.9 s, verify 0.4 s, sinograms 0.2 s, qc 2.1 s.

## phantom (phantom)

1,786,818 singles in 9,818 packets; 52,712 prompts and 1,042 delayed written; end-to-end latency p99 1.73 ms, max 4.86 ms.

| Check | Equation | Values | Result |
|---|---|---|---|
| server: exit status | exit status = 0 | 0 / 0 | pass |
| server: no fault | fault = none | None / None | pass |
| server: no stage dropped a batch | dropped batches = 0 | 0 / 0 | pass |
| server: no late single | late singles = 0 | 0 / 0 | pass |
| link: delivered or lost | delivered + lost = packets sent | 9818 / 9818 | pass |
| link: received is delivered or stale | received = delivered + stale | 9829 / 9829 | pass |
| decoder: every word delivered reached the sorter | sorter singles in = words delivered - invalid words | 1784452 / 1784452 | pass |
| sorter: every single is accounted for | energy rejected + alone + 2 x pair windows + in multiples = singles in | 1784452 / 1784452 | pass |
| sorter: every pair window is a prompt or rejected by geometry | prompts + geometry rejected = pair windows | 52760 / 52760 | pass |
| sink: every coincidence was written | written = prompts + delayed | 53754 / 53754 | pass |
| files: the records are the prompts and delayed counted | (prompts, delayed) in the files = (prompts, delayed) of the sorter | [52712, 1042] / [52712, 1042] | pass |
| sinograms: every record binned or set aside | binned + outside FOV + above ring difference + outside TOF + no angle + invalid = records | 53754 / 53754 | pass |
| integrity: the run says whether it is complete | complete = no damage injected | False / False | pass |
| integrity: the loss is named | packets_lost in the losses | /detector_counte... / ['/detector_coun... | pass |

Times: reference 5.9 s, acquisition 7.1 s, verify 0.1 s, sinograms 0.3 s.

