# Exercise 9.4: notes on the solution

**Walk.** With a fixed threshold of 2% of a 511 keV pulse, a 100 keV pulse crosses tens of
picoseconds later, because its edge rises more slowly in volts per nanosecond. In a scanner
that is a systematic, energy-dependent timing error. It is the same order as the coincidence
time resolution, so it must be corrected (a walk table per energy) or avoided. Constant
fraction avoids it for a fixed pulse shape: every pulse crosses 10% of its own peak at the
same time. Real pulses fluctuate in shape, and many SiPM front ends trigger on the first
few photons at a very low threshold instead, where walk is small. The model here is a
teaching model, not a SiPM simulation.

**ToT.** On the exponential tail, the pulse falls below the threshold at
t_off ≈ τ_decay · ln(A / threshold), so ToT is about τ_decay · ln(A) + constant: logarithmic in
energy. Doubling the energy adds 27.7 ns, whether you start at 300 keV or 30 keV. A ToT
energy measurement is therefore compressed at high energy, and it needs a calibration
curve per channel before an energy window means anything. Some ASICs offer both charge
integration (QDC) and ToT for this reason (verify: which mode the NeuroLF front end uses).

**Precision.** The starter's 50 ps scan quantizes the crossing time to 50 ps, larger than
the walk it is supposed to measure. A measurement tool must be much finer than the effect.
