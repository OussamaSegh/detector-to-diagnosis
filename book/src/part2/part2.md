# Part II: PET physics and data acquisition {.part}

Part II (five chapters, about 20% of your study time) is the domain you will lead. A DAQ team
owns the coincidence sorter, the sensor readout and the hardware controls; none of them can be designed well without knowing what the detector measures, what the
electronics deliver, and what the reconstruction downstream needs from you.

The chapters follow the data:

- **Chapter 8** is PET physics for software engineers: decays, photons, crystals and event
  types. MiniDAQ gains a detector simulator with ground truth.
- **Chapter 9** is the readout: how a photodetector pulse becomes a timestamp and an energy,
  event-word formats, clocks, and links that lose and reorder packets.
- **Chapter 10** is the coincidence sorter, the heart of the DAQ: merging streams, windows,
  multiples policies, randoms estimation and throughput.
- **Chapter 11** is count-rate performance: dead time, NECR and the bottleneck that saturates
  first.
- **Chapter 12** is the output: list-mode formats, sinograms and data integrity.

The physics in these chapters is the minimum a DAQ lead needs, explained for an engineer and
checked against the standard textbooks. NeuroLF's own numbers are not public in detail;
where this book needs one, it uses a typical value and marks it *assumption: confirm with
team*.
