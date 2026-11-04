# Part IX: Beyond the acquisition: the hospital, the team and the tools {.part}

Part IX (three chapters) looks outward from MiniDAQ. Eight parts built the data acquisition
system and the evidence around it, and ended with an image in a file only MiniDAQ's own tools can
read, written by a team of one with tools the book took for granted. A scanner's software lives in
a hospital, is written by a team and, more and more, with an AI assistant at the engineer's side.

- **Chapter 35** carries the image the rest of the way: a series of DICOM objects that a picture
  archive (PACS) can store and any viewer can read, sent over the network with the archive's own
  protocol, through a queue that loses nothing. It is where three hazards live that no earlier
  chapter could have: an image filed under the wrong patient, values or positions read
  differently from what the reconstruction made, and a series that does not arrive whole.
- **Chapter 36** is about the team: Git and the workflow of a regulated team, from branches and
  commits to review and the record that every change leaves, with a tool that checks a range of
  commits against the project's rules.
- **Chapter 37** is about the tools that now write code with you: AI-assisted coding for
  medical-device software, drawn from how this book and MiniDAQ were built and checked, and what a
  regulated process asks of a change an assistant wrote.
