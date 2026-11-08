# MiniDAQ end to end: PASS

2026-11-08T20:58:52Z, commit 517cd49, x86_64, 4 CPUs.

Command: `tools/e2e.py build/release/minidaq/apps /tmp/claude-0/-home-user-detector-to-diagnosis/644a8998-0eec-5556-826b-4d3c34984615/scratchpad/out100/e2e`

## qc (point)

912,139 singles in 5,012 packets; 135,972 prompts and 338 delayed written; end-to-end latency p99 2.28 ms, max 10.32 ms.

| Check | Equation | Values | Result |
|---|---|---|---|
| server: exit status | exit status = 0 | 0 / 0 | pass |
| server: no fault | fault = none | None / None | pass |
| server: no stage dropped a batch | dropped batches = 0 | 0 / 0 | pass |
| server: no late single | late singles = 0 | 0 / 0 | pass |
| link: every packet sent was delivered | packets delivered = packets sent | 5012 / 5012 | pass |
| link: every single sent was delivered | words delivered = singles sent | 912139 / 912139 | pass |
| link: delivered or lost | delivered + lost = packets sent | 5012 / 5012 | pass |
| link: received is delivered or stale | received = delivered + stale | 5012 / 5012 | pass |
| decoder: every word delivered reached the sorter | sorter singles in = words delivered - invalid words | 912139 / 912139 | pass |
| sorter: every single is accounted for | energy rejected + out of order + alone + 2 x pair windows + in multiples = singles in | 912139 / 912139 | pass |
| sorter: every pair window is a prompt or rejected by geometry | prompts + geometry rejected = pair windows | 135980 / 135980 | pass |
| sink: every coincidence was written | written = prompts + delayed | 136310 / 136310 | pass |
| files: the records are the prompts and delayed counted | (prompts, delayed) in the files = (prompts, delayed) of the sorter | [135972, 338] / [135972, 338] | pass |
| sinograms: every record binned or set aside | binned + outside FOV + above ring difference + outside TOF + no angle + invalid = records | 136310 / 136310 | pass |
| integrity: the run says whether it is complete | complete = no damage injected | True / True | pass |
| reference: the server wrote the reference's records | SHA-256 of the records = SHA-256 of the reference's | ccac2cb7d60ce3a2... / ccac2cb7d60ce3a2... | pass |
| QC: the daily QC report passes | QC result = PASS (exit status 0) | PASS / PASS | pass |

Times: reference 1.1 s, acquisition 2.9 s, verify 0.3 s, sinograms 0.1 s, qc 1.9 s.

## phantom (phantom)

4,466,628 singles in 24,542 packets; 134,605 prompts and 6,453 delayed written; end-to-end latency p99 1.59 ms, max 4.22 ms.

| Check | Equation | Values | Result |
|---|---|---|---|
| server: exit status | exit status = 0 | 0 / 0 | pass |
| server: no fault | fault = none | None / None | pass |
| server: no stage dropped a batch | dropped batches = 0 | 0 / 0 | pass |
| server: no late single | late singles = 0 | 0 / 0 | pass |
| link: every packet sent was delivered | packets delivered = packets sent | 24542 / 24542 | pass |
| link: every single sent was delivered | words delivered = singles sent | 4466628 / 4466628 | pass |
| link: delivered or lost | delivered + lost = packets sent | 24542 / 24542 | pass |
| link: received is delivered or stale | received = delivered + stale | 24542 / 24542 | pass |
| decoder: every word delivered reached the sorter | sorter singles in = words delivered - invalid words | 4466628 / 4466628 | pass |
| sorter: every single is accounted for | energy rejected + out of order + alone + 2 x pair windows + in multiples = singles in | 4466628 / 4466628 | pass |
| sorter: every pair window is a prompt or rejected by geometry | prompts + geometry rejected = pair windows | 134836 / 134836 | pass |
| sink: every coincidence was written | written = prompts + delayed | 141058 / 141058 | pass |
| files: the records are the prompts and delayed counted | (prompts, delayed) in the files = (prompts, delayed) of the sorter | [134605, 6453] / [134605, 6453] | pass |
| sinograms: every record binned or set aside | binned + outside FOV + above ring difference + outside TOF + no angle + invalid = records | 141058 / 141058 | pass |
| integrity: the run says whether it is complete | complete = no damage injected | True / True | pass |
| reference: the server wrote the reference's records | SHA-256 of the records = SHA-256 of the reference's | b4413f9b4f199039... / b4413f9b4f199039... | pass |
| image: the cylinder's radius at half its level | abs(radius - 80 mm) <= 2 mm | 80.25 / 80.0 | pass |
| image: flat inside the cylinder (attenuation corrected) | abs(center / periphery - 1) <= 0.1 | 1.0419 / 1.0 | pass |

Times: reference 13.4 s, acquisition 12.9 s, verify 0.3 s, sinograms 0.1 s, reconstruction 0.4 s.

Image: OSEM (C++ projector), 4 iterations of 8 subsets, 128 x 128 pixels of 2 mm; radius at half level 80.25 mm, center over periphery 1.0419, coefficient of variation of 8 mm blocks 0.2014.

