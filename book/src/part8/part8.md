# Part VIII: MiniDAQ 1.0 and the work after it {.part}

Part VIII (two chapters) closes the project. Seven parts built MiniDAQ one stage at a time: the
simulator of a detector, the readout link, the server's pipeline and coincidence sorter, the list
mode, the sinograms, the corrections, the reconstruction and the quality report, each with its own
tests, measurements, requirements and change records. Each stage was shown to do what its chapter
asked of it. Nothing yet showed that the stages do it together, and nothing said in writing what
"done" means for the whole product.

- **Chapter 33** is the capstone. It runs the chain as the scanner runs it, from simulated decays to
  a reconstructed image, through the shipped programs and over a real socket; checks that what
  every stage passes on is what the next stage receives; compares the server's output record for
  record with an offline reference; writes the acceptance criteria of MiniDAQ 1.0 as a
  specification that a tool evaluates; and freezes the requirements so that a verified
  requirement can change only through change control.
- **Chapter 34** is about the day after: what an engineer does in the first ninety days with a
  data acquisition codebase they did not write, whether it is MiniDAQ or a real scanner's. It
  turns the questions that every chapter's "ask your team" box raised into a method, and adds a
  tool that surveys a repository for the places that deserve attention first.
