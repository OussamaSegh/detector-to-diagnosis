```{=latex}
\mainmatter
```

# Part I: Modern, low-latency C++ for data acquisition {.part}

Part I is the largest part of the book (seven chapters, about 30% of your study time) because
fast, low-latency C++ for a continuous stream of detector data is the core of a DAQ engineer's
work. A brain PET scanner can produce tens of millions of singles per
second; your code must keep up without dropping events and without unbounded latency, and it must
stay maintainable and auditable for the life of the product.

The chapters build on each other and on MiniDAQ, the running project:

- **Chapter 1** sets the language baseline: ownership, strong types, error handling,
  concepts, compile-time work and undefined behavior.
- **Chapter 2** is about memory: caches, data layout, allocation and bit-packed event
  words.
- **Chapter 3** turns MiniDAQ into a multi-threaded pipeline connected by lock-free
  queues.
- **Chapter 4** makes it deterministic on Linux: CPU isolation, memory locking and tail
  latency.
- **Chapter 5** is performance engineering: benchmarks you can trust, profilers, SIMD and
  regression gates.
- **Chapter 6** is architecture: layers, the acquisition state machine, the control API
  and decision records.
- **Chapter 7** is safe and secure C++: coding standards, static analysis, fuzzing,
  hardening and the SBOM.
