# Roadmap for release 3.0.0: the foundations, and parallel computing on GPUs

Status: accepted, 2026-11-25, by the coordinator under the author's standing delegation, with
CR-0040. Drafted at the author's request of 2026-11-25 (section 8): the book
should teach multithreading and concurrency, C++23, Linux, design patterns and advanced data
structures such as lock-free queues to a reader who has never used them, and possibly parallel
computing, CUDA, GPU image reconstruction and deep learning. This plan is folded into
`docs/ROADMAP-3.0.0.md` as Themes F and G (its sections 4, 5 and 6). It changes nothing in 2.3.0,
which another thread is building now.

## 1. What the book has today, and the gap

An audit of every chapter on 2026-11-25 (main at e0ac879) found that the book covers each of
these topics, but at the level of an engineer who already knows the basics. Every chapter's
prerequisites say so: Chapter 3 expects that "you should have written a program with
`std::thread` before"; Chapter 4 starts at scheduling policies, not at what a process is.

| Topic the author named | Where the book has it | Level | What is missing for a beginner |
|---|---|---|---|
| Multithreading and concurrency | Chapter 3 (memory model, SPSC and MPMC rings, pipelines, TSan, latches), Chapter 6 (a deadlock in the state machine), Appendix A (concurrency architecture) | Advanced | What a thread is, a data race shown failing, mutexes and their lock types, condition variables, deadlock and lock order, futures, `std::async`, tasks and thread pools, semaphores, the parallel algorithms |
| C++23 | Chapter 1 (ownership, strong types, `std::expected`, concepts, constexpr, UB; one section "What C++23 adds") | Production C++20, a few C++23 features | The core language and the standard library from first principles; the C++11 to C++23 timeline; each C++20 and C++23 feature on code a reader can run: ranges and views, `std::format` and `std::print`, `std::generator`, deducing `this`, `std::mdspan`, `std::flat_map`, modules and why MiniDAQ does not use them |
| Linux | Chapter 4 (scheduling, isolation, page faults, clocks), Chapter 22 (device model, `mmap`, MMIO), Chapter 23 (sockets, NIC tuning), Chapter 21 (gdb, core dumps), Chapter 32 (CMake) | Advanced | The shell and the file system, processes and file descriptors, `fork` and `exec`, signals, pipes, `poll` and `epoll`, `eventfd`, shared memory, permissions, `systemd`, `strace`, the toolchain (compiler, linker, shared libraries, `ldd`, `nm`) |
| Design patterns | Chapter 6 (ports and adapters, the state machine), Appendix A (architecture-level patterns and their ADRs) | Architecture | The code-level patterns in modern C++: strategy, observer, factory and registry, builder, decorator, command, visitor with `std::variant`, type erasure, CRTP and policies, pimpl, RAII and scope guards; concurrency patterns (active object, monitor, reactor, thread pool); anti-patterns (singleton, god object); when a pattern is the wrong answer |
| Advanced data structures, lock-free queues | Chapter 2 (layouts, packing, false sharing), Chapter 3 (SPSC ring, Vyukov's MPMC queue, ABA in one section), Chapter 10 (the sorter's windows) | Applied | How the standard containers work inside and what they cost; heaps and the k-way merge; flat maps and small-buffer containers; intrusive lists; arenas and `std::pmr`; bitsets; compare-and-swap from zero; a Treiber stack and the Michael-Scott queue; memory reclamation (hazard pointers, epochs); the seqlock; testing them |
| Parallel computing | Chapter 5 (SIMD, histogramming), Chapter 28 (the projector runs on four threads with `std::jthread`), Chapter 31 (Numba) | Touched | Amdahl and Gustafson, the roofline, data and task parallelism, OpenMP, the parallel algorithms, reductions and their reproducibility, scaling measured |
| CUDA, GPU reconstruction | Chapter 28 says GPUs "change the projector and the model, not the structure"; Appendix A names "a reconstruction moved to a GPU" as a decision not taken; roadmap 3.0.0 section 9 names it as further study | Absent | Everything |
| Deep learning | Chapter 37 and Theme O keep AI inside the device out of the book | Absent | Everything, and the reason why it stays outside MiniDAQ's product |

