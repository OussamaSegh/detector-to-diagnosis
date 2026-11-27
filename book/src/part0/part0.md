```{=latex}
\mainmatter
```

# Part 0: Foundations {.part}

Part 0 is the on-ramp to the rest of the book. It is written for a reader who can write a loop
and a function in some language, has compiled a C++ program at least once, and wants the rest
from first principles: the language, the Linux system under it, threads, the classic designs and
the data structures that a data acquisition system is built from. Part I starts where these
chapters end, at the level of an engineer who already uses all of this every day.

The seven chapters carry letters instead of numbers, F1 to F7, so that the forty chapters after
them keep their numbers, and with them every exercise, directory and record that names one.

- **Chapter F1** is C++ from the ground up: how a program is compiled and linked, values,
  references and pointers, classes and RAII, templates, the standard library, and errors.
- **Chapter F2** walks the standards from C++11 to C++23, one feature at a time, on a running
  example, and says which compiler has which feature.
- **Chapter F3** is Linux for the C++ engineer: the shell, the system, the toolchain, and how to
  look at a running program.
- **Chapter F4** is Linux systems programming: processes, file descriptors, signals, event loops,
  shared memory and a first socket, each wrapped in RAII.
- **Chapter F5** is concurrency from zero: threads, data races, mutexes, condition variables,
  deadlock, tasks and thread pools, up to the first atomic.
- **Chapter F6** is design patterns in modern C++, at the level of the code: each pattern in its
  classic and its modern form, with what it costs.
- **Chapter F7** is data structures and algorithms for a DAQ, from the standard containers to a
  lock-free stack, and how to test them.

Each chapter follows the recipe of the rest of the book (objectives, prerequisites, sections from
the intuition to a worked example, exercises whose starters fail their tests, check yourself, a
summary and further reading), with one change: instead of a MiniDAQ milestone, it ends with
**Reading MiniDAQ**, a guided reading of the project's own code that uses the chapter's ideas,
with the questions a reviewer would ask of it. Part 0 changes nothing in MiniDAQ.

Every chapter has four exercises, and the last of them, marked (A), is an audit: a change
recorded as a coding assistant proposed it, with its specification and its patch. You review it,
write down what is wrong and why, and fix it until its acceptance tests pass. Reading code you
did not write, and saying precisely what is wrong with it, is the skill the rest of the book
assumes most.

**If you already know a chapter's topic**, answer its *Check yourself* questions first. If you
can answer them without looking, skip to the next chapter; Part I does not depend on the order
you read Part 0 in, only on its content. The exercises of Part 0 build and run like every other
exercise: `ctest --preset debug -L foundations` runs all of their tests at once.
