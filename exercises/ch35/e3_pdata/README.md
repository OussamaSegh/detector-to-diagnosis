# Exercise 35.3 (H): Messages out of fragments

**Goal.** Reassemble DIMSE messages from the P-DATA-TF PDUs of a DICOM association, as a storage
archive does for every image it receives. A sender cuts each command and each data set into
fragments that fit the receiver's maximum PDU length; a PDU can carry several fragments, and a
message can span many PDUs. A receiver that gets this wrong stores half an image as a whole one,
or the end of one image as the start of the next.

**Time.** 3 hours.

**The format** (DICOM part 8). A P-DATA-TF PDU's body is one or more PDV items, each:
4 bytes of length (big-endian; it counts the next two bytes and the fragment), 1 byte
presentation context ID, 1 byte message control header (bit 0: 1 for a command fragment, 0 for
a data set fragment; bit 1: 1 for the last fragment of that command or data set), then the
fragment. A message is a command and, unless its Command Data Set Type (0000,0800) is 0x0101, a
data set, both on the same presentation context; the command comes first.

**What to write** (`pdata.py`): `messages(pdus)`, a generator over `(pdu_type, body)` pairs that
yields `(context_id, command, dataset)` for each complete message, `dataset` being `None` for a
message without one. Raise `ValueError` for:
- a PDU that is not P-DATA-TF (type 4);
- a PDV whose length is under 2 or runs past the end of its PDU;
- a fragment on another presentation context than the message's;
- a data set fragment before the command is complete, or a command fragment after it is;
- input that ends in the middle of a message.

`command_has_dataset(command)` is given.

**Starter.** `starter/pdata.py` takes one PDV per PDU and treats every fragment as complete.

**Acceptance** (`tests/test_pdata.py`): a message in one PDU; a data set cut into many fragments
across PDUs; several PDVs in one PDU, closing one message and starting the next; an echo (no data
set) followed by a store; each of the five errors above.

**Then, by hand.**
1. A sender that never sets the last-fragment bit: what does a receiver that waits for it do, and
   what does yours do? Which is the right failure?
2. Why is "input ends in the middle of a message" an error and not a short data set? What does
   your storage archive answer, and what must it not do with the bytes it has?
3. How large may a message be before your receiver refuses it? Where would you put that limit
   in a product, and why is "the maximum PDU length" not that limit?
