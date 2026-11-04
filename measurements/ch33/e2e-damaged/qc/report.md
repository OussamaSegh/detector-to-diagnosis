# Acquisition QC: 20261104T074233864Z

Protocol: MiniDAQ acquisition QC, point source at the center, version 1. Result: **PASS**.

135,569 prompts and 335 delayed coincidences in 2.000 s, 18,432 crystals and 45,885 crystal pairs hit.

| Check | Value | Unit | Limit | Result |
|---|---|---|---|---|
| photopeak position | 511.196 ± 0.069 | keV | 505.9 to 516.1 | pass |
| energy resolution (FWHM/E) | 0.11966 ± 0.00037 |  | <= 0.14 | pass |
| photopeak fit, deviance per degree of freedom | 0.9921 |  | <= 2.0 | pass |
| coincidence time resolution (FWHM) | 303.77 ± 0.59 | ps | <= 400.0 | pass |
| timing offset | 2.29 ± 0.35 | ps | |x| <= 25.0 | pass |
| timing fit, deviance per degree of freedom | 1.133 |  | <= 2.0 | pass |
| prompt rate constant (p) | 0.2879 |  | >= 0.001 | pass |
| no dip in the prompt rate (p) | 1 |  | >= 0.001 | pass |
| prompts in the files minus prompts recorded | 0 |  | = 0 | pass |
| coincidences out of time order | 0 |  | = 0 | pass |

Uncertainties are one standard error, from the fit's covariance. Figures: `energy.png`, `timing.png`, `rate.png`. Inputs and environment: `provenance.json`.
