# Exercise 15.1: notes

**A hardware engineer's rating.** The probabilities of C-01 (loss on the link) and C-05 (a
damaged block) depend on the network and the disk: a hardware engineer would rate how often
packets are dropped at 70 M singles/s or how often a disk returns a bad block, and might find
them lower or higher than P4. The software's rating does not use those numbers, because it
takes the software's contribution as certain and asks only what happens next: is the loss
detected, reported, and acted on? That is why the controls of Chapter 15 detect and report
loss rather than try to make it rarer: they work whatever the hardware's rate is.

**Identification.** MiniDAQ holds no patient identity, so "wrong patient" cannot happen inside
it. What can happen is that one run's data is mixed with another's (C-07) or invented data
is taken for a scan (C-08): both put the wrong data behind a patient's name downstream.
