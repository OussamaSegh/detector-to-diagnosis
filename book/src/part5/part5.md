# Part V: Hardware interfacing, embedded Linux and networking {.part}

Part V (four chapters) is about the boundary between MiniDAQ and the electronics of the scanner.
You will not design the front-end boards or their firmware, but as the lead of the DAQ software
you must speak their language: drive their registers, keep their detectors biased and within
temperature, receive their data at line rate, agree with the firmware team on every bit that
crosses the boundary, and run all of it on a Linux platform that can be built, updated and
audited.

Until now MiniDAQ took its words from a simulator or from a UDP stream that a test program sent.
Part V puts hardware behind the same ports, with simulated hardware for every test and a real
backend for the bench.

- **Chapter 22** is talking to hardware from Linux: device files, memory-mapped registers and
  why `volatile` and barriers matter there, register maps generated from one specification, the
  slow-control buses and sensors of a detector, and fail-safe states. MiniDAQ gains typed
  registers, a memory-mapped bus, a simulated front-end board and a slow control that keeps the
  SiPMs' gain constant as their temperature changes.
- **Chapter 23** is high-throughput networking: the Linux receive path, socket buffers and
  batched receives, where a packet can be dropped and which counter shows it, and when kernel
  bypass is worth its cost.
- **Chapter 24** is FPGA basics for the DAQ software lead: reading a small firmware module and
  its timing diagram, clock domains and back-pressure, the interface control document between
  firmware and software, and what belongs on which side.
- **Chapter 25** is the embedded Linux platform: a controlled image, services with watchdogs,
  packaging, and signed updates that can be rolled back.
