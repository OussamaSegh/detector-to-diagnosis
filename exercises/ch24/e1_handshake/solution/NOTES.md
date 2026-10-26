# Exercise 24.1: notes on the solution

**Which cycle to compare.** Rules 2 and 3 are about a word that is waiting, and a word waits when
the previous cycle had valid and not ready. So the check looks at cycle `i - 1` to decide whether
cycle `i` is bound: valid must still be 1 and data must be the same. After a transfer (valid and
ready in `i - 1`) the next cycle is free, which is why back-to-back words are not a violation.

**Rule 4 and deadlock.** If the sender waits for ready before raising valid and the receiver waits
for valid before raising ready, neither ever moves: the stream deadlocks with both signals at 0,
and the trace shows only idle cycles. That is indistinguishable from a sender that has nothing to
send, so one trace cannot convict a design of breaking rule 4; it is checked by reading the RTL
(valid must not be a function of ready) or with an assertion in simulation. The receiver, on the
other hand, may wait for valid before raising ready: the rule is asymmetric so that one side always
moves first.

**What the numbers say.** Stalls are back-pressure: the receiver could not take the word. On the
board, the data link stalls the FIFO when the network is busy; the longest stall times the
incoming rate is how many words the FIFO must hold (Exercise 24.3).
