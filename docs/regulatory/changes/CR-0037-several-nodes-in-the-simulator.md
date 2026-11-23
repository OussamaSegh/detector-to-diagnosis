# CR-0037: Several readout nodes in the simulator, merged in one process

| Field | Value |
|---|---|
| Status | approved |
| Requested | 2026-11-23, by the software lead |
| Source | improvement; roadmap 2.2.0, theme S |
| Decision | approved, 2026-11-23, by the software lead (the author), in writing in the project |
| Commits | none yet |

## Description

A scanner larger than MiniDAQ's reads its detector blocks out through several acquisition PCs,
each sending its own time-ordered stream with its own clock. This change lets the simulator and
the synthetic source produce such streams, and merges them in one process before the coincidence
sorter, so that the Third Edition (roadmap 3.0.0, Part XI) can build on code that works.

1. **Nodes in the simulator** (item `sim`, not shipped): the scanner's blocks are divided among
   N readout nodes (contiguous ranges of blocks by default, or a list of the node of each
   block). Each node is a time-ordered stream of its own, and stamps its singles with its own
   clock offset, as a separate acquisition PC would.
2. **The node merge** (item `merger`, class B): before the sort stage, the pipeline subtracts
   each node's configured clock offset and merges the nodes' streams with a k-way merge built on
   the stream merger of Chapter 10. It holds a single until every node has delivered a later
   time, so that a coincidence whose two singles come from two nodes is formed as it would be
   from one stream: that hold is the overlap at the node boundaries, stated in time.
3. **Configuration schema 2.2**: an optional `source.nodes` object (`count`, and
   `clock_offsets_ps` with one entry per node) for the synthetic source. Without it there is one
   node and the pipeline takes the path of 2.1, which bypasses the merge.

Not in this change: nodes as separate processes or machines, the loss of a node, the network
between nodes (roadmap 3.0.0, Chapters 41 and 42).

## Reason

Part XI of the Third Edition teaches acquisition at scale. Without a merge that is specified,
tested against a reference and measured, it would have to teach on code that does not exist.
The merge is also where a coincidence across two nodes can be lost, a cause of H-01: it is
specified before it is coded.

## Impact analysis

### Requirements

Added, all verified by test; they take the next numbers of their groups when the SRS draft is
written:

- **Simulator group**: The simulator shall divide the scanner's blocks among a configured number
  of readout nodes, from 1 to 8, give each node a time-ordered stream of the singles of its
  blocks stamped with the node's clock offset of at most 1 µs either way, and with one node
  produce the stream it produces without nodes.
- **Merger group**: The node merge shall subtract each node's configured clock offset and merge
  the nodes' streams into one stream in the pipeline's time order, releasing a single only when
  every node has delivered a later time or ended.
- **Merger group**: For any division of the blocks among nodes and any clock offsets within the
  bound, the coincidences of the merged run shall equal, coincidence for coincidence, those of
  the same singles sorted as one stream (the single-node oracle).
- **Configuration group**: The acquisition configuration shall accept, from schema 2.2 on, an
  optional `source.nodes` object for the synthetic source with the count of nodes and one clock
  offset per node, refuse it for another source type or a schema before 2.2, and refuse a count
  or an offset outside its range.

SRS-PIPE-010 (the same coincidences as the reference) and SRS-PERF-020 (10 M singles/s with a
margin of 2) are repeated with one node, the default. The throughput with 1, 2 and 4 nodes and
the merge's cost per single are measured and recorded, not required.

### Software items and safety class

`sim` (not shipped): the node division. `merger` (class B): the node merge. `pipeline`
(class B): the source stage merges when there are several nodes. `config` (class B): the
optional field. No item's class or segregation changes.

### Risk

H-01 (coincidence data lost without notice) gets a new cause: a single held too briefly at a
node boundary is dropped as late, or two nodes' singles are merged out of order, and a
coincidence across two nodes is lost. Its control is the node merge's requirement (a single is
released only when every node is past its time; a late single is counted, never dropped
silently, as SRS-MRG-003 already requires) and its verification by the single-node oracle. The
probability estimate of H-01 does not change: the merge is used only with the simulator in 2.2.

### SOUP

None.

### Interfaces and data formats

Configuration schema 2.2, compatible: the new field is optional, and every 2.0 and 2.1 document
is read as before. The control protocol, the readout format and the list-mode format do not
change.

### Documents

The SRS (the new requirements); the risk file (H-01's new cause); the configuration schema and
its documentation (2.2); the architecture (the merge before the sort stage); the performance
budget (the throughput with 1, 2 and 4 nodes); ADR 0041; the CHANGELOG.

### Regulatory

The intended use does not change. The merge is a new part of a safety-relevant function, the
coincidence chain; it is exercised only with the simulator in 2.2, and the product's acquisition
from one UDP source does not change.

## Verification

Property tests with the single-node oracle (random divisions of the blocks and random offsets
within the bound, the merged coincidences equal to the single-node ones); unit tests of the
node division and the merge (order, ties, a slow node, the end of a run); the configuration
tests of schema 2.2; `tools.agent_gate` and the release checks with the default of one node,
SRS-PIPE-010 and SRS-PERF-020 among them; the throughput measured with 1, 2 and 4 nodes.

## Decision

Approved by the software lead on 2026-11-23, in writing in the project (22:20 UTC), on the impact analysis above.
