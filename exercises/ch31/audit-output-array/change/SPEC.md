# Task given to the agent

Implement `writable_out(out, shape)` in `out_array.py`. The projector writes its result into
`out` through a raw pointer to doubles, in C order. Return `out` if that is safe, and raise
`ValueError` with the reason otherwise. Safe means:

- a NumPy array (`numpy.ndarray`);
- whose elements are float64 in the machine's byte order, however the array was made (SRS-REC-009
  refuses only an output that is not float64);
- of exactly `shape`, C-contiguous and writeable.

Add tests.
