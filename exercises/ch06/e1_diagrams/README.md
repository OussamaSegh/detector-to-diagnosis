# Exercise 6.1 (E): Draw the component diagram and the state machine

**Goal.** Draw the two diagrams every newcomer to MiniDAQ needs: the components with their
dependencies, and the acquisition state machine. Draw them as Graphviz files, so they live in
version control and a test can check that they still match the code.

**Time.** 90 minutes.

**Tasks.**
1. In `states.dot`, draw every transition of `minidaq::control::transitions` as an edge
   `from -> to [label="event"]`. Node names are the state names (`idle`, `configured`, ...).
   You may add a start point node named `start` with an edge to the initial state.
2. In `components.dot`, draw at least 12 components of MiniDAQ as nodes. Give each node a
   `class` attribute naming its layer: `core`, `application`, `adapters` or `app` (see
   `docs/architecture/layers.json` for which code belongs where). An edge `a -> b` means
   "a uses b". Include at least the pipeline, the state machine, the service, the
   configuration, the ports, the control protocol, the server and both applications.
3. Render both with `dot -Tsvg` and look at them. Rearrange until a reader can follow the
   arrows in under a minute.

**Acceptance tests** (`tests/test_diagrams.py`, run by CTest with your directory on
`PYTHONPATH`): the state edges equal `docs/architecture/acquisition-states.json`; every
component has a valid class, every layer appears, and every edge goes from a layer to one it
may use (the same rule `tools/check_layers.py` applies to the code); no component is
isolated; both files render if Graphviz is installed.

**Hint.** Draw the component diagram top to bottom with `rankdir=TB` and one `subgraph
cluster_...` per layer. If an arrow points up, either the drawing or the code is wrong. Which
one?
