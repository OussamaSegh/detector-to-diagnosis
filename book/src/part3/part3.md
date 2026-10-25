# Part III: Medical device software standards {.part}

Part III (five chapters, about 15% of your study time) is the frame that every line of the
NeuroLF's code sits in. A medical device software team organizes its work by the
regulations and by ISO 13485, IEC 62304, ISO 14971 and IEC 81001-5-1. None of them
tells you how to write a coincidence sorter. Together they decide what you must know about it
before it ships, what you must write down, and what you must do when it fails in the field.

The goal is not to become a regulatory expert. It is to make your own engineering work
(requirements, plans, designs, tests and records) audit-ready by default, so that the evidence
exists because you built it, not because someone reconstructed it before an audit.

- **Chapter 13** is the landscape: the EU MDR, the FDA's pathways, Switzerland, the map of
  standards and what happens after a device is on the market. MiniDAQ gains an intended-use
  statement and a regulatory context page.
- **Chapter 14** is IEC 62304, the software life cycle: safety classes, the development
  process, SOUP and traceability. MiniDAQ gains a development plan, requirements and a trace
  matrix generated from its tests.
- **Chapter 15** is ISO 14971, risk management for software: hazards, risk controls and their
  verification. MiniDAQ gains a risk file linked into the trace matrix.
- **Chapter 16** is ISO 13485 and daily work in a quality management system: design controls,
  change control, CAPA and audits. MiniDAQ gains a design history index and change templates.
- **Chapter 17** is cybersecurity under IEC 81001-5-1 and the FDA: threat models, security
  requirements and vulnerability management. MiniDAQ's control API gains authentication.

Standards are copyrighted, and this book does not reproduce their text. It names clauses
where that helps you find your way in your organization's copies, describes what they ask in
its own words, and marks with *verify* every detail you should check against the edition you
work to. Regulations are law and are quoted where the wording matters. Nothing in these
chapters describes any manufacturer's own procedures; your quality system decides how the work is
done there.
