# Exercise 4.4 (M, extra): An arena that never page-faults on the hot path

**Goal.** Chapter 2's arenas removed `malloc` from the hot path, but the first write to each
fresh page of an arena still costs a page fault: a trip into the kernel of a microsecond or
more, at an unpredictable moment. Build an arena whose memory is faulted in (and optionally
locked) when it is created, and prove with the kernel's own counters that using it causes no
faults.

**Time.** 90 minutes.

**Tasks.**
1. `ex::PrefaultedArena(bytes, options)` maps `bytes` (rounded up to whole pages) of anonymous
   memory with `mmap`, then touches every page so that it is backed by real memory before the
   constructor returns. Throw `std::system_error` if `mmap` fails.
2. By default call `madvise(MADV_NOHUGEPAGE)` on the region so the measurement is about 4 KiB
   pages; with `options.huge_pages`, ask for transparent huge pages with `MADV_HUGEPAGE`
   instead (best effort).
3. With `options.lock`, `mlock` the region; if that fails, keep going and report it through
   `locked()`.
4. `allocate(n, align)` is a bump allocator: it returns `nullptr` when the arena is full or
   when `align` is not a power of two. `reset()` makes all of it available again.
5. The destructor unmaps. The type is move-only.

**Acceptance tests** (`tests/test_arena.cpp`): allocation rules, and the page-fault test:
writing every byte of a 32 MiB arena after construction must cost fewer than 64 minor faults
on the writing thread (`minidaq::rt::thread_page_faults()`), where the same writes to a plain
`mmap` region cost thousands. The fault test is skipped in sanitizer builds, whose shadow
memory faults on its own.

**Watch out.** *Reading* a never-written anonymous page does not allocate it: the kernel maps
the shared zero page, and your first write still faults. Touch pages by writing.

**Think about it:** what does `mlockall(MCL_CURRENT | MCL_FUTURE)` (which the pipeline uses)
give you that prefaulting one arena does not, and what does it cost at start-up?
