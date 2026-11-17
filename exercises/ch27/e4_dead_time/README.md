# Exercise 27.4 (M): The kind of dead time, and its tau, from a decaying source

**Goal.** Find a unit's dead-time model and its tau from a decaying source, as a count-rate
measurement does, and invert the model for the true rate, including where a paralyzable unit
has no answer. Chapter 27's correction takes the model's kind and tau as given; this exercise is
where they come from.

**Time.** 60 minutes.

**The measurement.** A fluorine-18 source starts at 3 M true events per second into one unit and
decays for 10 hours; the recorded rate is counted for 10 s every 20 minutes. The true rate is
`n0 exp(-lambda t)` with one unknown, `n0`. Corrected with the right model and tau, the recorded
rates give the same `n0` at every point; with a wrong one, they do not.

**Starter.** `starter/deadtime.py` runs and gives plausible numbers. `recorded_rate` is correct.
`true_rate` uses the non-paralyzable inverse for both kinds. `fit` takes `n0` from the last,
weakest point, assumes dead time is negligible there, averages `1/m - 1/n` for tau, and always
answers non-paralyzable.

**Acceptance** (`tests/test_deadtime.py`, tau 200 ns):
- `true_rate` inverts each model from 1 k to 0.9 / tau true events per second.
- A paralyzable recorded rate above its maximum 1 / (e tau) raises `ValueError`, and so does a
  non-paralyzable one at 1 / tau.
- At 3 M true events per second, 1.65 M recorded: the paralyzable inverse gives 3 M back, the
  non-paralyzable one less than 2.7 M.
- A paralyzable unit's series is recognized as paralyzable, with tau within 2% and n0 within
  0.5%, and a non-paralyzable unit's as non-paralyzable.
- A last point 5% off moves neither tau by more than 3% nor n0 by more than 1%.

**Then, by hand.**
1. What did the starter find for tau and n0 on the paralyzable series, and where did its error
   come from?
2. How much do the two models disagree about the true rate at 1 M, 1.5 M and 1.8 M recorded
   events per second with tau 200 ns? At which rates does the kind matter?
3. A paralyzable unit records 1.8 M per second. What is the true rate, and why should a scanner
   not be run there? Answer in `NOTES.md`.

**Hints.** For a paralyzable unit, `m tau = n tau exp(-n tau)`, so `-n tau` is Lambert's W of
`-m tau` on its principal branch. A model is right when `n(t_i) exp(lambda t_i)` is the same at
every point: minimize its relative spread over tau, for each kind, and compare the minima.
