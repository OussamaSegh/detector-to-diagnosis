# How to use this book {.unnumbered #how-to-use}

This book teaches you to build the data acquisition software of a PET scanner in modern C++, and
to build it the way regulated medical device software must be built. It is practice-heavy: every
chapter grows MiniDAQ, a simulated PET data acquisition system with its own regulated software
file, and every code listing is compiled and tested from the companion repository.

## How a chapter is built {.unnumbered}

Every chapter has the same shape:

1. **Why it matters**, a short scene from the daily work, the learning objectives, and the
   prerequisites with an estimate of the reading, exercise and milestone time.
2. **Sections** that go from the intuition to a worked example. Boxes mark common mistakes, what
   changes in regulated work, and the questions worth asking your own team.
3. **Exercises**, marked E (easy), M (medium) or H (hard). Each has a goal, a starter, acceptance
   tests and a time estimate. Every starter fails its acceptance tests until you have done the
   work; the solutions manual and the repository hold a solution that passes them.
4. **A MiniDAQ milestone** with a definition of done.
5. **Check yourself** questions, a summary, and the references.

## Choosing your path {.unnumbered}

The time estimates add up to a lot of work, more than most readers will do in one pass. Two
paths through each chapter help:

- **The core path** is the reading and the milestone. It is what you need to follow the next
  chapters and to keep MiniDAQ complete.
- **The full path** adds every exercise. Do the exercises in the order the chapter lists them;
  several chapters say which ones to keep when time is short, and the ones marked H and the
  extras can wait.

If you read selectively, protect Parts I and II and Chapter 14 (IEC 62304): together they are
the data acquisition system, its C++ and the regulated life cycle that every other chapter
builds on. Keep a list of the exercises you skip. A real system you work on later is often the
best reason to come back to one.

Answer the Check yourself questions from memory a day or two after you read a chapter, and keep
a short learning log: the numbers you measured on your own machine, the questions you could not
answer, and what to revisit.

## The companion repository {.unnumbered}

MiniDAQ grows in chapter order. The repository has one git tag per chapter (`ch00` is the empty
starting point, then `ch01`, `ch02` and so on), so each milestone can start from the previous
chapter's tag (`ch07` for Chapter 8's milestone, for example) rather than from your own code.
Merge your own work into it when you want to keep it. The exercises are under
`exercises/chNN/`, each with its README, starter, solution and tests; the repository README lists
the tools to install and the commands to build and test.
