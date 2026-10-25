# Exercise 16.2: notes

**"It is only a default."** A default is the value of every configuration that omits the key, so
changing it changes the acquisition of documents that nobody edited, which is hazard H-04; that is
why version 1.0 to 1.3 documents keep 4 ns and the new value comes with schema 1.4. The number
appears in more places than the one constant (the shipped `default.json` sets 4000 explicitly, so
changing only the constant would leave the default configuration at 4 ns), and several tests and a
measurement assume it. And the new value must be shown to keep every true pair for the real
scanner's timing resolution, which is an assumption until it is measured: the change request is
where that condition is written down before anyone approves it.

**What the draft got wrong.** It was "approved" with a pending decision; it named a test that
does not exist as if it did; it said "None" under risk for a change to the sorter's selection; it
left out half of the sections; and it treated SRS-SRT-001 as unaffected because its text did not
change, while its test is one of the ones that break.
