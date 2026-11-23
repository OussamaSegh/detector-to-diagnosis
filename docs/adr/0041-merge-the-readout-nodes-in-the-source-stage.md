# 0041. Merge the readout nodes in the source stage, waiting for every node

Date: 2026-11-23
Status: Accepted

## Context

A scanner larger than MiniDAQ's reads its blocks out through several acquisition PCs, each a
readout node with its own time-ordered stream and its own clock. The coincidence sorter needs one
stream in true time. A coincidence whose two singles come from two nodes is formed only if the
merge holds each single until no earlier single can still come from another node; a merge that
releases too early drops the late single and loses the coincidence (a new cause of H-01). The
Third Edition (roadmap 3.0.0, Part XI) teaches acquisition at scale and needs code that does this
and is tested against a reference (CR-0037).

## Options

1. **Merge in the sort stage.** The sort stage would take several inputs; its thread would do the
   sorting and the merging, and the pipeline's shape would change for every run.
2. **A stage of its own between the source and the sort stage.** A sixth thread and a fifth
   channel: a copy of every single and a latency for every run, including runs with one node.
3. **Merge in the source stage, from the StreamMerger of Chapter 10, with no maximum skew.**
   The nodes' streams become one stream before the pipeline sees them; with one node the merge
   is bypassed and the run is that of 2.1.

## Decision

Option 3 (CR-0037).

- `NodeMerge` (item merger) subtracts each node's configured clock offset and pushes the stream
  to a StreamMerger with one board per node and `max_skew` 0: a single is released only when
  every node has delivered a later time (a single or a time marker) or has ended. A silent node
  holds the run back rather than lose its coincidences; a late single is counted (SRS-MRG-003).
- The simulator (`sim::NodeLayout`, `NodeSplitter`, `MultiNodeSource`) divides the synthetic
  singles among the nodes, stamps them with each node's clock, and reports each node's time
  after each step, as a node's time markers would. The paced source uses it when a configuration
  names more than one node.
- The reference is the single-node oracle: for random divisions of the blocks and random offsets
  within 1 µs, the coincidences of the merged stream equal those of the same singles sorted as
  one stream (SRS-MRG-007, RC-56).

## Consequences

### Positive

- The pipeline does not change, and one node is exactly the run of 2.1.
- The merge's waiting rule is the one Chapter 10 already proved for boards, with the skew bound
  removed for a reason that is stated.
- The cost is measured: about 20 ns per single with 2 nodes and 25 ns with 4, on the source
  thread; the whole pipeline keeps a margin of 2.5 times at 10 M singles/s with 4 nodes
  (performance budget, version 5).

### Negative

- The merge shares the source thread with the generator: with 8 nodes the synthetic source falls
  just below 10 M singles/s. Nodes that are separate machines move the generation elsewhere.
- A node that stops without ending holds every single back until the run is stopped; the loss of
  a node and its detection are roadmap 3.0.0 (Chapter 42).
- The clock offsets are configured, not measured: a wrong offset of more than a coincidence
  window loses true coincidences across nodes, which the time base monitor of Chapter 38 would
  show as a block offset.
