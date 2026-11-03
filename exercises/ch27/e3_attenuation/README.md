# Exercise 27.3 (S): A head outline and the decay of a frame

**Goal.** Compute the attenuation correction of a head modeled as an ellipse of water, off center
and turned, as a calculated attenuation correction does when there is no CT, and the decay factor
of a frame. `tools/recon` models only a centered cylinder.

**Time.** 60 minutes.

**Starter.** `starter/attenuation.py` runs. `chords` uses a circle of the ellipse's mean radius,
`acf` takes mu in 1/cm and the chord in mm, and `decay_factor` corrects for the decay up to the
start of the frame.

**Acceptance** (`tests/test_attenuation.py`; a line is its angle phi and its signed distance s
from the center, lengths in mm):
- `chords` of a circle: `2 sqrt(R^2 - s^2)`.
- `chords` of 40 random ellipses, off center and turned, against the length measured by walking
  along the line in steps of 5 um: within 0.05 mm.
- A head 160 mm wide and 200 mm long, turned 20 degrees: 200 mm along its long axis and 160 mm
  across.
- `acf` of 200 mm of water at 0.096 per cm: `exp(1.92)`.
- `decay_factor`: 1 at the reference time, 2 one half-life later, `2 ln 2` for a frame one
  half-life long; frames of 1 to 30 minutes of the same source all give the same activity.

**Then, by hand.**
1. What is the attenuation correction factor of the line through the center of a head 180 mm
   across? If the outline is drawn 5 mm too large all round, how wrong is that line after the
   correction?
2. A frame from 60 to 70 minutes after the reference time, fluorine-18 (half-life 109.77 min):
   the decay factor, the starter's, and the factor at the middle of the frame. Which shortcut is
   good enough, and for which frames is neither?
3. Why does the attenuation of a PET line not depend on where along it the annihilation was?
   Answer in `NOTES.md`.

**Hints.** Move the line into the ellipse's frame: subtract the center's projection on the line's
normal from s, and turn the normal by minus the ellipse's angle. Along a normal n the ellipse
reaches `h = sqrt(a^2 n_x^2 + b^2 n_y^2)`, and a line at distance d from its center cuts it in
`2 a b sqrt(h^2 - d^2) / h^2`. Check it on a circle first.
