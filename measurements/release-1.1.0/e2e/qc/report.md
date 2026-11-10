# Acquisition QC: 20261110T090454496Z

Protocol: MiniDAQ acquisition QC, point source at the center, version 1. Result: **PASS**.

135,972 prompts and 338 delayed coincidences in 2.000 s, 18,432 crystals and 45,943 crystal pairs hit.

| Check | Value | Unit | Limit | Result |
|---|---|---|---|---|
| photopeak position | 511.201 ± 0.069 | keV | 505.9 to 516.1 | pass |
| energy resolution (FWHM/E) | 0.11968 ± 0.00037 |  | <= 0.14 | pass |
| photopeak fit, deviance per degree of freedom | 0.9831 |  | <= 2.0 | pass |
| coincidence time resolution (FWHM) | 303.77 ± 0.59 | ps | <= 400.0 | pass |
| timing offset | 2.28 ± 0.35 | ps | |x| <= 25.0 | pass |
| timing fit, deviance per degree of freedom | 1.142 |  | <= 2.0 | pass |
| prompt rate constant (p) | 0.6065 |  | >= 0.001 | pass |
| no dip in the prompt rate (p) | 1 |  | >= 0.001 | pass |
| prompts in the files minus prompts recorded | 0 |  | = 0 | pass |
| coincidences out of time order | 0 |  | = 0 | pass |

Uncertainties are one standard error, from the fit's covariance. Figures: `energy.png`, `timing.png`, `rate.png`. Inputs and environment: `provenance.json`.