So the book needs an on-ramp before Part I, and a new Part on parallel computing at the end of
Volume 2. The existing chapters stay as they are: they become the second step after each
foundation chapter, not something the new chapters repeat.

## 2. What this plan adds

1. **Part 0, "Foundations"**, seven chapters F1 to F7 at the start of Volume 1, written for a
   reader who knows how to program but has never used these topics. Each ends where a chapter
   of Part I begins, and says which one.
2. **Part XII, "Parallel computing, GPUs and learned reconstruction"**, four chapters 46 to 49
   at the end of Volume 2, after Part XI. GPU code is optional: the book builds, every exercise
   runs and CI passes on a machine without a GPU.
3. **Change request CR-0040** (approved 2026-11-25, all optional) for the dependencies Part XII needs: the CUDA toolkit as an
   optional build target of the reconstruction tool, OpenMP from the compiler, and PyTorch as an
   optional test oracle. None of them is part of the acquisition product.

### Why Part 0 is lettered and Part XII comes last

- **Lettered chapters.** Numbering the foundations 1 to 7 would renumber the forty chapters after
  them. Their numbers are in 171 exercise IDs, the exercise and measurement directories
  (`exercises/ch03`), the solutions, problem reports, change requests, ADRs and the trace matrix.
  So the foundation chapters are F1 to F7, their exercises F1.1 and so on, and their directories
  `exercises/f1` to `exercises/f7`. The book build gives Part 0 its own counter, as it does for
  the appendices (verify: the LaTeX and EPUB numbering with `\thechapter` set to `F\arabic`;
  the fallback is unnumbered chapters whose titles carry "F1").
- **Part XII after Part XI.** Chapters 41 to 45 are already named in approved records (CR-0036,
  CR-0037, ADR 0040, ADR 0041, the architecture description). Part XII takes the next numbers.
  It builds on Chapter 28 (reconstruction) and Chapter 31 (scientific Python), not on Part XI,
  so a reader can go to it straight from Part VI; the reading paths say so.

## 3. Part 0: Foundations (Volume 1, before Part I)

The Part opener says who it is for: a reader who can write a loop and a function in some
language and has compiled a C++ program, and wants the rest from first principles. A reader who
knows a chapter's topic takes its "Check yourself" first and skips the chapter if they pass.

Every chapter follows the book's recipe (objectives, prerequisites and time, sections from the
intuition to a worked example, exercises with starters that fail, check yourself, summary,
further reading). Instead of a MiniDAQ milestone, each ends with **"Reading MiniDAQ"**: a guided
reading of the MiniDAQ code that uses the chapter's ideas, with the questions a reviewer asks
of it. Part 0 changes no MiniDAQ product code, requirement or interface.

Each chapter is about 24 pages and has four exercises, at least one marked (A), an audit of a
recorded change (Theme Q). Its code builds with the project's presets and its tests run in
`ctest -L unit`, with the label `foundations`.

### F1. C++ from the ground up

The core language and the standard library, for a reader who has written C or another language.

- **The compilation model.** Translation units, headers, the preprocessor, the linker, the one
  definition rule; what an undefined reference means; a three-file program built by hand, then
  with CMake.
- **Values, references and pointers.** Objects and their lifetime, the stack and the heap, `const`,
  references, raw pointers and why production code rarely owns through them.
- **Classes.** Constructors and destructors, RAII as the one idea that makes C++ safe, the rule
  of zero, three and five, copy and move shown with a counting type.
- **Templates and the standard library.** Function and class templates; `std::vector`,
  `std::array`, `std::string`, `std::unordered_map`; iterators and the algorithms; lambdas and
  captures.
- **Errors.** Exceptions, error codes, `std::optional`; where each belongs.
- **Reading MiniDAQ.** `Single`, `Quantity` and the decoder, with the questions of Chapter 1.
- Exercises: F1.1 a RAII file handle; F1.2 a rule-of-five buffer with a counting test; F1.3
  algorithms instead of loops on singles; F1.4 (A) a class that leaks on an exception.
- Leads to Chapter 1.

### F2. Modern C++, from C++11 to C++23

What each standard added, why, and how MiniDAQ uses it. The chapter is a timeline with a running
example: the energy spectrum of a list-mode file, rewritten as each feature arrives.

