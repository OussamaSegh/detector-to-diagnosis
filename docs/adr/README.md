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
| [0007](0007-list-mode-file-format.md) | List-mode file format | Superseded by [0012](0012-mdq-l1-list-mode-format-and-writer.md) |
| [0008](0008-hardened-release-builds.md) | Hardened release builds | Accepted |
| [0009](0009-udp-readout-link.md) | UDP readout link with sequence numbers and a bounded reorder buffer | Accepted |
| [0010](0010-coincidence-sorter-and-merger.md) | A streaming coincidence sorter with configurable policies, and a watermark merger | Accepted |
| [0011](0011-front-end-model-and-capacity-measurement.md) | Front-end dead time in the simulator, and capacity measured with a replayed stream | Accepted |
| [0012](0012-mdq-l1-list-mode-format-and-writer.md) | MDQ-L1, a custom block format for list-mode data, written by a two-thread sink | Accepted |
| [0013](0013-versioned-status-fields.md) | The status object is part of the versioned control API (API 1.1) | Accepted |
| [0014](0014-control-api-authentication-and-tls.md) | Control API authentication with bearer tokens and roles, over TLS 1.3 | Accepted |
| [0015](0015-property-based-tests-with-a-small-harness.md) | Property-based tests with a small in-house harness | Accepted |
| [0016](0016-flight-recorder-and-crash-report.md) | A flight recorder in memory and a crash report written by the dying process | Accepted |
