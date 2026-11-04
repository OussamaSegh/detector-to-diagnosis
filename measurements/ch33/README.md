# Chapter 33 measurements: MiniDAQ end to end

- `e2e/`: `tools/e2e.py` on the release build, the clean commit named in `e2e/e2e.json`: the
  daily-QC acquisition (a point source, 1 MBq, 2 s) and the phantom acquisition (5 MBq, 2 s),
  each sent by `minidaq_send` at detector speed over UDP to `minidaq_server`. `e2e.md` lists every
  check with its values; `qc/` is the QC report; `image.npy` the phantom's OSEM image;
  `manifest.json` the SHA-256 of every file.

      MINIDAQ_RECON_CPP=build/release/recon python3 tools/e2e.py build/release/minidaq/apps \
          measurements/ch33/e2e > measurements/ch33/e2e.txt

- `e2e-damaged/`: the same with a damaged link (`--loss 0.002 --reorder 0.002 --duplicate 0.002`,
  2 MBq, no image): both runs incomplete with the loss named, every packet accounted for.
- `flatness.py`, `flatness.txt`: the image checks over five seeds, with and without the
  attenuation correction. The end-to-end run uses one fixed seed (33), so its image and its two
  numbers are the same on every run of the same code; the spread over seeds shows the margin to
  the limits.
- `acceptance-0.7.0.md`: `tools/acceptance.py` against the evidence of release 0.7.0
  (`measurements/release-0.7.0/`), as if that release had been judged by the specification. Its
  `release-checks.txt` was collated by hand from the four parts' outputs; from 0.8.0 on the
  script writes it.

Found on the way: without `--link 1` the offline sorter and the server disagree by design (10 of
13,126 prompts in the first comparison, 0.5 s at 2 MBq, seed 7), because the link rounds the
energy to 0.5 keV and moves singles across the energy window's edges; with it, they agree record
for record. And MDQ-PR-055: `minidaq_sim` printed one more recorded single than it used.