- **C++11 to C++17.** `auto`, move semantics, smart pointers, `constexpr`, structured bindings,
  `std::string_view`, `std::variant`, `if constexpr`, class template argument deduction.
- **C++20.** Concepts, ranges and views, `std::span`, `std::format`, the three-way comparison,
  `consteval`, coroutines (the idea, and `std::generator` in C++23 as the form a reader uses),
  modules (what they promise, and ADR 0035's reason to leave them out).
- **C++23.** `std::expected` and its monadic operations, deducing `this` (explicit object
  parameters), `std::print`, `std::ranges::to`, `std::mdspan` for an image or a sinogram,
  `std::flat_map`, `if consteval`, `std::to_underlying`, `std::unreachable`,
  `std::move_only_function`, `std::byteswap`, multidimensional `operator[]`.
- **What your compiler supports.** A table of each feature against GCC 13 (Ubuntu 24.04), the
  compiler of Ubuntu 26.04 and Clang, and the feature-test macros that check it at compile time
  (verify: each row against the compilers' status pages before writing; `std::mdspan` and
  `std::flat_map` are expected to need GCC 15).
- **Reading MiniDAQ.** The `std::expected` shim and its removal (Theme N), the concepts of the
  event processors.
- Exercises: F2.1 the spectrum with ranges and `std::ranges::to`; F2.2 a sinogram view with
  `std::mdspan`; F2.3 a `std::generator` over a list-mode file; F2.4 (A) a view that dangles.
- Leads to Chapters 1 and 2. Theme N updates Chapter 1's section "What C++23 adds" to point here
  and keeps only the production rules.

### F3. Linux for the C++ engineer: the shell and the toolchain

- **The shell.** Files, directories, permissions, pipes and redirection, environment variables,
  `grep`, `find`, `xargs`, a script with `set -euo pipefail`, why the book's scripts quote every
  variable.
- **Packages and the system.** `apt`, `/usr`, `/etc`, `/proc`, `/sys`, `systemd` units and
  `journalctl`, users and groups, `sudo` and why MiniDAQ's service does not run as root.
- **The toolchain.** What `g++` runs (preprocessor, compiler, assembler, linker), object files,
  static and shared libraries, `ldd`, `nm`, `objdump`, `readelf`, rpath, symbol visibility,
  sanitizers as compiler options.
- **Looking at a running program.** `ps`, `top`, `strace`, `ltrace`, `lsof`, `/proc/<pid>`,
  core dumps enabled and found.
- **Reading MiniDAQ.** The service's `systemd` unit and its hardening, the build presets, the
  installed tree of `packaging/`.
- Exercises: F3.1 a script that finds the run with the most dropped events; F3.2 a shared
  library built and loaded, then the missing-symbol error fixed; F3.3 an `strace` of the server
  explained line by line; F3.4 (A) a release script that deletes the wrong directory on an
  empty variable.
- Leads to Chapters 4, 21 and 32.

### F4. Linux systems programming

The kernel's interface as a C++ program sees it, each call wrapped in RAII and `std::expected`.

- **Processes.** `fork`, `exec`, `wait`, exit codes, zombies; threads against processes.
- **File descriptors.** `open`, `read`, `write`, `close`, `errno`, short reads and writes and the
  loop that handles them, `O_CLOEXEC`, `fsync` and durability (the list-mode sink's rule
  "durable before acknowledged").
- **Signals.** Delivery, masks, async-signal safety, why a handler only sets a flag or writes to
  a descriptor and never does the work itself, `signalfd`, `SIGPIPE`.
- **Waiting for many things.** Blocking calls, `poll` and `epoll`, `eventfd` to wake a loop,
  `timerfd`; an event loop written from zero; level and edge triggering.
- **Sharing memory between processes.** `mmap` of a file and of shared memory, `memfd`, and the
  synchronization it still needs.
- **Sockets, the first step.** A TCP echo server and client, with framing; Chapter 23 goes on
  from there.
- **Reading MiniDAQ.** The control server's `poll` loop and its `eventfd`, the server's signal
  handling in `minidaq/apps/minidaq_server.cpp`, the list-mode sink's `fsync` order.
- Exercises: F4.1 a child process supervisor with exit codes; F4.2 an `epoll` loop that serves
  two sockets and a timer; F4.3 a clean shutdown on `SIGTERM`; F4.4 (A) a write loop that loses
  data on a short write.
- Leads to Chapters 4, 6, 22 and 23.

### F5. Concurrency from zero

- **Threads.** What a thread is and what it shares; `std::thread` and `std::jthread`; join,
  detach and why detach is almost always wrong; passing data in and out.
- **Data races.** A counter that loses increments, shown failing and found by ThreadSanitizer;
  what undefined behavior means for a race.
- **Mutual exclusion.** `std::mutex`, `std::lock_guard`, `std::unique_lock`, `std::scoped_lock`,
  `std::shared_mutex`; critical sections kept short; a monitor class.
- **Waiting.** Condition variables, spurious wakeups and the predicate, a bounded blocking queue
  written from zero; `std::counting_semaphore`, `std::latch`, `std::barrier`; stop tokens.
- **Deadlock.** The four conditions, lock order, `std::scoped_lock` on several mutexes, the
  deadlock of Chapter 6 found again.
- **Tasks.** `std::async`, `std::future`, `std::promise`, `std::packaged_task`; a thread pool
  written from zero; why the acquisition uses fixed threads and the reconstruction a pool.
- **The parallel algorithms.** Execution policies, what they need from the standard library
  (verify: libstdc++'s parallel backend needs TBB, which is not an approved dependency, so the
  text shows them and Chapter 46 measures OpenMP instead).
- **A first atomic.** `std::atomic<int>` as the fix for the counter, and the bridge to Chapter
  3's memory model.
- Exercises: F5.1 a race found with TSan and fixed two ways; F5.2 a bounded blocking queue
  with a stress test; F5.3 a thread pool with futures; F5.4 (A) a recorded change that deadlocks
  under one schedule only.
- Leads to Chapter 3.

### F6. Design patterns in modern C++

Each pattern is shown in three forms where they exist (inheritance, templates, `std::function`
or `std::variant`), with what each costs, measured, and the MiniDAQ code that uses it or the
reason it does not. Appendix A keeps the architecture-level patterns; this chapter is the code
level, and points there.

- **Why patterns, and when not.** SOLID in one page each, with a counterexample.
- **Creating objects.** Factory and registry (the source chosen by `source.type`), builder (a
  configuration), and why singleton is an anti-pattern in a testable system.
- **Structure.** Adapter (ports and adapters again), decorator (a stage that counts or traces),
  pimpl and the stable ABI, composite.
- **Behavior.** Strategy (the coincidence window policy), observer (the event push of control
  API 4.0, Theme M), command (control requests), state (the acquisition state machine, Chapter
  6), template method against CRTP, visitor with `std::variant` and `std::visit`, null object.
- **C++ idioms.** RAII and scope guards, type erasure written from zero, policy-based design,
  CRTP, tag dispatch replaced by concepts.
- **Concurrency patterns.** Producer-consumer, pipeline, active object, monitor, reactor (F4's
  event loop), thread pool, double buffering.
- **Reading MiniDAQ.** The adapters of `minidaq/src/control/adapters.cpp`, the state machine's
  table, and the observer of API 4.0 once Theme M has built it.
- Exercises: F6.1 a registry of sources with a test of an unknown type; F6.2 the same strategy
  three ways, benchmarked; F6.3 a visitor over control requests; F6.4 (A) an observer that
  calls back under its own lock.
- Leads to Chapter 6 and Appendix A.

### F7. Data structures and algorithms for a DAQ, up to lock-free

- **Cost models.** Big-O and why the cache decides as often as it does (Chapter 2's numbers);
  amortized cost; measuring both.
- **The standard containers inside.** `std::vector` growth and invalidation, `std::deque`,
  `std::list`, `std::map` as a red-black tree, `std::unordered_map`'s buckets and its load factor;
  which to pick, measured on singles.
- **Containers the standard did not have.** Flat maps (and `std::flat_map` in C++23), a
  small-buffer vector, intrusive lists, a circular buffer, a bitset of channels.
- **Heaps and merging.** Binary heaps, `std::priority_queue`, the k-way merge of time-ordered
  streams that the multi-node sorter uses (Chapter 41).
- **Memory.** Arenas, pools and free lists, `std::pmr` and its resources; when they help.
- **Lock-free from zero.** Compare-and-swap, the Treiber stack, the ABA problem shown failing,
  the Michael-Scott queue, memory reclamation (hazard pointers, epochs, and the C++26 facilities;
  verify their status in the compilers), the seqlock for a status snapshot; progress
  guarantees (lock-free, wait-free, obstruction-free); when a lock is faster.
- **Testing them.** Stress tests, TSan, a small exhaustive scheduler that runs every interleaving
  of two threads for a few steps, linearizability checked against a sequential model.
- **Reading MiniDAQ.** `spsc_ring.hpp`, `mpmc_queue.hpp`, `channel.hpp` and the flight
  recorder.
- Exercises: F7.1 the k-way merge with a heap and its property test; F7.2 an arena with a test
  that the hot loop does not allocate; F7.3 a Treiber stack with ABA shown and then fixed; F7.4
  (A) a lock-free queue whose reclamation frees a node another thread still reads.
- Leads to Chapters 2, 3 and 10.

## 4. Part XII: Parallel computing, GPUs and learned reconstruction (Volume 2, after Part XI)

The Part works on the reconstruction tool (`recon/`, Chapter 28), which is a tool and not part
of the acquisition product (its requirements are SRS-REC, class "tools"). The acquisition stays
on the CPU: the Part opener says why (latency, determinism, certification of a GPU driver) and
what a team weighs before moving anything of the product to a GPU.

**GPU code is optional.** The rule, checked in CI:

- Every GPU kernel has a CPU path that computes the same thing and is the oracle of its tests.
- The CUDA target is built only when CMake finds the toolkit (`MINIDAQ_BUILD_CUDA`, default
  off). Without it the book builds, every exercise has a CPU path, and `ctest -L unit` passes.
- Tests that need a device carry the label `gpu` and report "skipped" when no device is found.
- A CI job builds the CUDA target with the toolkit and no GPU (compile only), so the code cannot
  rot; GitHub's standard runners have no GPU (verify: whether a GPU runner is available to the
  project, and its cost, before relying on one).
- The reader without an NVIDIA GPU (for example on Apple Silicon) runs the CUDA exercises on a
  cloud GPU or a free notebook service, or does the CPU path and reads the measured results that
  the book prints. Each chapter says which. Metal, HIP and SYCL are named, not taught.

### 46. Parallel computing on the CPU

- **How much faster can it get.** Amdahl and Gustafson, measured on the projector; the roofline
  model and arithmetic intensity; memory-bound against compute-bound.
- **Data and task parallelism.** Chunks and work stealing, scheduling, load balance across
  views of different cost.
- **OpenMP.** `parallel for`, schedules, reductions, `simd`; against the projector's
  `std::jthread` chunks of Chapter 28.
- **Reductions and reproducibility.** Backprojection with atomic adds against one image per
  thread; why a parallel sum of floats changes with the thread count, and how a regulated tool
  keeps results reproducible (a fixed reduction order, Kahan summation, tolerances stated in the
  requirement).
- **Scaling, measured.** Strong and weak scaling of OSEM on 1 to N threads, false sharing in the
  image, NUMA in one page.
- Exercises: 46.1 the projector with OpenMP and its scaling curve; 46.2 a reproducible
  parallel sum; 46.3 a roofline of the backprojector; 46.4 (A) a parallel backprojection with a
  race that changes the image by less than the test's tolerance.

### 47. GPU programming from zero with CUDA

- **What a GPU is.** Streaming multiprocessors, warps, SIMT, the memory hierarchy (registers,
  shared memory, L2, global memory), latency hidden by occupancy.
- **The programming model.** Kernels, grids, blocks and threads; indexing; a vector add and a
  histogram of energies.
- **Memory.** Allocation, copies, pinned memory, unified memory, coalescing, shared memory tiles,
  bank conflicts, atomics.
- **Streams and overlap.** Asynchronous copies, streams, events and timing; overlapping transfer
  and compute.
- **CUDA in a C++ code base.** RAII wrappers for device memory and streams, error checking that
  cannot be forgotten, CMake's CUDA language as an optional target, the CPU fallback behind one
  interface.
- **Measuring.** Nsight Systems and Nsight Compute, what occupancy and achieved bandwidth say.
- **Testing GPU code.** The CPU path as the oracle, tolerances, compute-sanitizer for races and
  out-of-bounds accesses.
- **Other ways to the GPU.** HIP, SYCL, OpenMP offload and the C++ parallel algorithms on GPUs,
  each in a paragraph.
- Exercises: 47.1 an energy histogram with shared-memory privatization; 47.2 a tiled image
  convolution; 47.3 overlap of copy and compute measured; 47.4 (A) a kernel with a race on
  shared memory that compute-sanitizer finds.

### 48. GPU image reconstruction

- **Mapping the projector.** Ray-driven forward projection (Joseph's method, one thread per
  line) and voxel-driven backprojection (one thread per pixel, a gather instead of a scatter);
  why the two are each other's adjoint only if built so, and the dot-product test of SRS-REC-001
  on the GPU.
- **MLEM and OSEM on the GPU.** Keeping the image and the sinogram on the device across
  iterations; subsets; the sensitivity image.
- **List-mode and time of flight.** One thread per event, the TOF kernel of Chapter 39, atomics
  in the backprojection.
- **Precision and determinism.** Single against double precision, fused multiply-add, atomics
  that change the order of a sum; the requirement that the GPU projector gives the CPU
  projector's projections to a stated tolerance, and the image after N iterations within a
  stated bound.
- **Measured.** CPU (one thread, N threads with OpenMP) against GPU for the book's phantom and a
  larger one, with copies counted.
- **A GPU in a regulated tool.** The CUDA runtime as SOUP, the driver as part of the platform,
  version pinning, equivalence across GPU models, what the release record keeps; open-source
  reconstruction packages with GPU projectors named for further reading (verify: their current
  names, licenses and GPU support before citing).
- Exercises: 48.1 the forward projector on the GPU against `recon_cpp`; 48.2 the voxel-driven
  backprojector and its dot-product test; 48.3 OSEM on the GPU with the image kept on the
  device; 48.4 the list-mode TOF backprojection with atomics, and its tolerance justified.
- **MiniDAQ milestone.** `recon_cuda`, an optional projector behind the same interface as
  `recon_cpp`, selected at run time, with new requirements SRS-REC-0nn (grep the SRS for the next
  free number before choosing).

### 49. Deep learning for PET, from zero

- **What a network is.** Tensors, layers, a loss, gradient descent, backpropagation written by
  hand for a two-layer network, then convolutions and a small U-Net.
- **Training it to denoise.** Low-count and high-count reconstructions of the same simulated
  phantom from MiniDAQ's simulator as the training pairs; training, validation and test sets;
  data leakage and how a phantom family hides it; overfitting.
- **Judging the result.** Chapter 30's image-quality measures, against the network's loss;
  hallucinated structure, shown; why a lower noise is not a better image.
- **Learned reconstruction, the idea.** Unrolled iterations with a learned step, in one section;
  read, not built.
- **Running it on the GPU.** Inference with the network's weights on the CUDA kernels of
  Chapter 47, against the CPU result.
- **Why this stays out of MiniDAQ's product.** AI inside a device, what the regulations then ask
  (machine-learning-enabled software, predetermined change control plans, the EU AI Act; verify
  each before citing): the chapter states it, and the network stays a research tool with its own
  record, outside the product. This keeps roadmap 3.0.0's Theme O decision.
- The network is written in numpy, with no new dependency, so every reader can train it on a
  CPU in minutes at the book's image size. A PyTorch version of the same network is the optional
  oracle: when PyTorch is installed, a test loads the same weights into both and compares the
  outputs (CR-0040); a sidebar shows the PyTorch code a team would use.
- Exercises: 49.1 backpropagation checked against finite differences; 49.2 the denoiser
  trained, with its learning curves; 49.3 a test set that leaks, found and fixed; 49.4 (A) a
  denoiser that scores well and removes a lesion.

## 5. Dependencies (CR-0040, approved)

| Item | Used by | Ships in the product | Status |
|---|---|---|---|
| CUDA toolkit (nvcc, runtime) | `recon_cuda`, Chapters 47 to 49 | No | Optional build target; SOUP of the reconstruction tool and a tool entry for nvcc and compute-sanitizer; version pinned in CI's compile-only job (verify: the CUDA release that supports the compiler of Theme N as a host compiler) |
| OpenMP (GCC's `libgomp`) | the reconstruction tool, Chapter 46 | No | Optional (`MINIDAQ_BUILD_OPENMP`, off by default; the `std::jthread` path stays); comes with the compiler; recorded as SOUP of the tool |
| PyTorch | the optional test oracle of Chapter 49 | No | Test only, never required; pinned, CPU build; `analysis/requirements.lock` "Test only" section, as pydicom |
| Intel TBB | not used | No | Not added: Chapter F5 shows the parallel algorithms without it |

CR-0040 was approved on 2026-11-25 by the coordinator under the author's delegation, on the
condition that all three stay optional: the default build, the book and CI need none of them.

## 6. Page budget

The Third Edition is two volumes (roadmap 3.0.0, Theme K), each at most 828 pages. From the word
counts on 2026-11-25 (about 440 words a page including figures):

| | Today | Added | Estimate |
|---|---|---|---|
| Volume 1: front matter, Parts I to V | about 515 pages | Part 0, seven chapters of about 24 pages | about 690 pages, with 2.3.0's figures |
| Volume 2: Parts VI to X, Appendix A | about 280 pages | Part XI (about 110), Appendices B and C (about 40), Part XII (about 110) | about 560 pages |

Both stay under the limit with margin. The two-volume build (Theme K) therefore moves to the
first milestone of 3.0.0-dev: a single volume cannot take the new Parts.

## 7. Milestones (inside 3.0.0-dev; roadmap 3.0.0, section 5)

| Milestone | Content | Exit criterion |
|---|---|---|
| First (with Theme N) | Two-volume build; Part 0 opener; build numbering for F chapters | Both volumes build, each under 828 pages; an empty F1 numbers as "F1" in PDF, EPUB and web |
| Second: Theme F | Chapters F1 to F7, in that order, each with its exercises, solutions and "Reading MiniDAQ" | Chapter recipe complete; exercises' starters fail and solutions pass in `ctest -L unit`; Volume 1 under 828 pages |
| After Part XI: Theme G | Chapters 46 to 49; `recon_cuda`; CI compile-only job | Chapter recipe complete; CPU-only CI green; `gpu` tests pass on one GPU machine and the run is in the chapter's record |

Each chapter is readable on the download page and in the web edition as soon as it is merged
on main, before the release, as every chapter is today.

## 8. Risks

| Risk | Effect | Response |
|---|---|---|
| The foundations repeat Part I | Pages spent twice; a reader bored | Each F chapter stops where a Part I chapter starts, and the Part I chapter's prerequisites point back to it; the review checks every overlap |
| Beginner chapters in a book written for practitioners | The tone shifts | Same recipe and voice; the beginner is addressed in the prerequisites, not in the prose; "Check yourself" lets a reader skip |
| C++23 features missing in the compiler | Examples do not build | Feature-test macros; a feature the compiler of Theme N lacks is shown as printed code with "verify", not built |
| No GPU on CI or on the reader's machine | GPU code rots; exercises cannot be done | CPU oracle for every kernel; compile-only CI job; `gpu` label skipped without a device; cloud GPU documented |
| A GPU result that differs from the CPU | A wrong image accepted, or a correct one rejected | Tolerances stated in the requirements and justified from the arithmetic; the dot-product test on the device |
| Deep learning read as an endorsement of AI in the device | A reader puts a network into a product without the regulatory work | Chapter 49 states what that work is, and the network stays a research tool outside the product |
| Scope: eleven chapters added to a release that must ship | 3.0.0 slips | The list is fixed here. If 3.0.0 is late, the cut order is: Chapter 49 first, then Chapter 48 folded into 47; Part 0 is never cut, because the author asked for it first |

## 9. Decisions taken

Taken by the coordinator under the author's standing delegation on 2026-11-25, as recommended,
when it accepted this plan and approved CR-0040:

1. Part 0 lettered F1 to F7 before Part I, rather than renumbering the book (recommended).
2. Part XII after Part XI with chapters 46 to 49 (recommended), rather than splitting Part VI.
3. GPU optional, with a CPU oracle and a compile-only CI job (recommended; the author's
   direction of 2026-11-25 through the coordinator).
4. The deep-learning chapter in numpy with PyTorch only as an optional oracle (recommended),
   rather than PyTorch required.
