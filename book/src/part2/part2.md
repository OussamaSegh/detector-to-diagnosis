# Part II: PET physics and data acquisition {.part}

Part II (five chapters, about 20% of your study time) is the domain you will lead. A DAQ team
owns the coincidence sorter, the sensor readout and the hardware controls; none of them can be designed well without knowing what the detector measures, what the
electronics deliver, and what the reconstruction downstream needs from you.

The chapters follow the data:

- **Chapter 8** is PET physics for software engineers: decays, photons, crystals and event
  types. MiniDAQ gains a detector simulator with ground truth.
- **Chapter 9** is the readout: how a photodetector pulse becomes a timestamp and an energy,
  event-word formats, clocks, and links that lose and reorder packets. MiniDAQ gains the
  MDQ-R1 packet format and a UDP transport that counts every lost, late or reordered packet.
- **Chapter 10** is the coincidence sorter, the heart of the DAQ: merging streams, windows,
  multiples policies, randoms estimation and throughput. MiniDAQ gains a streaming sorter
  with a delayed window, validated against the simulator's truth.
- **Chapter 11** is count-rate performance: dead time, NECR and the bottleneck that saturates
  first. MiniDAQ gains dead-time models and a harness that draws NEMA-style count-rate curves.
- **Chapter 12** is the output: list-mode formats, sinograms and data integrity. MiniDAQ
  gains the MDQ-L1 file format with its specification, a crash-safe writer and a sinogram
  histogrammer.

At the end of Part II, MiniDAQ runs the whole chain in software, from a simulated scanner
through the readout link and the sorter to list-mode files and sinograms, and every
stage reports what it lost and why.

The physics in these chapters is the minimum a DAQ lead needs, explained for an engineer and
checked against the standard textbooks. NeuroLF's own numbers are not public in detail;
where this book needs one, it uses a typical value and marks it *assumption: confirm with
team*.
