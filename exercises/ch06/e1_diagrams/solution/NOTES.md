# Exercise 6.1: notes on the reference solution

The reference diagrams are the ones in `docs/architecture/`: the solution files are copies,
and the architecture document renders them.

- **States.** Twelve edges, one per table row. The four `error` edges are what make a
  diagram of this machine cluttered; an alternative is a single note "any state but fault
  --error--> fault", but then a test cannot compare the drawing with the table. Keep the
  edges and color the fault state instead.
- **Components.** Drawn top to bottom, apps first, core last, one cluster per layer. Every
  arrow points down or sideways inside a layer; an upward arrow is a layering violation. The
  dashed edge from `minidaq_ctl` to `ControlServer` is a network connection, not a code
  dependency: the client links none of the server's code.
- **Granularity.** One node per item someone would talk about in a design review. Twelve to
  twenty nodes is readable; the whole class list is not.
- **What the test does not check** is that your diagram matches the *code's* includes. That
  is `tools/check_layers.py`'s job. A diagram is a claim; the include check is the evidence.
