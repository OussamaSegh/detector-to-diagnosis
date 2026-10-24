# 0007. List-mode file format

Date: 2026-10-24
Status: Proposed

## Context

The pipeline's coincidences currently go to a counting sink that discards them. Before
MiniDAQ writes data that reconstruction, calibration and analysis will read for years, we
need a file format. It must sustain the sorter's output rate on the acquisition disk,
detect corruption, survive a crash with at most the last block lost, carry the metadata of
the acquisition (configuration, geometry, calibration versions, software version), and be
readable from C++ and Python. The detailed requirements and measurements are the subject of
Chapter 12; this record captures the options so the decision is made deliberately.

## Options

1. **A custom binary format**: a versioned header, then fixed-size records in blocks, each
   block with a CRC32. Fastest to write, simplest to make crash-safe, fully under our
   control; we must document it and write the readers.
2. **HDF5**: a self-describing container with datasets and attributes, wide tool support
   (h5py). Large SOUP item; write throughput and crash behavior depend on configuration and
   must be measured.
3. **An existing list-mode convention** (for example the formats read by STIR or CASToR).
   Reconstruction tools read it directly; it may not hold the metadata we need, and we do not
   control its evolution.

## Decision

Not decided. Proposed direction: option 1 for the raw stream, with the acquisition metadata
in a sidecar or header and converters to the formats of reconstruction tools, to be
confirmed by the throughput and crash tests of Chapter 12. Until then the
`CoincidenceSinkPort` interface keeps the choice open: the pipeline does not know what a
sink does with the data.

## Consequences

### Positive

- The decision is made with measurements on the target disk rather than by habit.
- Nothing upstream of the sink depends on the format.

### Negative

- Until the record is accepted, MiniDAQ cannot keep data, so end-to-end tests stop at the
  counting sink.
