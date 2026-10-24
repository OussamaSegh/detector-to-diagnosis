# Architecture decision records

One file per decision, numbered in the order the decisions were made, never renumbered.
A decision that changes is not edited away: write a new record and mark the old one
"Superseded by NNNN". The format is in [0001](0001-record-architecture-decisions.md);
`exercises/ch06/e3_adrs` contains a checker for it.

| Number | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-batched-spsc-channels.md) | Batched SPSC channels between pipeline stages | Accepted |
| [0003](0003-control-protocol.md) | Control protocol: newline-delimited JSON over TCP | Accepted |
| [0004](0004-json-library.md) | JSON library for the control plane | Accepted |
| [0005](0005-acquisition-state-machine.md) | A table-driven acquisition state machine | Accepted |
| [0006](0006-cpp20-with-expected-shim.md) | C++20 with a std::expected shim | Accepted |
| [0007](0007-list-mode-file-format.md) | List-mode file format | Proposed |
