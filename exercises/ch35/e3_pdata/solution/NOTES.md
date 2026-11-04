# Exercise 35.3: notes

The starter fails all ten tests. It reads only the first PDV of each PDU, so even a command and
its data set in one PDU lose the data set; with a data set cut across PDUs it yields every
fragment as a whole data set, and an archive built on it would store a tenth of an image ten
times; and it checks nothing, so a damaged stream is a stream of shorter messages.

Design choices:

- Two generators: `pdvs` knows the PDU's layout, `messages` the rules of a message. The PDV loop
  checks the length against its PDU before it slices, because a Python slice past the end is not
  an error, it is a shorter fragment.
- The state is the message's context, its command, its data set and whether the command is
  complete; every rule is a check of one of them. A message starts with the first fragment and
  ends with the last one of its data set (or of its command, without one).
- Input that ends mid-message is an error, not a short data set: the archive must not store the
  bytes it has. It aborts the association; the sender, which has no success status for that
  instance, keeps it and sends it again (the outbox of Chapter 35).
- To the questions: a receiver waiting for a last bit that never comes waits until its timer
  ends the association, which is the right failure, loud and with nothing stored. The limit on a
  message is a limit on what the archive buffers, set from the largest object it accepts (a
  multi-frame object can be hundreds of megabytes); the maximum PDU length limits one PDU, not the
  number of PDUs in a message. This solution has no limit: a product's must have one.
