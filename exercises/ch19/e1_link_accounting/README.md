# Exercise 19.1 (E): Account for every packet

**Goal.** Write the accounting identities of a damaged readout stream. `minidaq_send` reports how
many packets it cut from the stream and how many it dropped, delayed and duplicated on purpose;
the server's link counters say what arrived and what the sequence tracker made of it. Every
packet must be accounted for, exactly.

**Time.** 45 minutes.

**Starter.** `starter/accounting.py` checks one identity. `tests/recorded.json` holds four real
runs (a clean stream, two damaged ones and one across the sequence wrap) as the system tests of
Chapter 19 make them. Chapter 9 describes the tracker's counters.

**Tasks.** Complete `check(sent, link)` so that it returns the names of the identities that do
not hold:

| Name | What must hold |
|---|---|
| `reordered` | only a delayed packet whose copy did not go on time can be put back in order |
| `sequence` | every sequence number is delivered or declared lost, once |
| `lost` | lost sequence numbers: the dropped packets and the delayed ones that came too late |
| `stale` | the stale packets are the duplicates and the delayed ones that came too late |
| `received` | a packet that arrived was delivered or dropped as stale |
| `datagrams` | every datagram put on the wire arrived (loopback loses nothing) |
| `words` | without a loss, every single arrived |
| `resyncs` | one sender, one numbering: no resync |

**Acceptance** (`ch19/e1_link_accounting/<variant>/unittest`): every recorded run passes; each
corrupted counter is named by the identity it breaks.

Then answer in `NOTES.md`: why can one delayed packet appear in two counters? If the server
received a datagram and then dropped it before the tracker saw it, which identities would break?
