# Audit report: the agent's writable_out (Exercise 31.5)

Not mergeable. The check compares dtypes by identity, and NumPy does not keep one dtype object
per type: it shares one among most float64 arrays, not all. This is MiniDAQ's own defect
(MDQ-PR-088), in the C++ projector's binding and in Exercise 29.4's solution, found by the
independent review of release 2.1.0.

## The defect: a float64 array with a dtype object of its own is refused (MDQ-PR-088)

An array that was unpickled (multiprocessing, joblib, `np.load` of a pickle) or viewed through
`newbyteorder()` twice has an equal float64 dtype that is a different object. `is` refuses it
with "out must be float64, got float64", a message that contradicts itself.

- *Test:* `test_an_array_sent_from_another_process_is_taken` and
  `test_an_array_whose_byte_order_was_swapped_twice_is_taken`.
- *Who meets it:* the scientist who parallelizes a reconstruction with `multiprocessing` and
  passes `out=` arrays to the workers. The code is safe, since nothing wrong is written, but
  the feature is unusable exactly where in-place output matters most.
- *Why the agent's tests could not see it:* every array in them was made with `np.zeros` in
  the same process, so all of them shared NumPy's one dtype object. The claim "NumPy keeps one
  dtype instance per built-in type" was the premise, and nothing tested it.
- *Correction:* `out.dtype != np.dtype(np.float64)`. Dtype equality compares the type and the
  byte order, so the big-endian array the agent worried about is still refused
  (`test_a_big_endian_array_is_refused`). In C++, `py::isinstance<py::array_t<double>>`, which
  uses NumPy's equivalence test.

## Verdict

Request changes. An exactness argument about a library ("one instance per type") is a fact to
check in a minute, not a reason to choose identity over equality.
