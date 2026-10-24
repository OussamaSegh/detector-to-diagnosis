# Exercise 4.4 notes

**What the test shows.** On the book's machine, writing 32 MiB of fresh `mmap` memory cost
8,192 minor faults, one per 4 KiB page; the same writes into the prefaulted arena cost none.
Timing the first and second `memset` of the region (7 runs, GCC 13.3 -O2) puts each fault at
1.2 to 2.0 us, median 1.5 us, including the kernel zeroing the page (VM numbers: verify on the
acquisition PC, for example with `perf stat -e minor-faults`). With transparent huge pages the
same region took 16 faults of 2 MiB each, at 52 to 83 us typical per fault and one of 5 ms:
fewer faults, but each one is a long stall, so huge pages must be prefaulted too. The faults
have not disappeared: they moved into the constructor, which runs before acquisition starts.

**Write, not read.** A read of an untouched private anonymous page maps the kernel's shared
zero page read-only. The first write then takes a copy-on-write fault anyway. Writing one
byte per page (through a `volatile` pointer so the compiler cannot drop the store) allocates
the page for real. `MAP_POPULATE` does the same inside `mmap` for writable private mappings;
the explicit loop shows what happens and works for memory you did not map yourself.

**Huge pages.** The test disables transparent huge pages (THP) on purpose, because with THP
set to `always` (as on the book's VM) the kernel may back the region with 2 MiB pages and the
baseline would show 16 faults instead of 8,192. For a real arena, huge pages are usually what
you want: fewer faults and far fewer TLB misses. With THP `madvise` mode, `MADV_HUGEPAGE` asks
for them; `khugepaged` may also collapse pages later, which is itself a source of latency
(verify: the kernel's `transhuge.rst` documentation).

**Locking.** Prefaulting does not stop the kernel from reclaiming or swapping the pages later
under memory pressure; `mlock` does. `mlockall(MCL_CURRENT | MCL_FUTURE)` covers every
mapping in the process, including thread stacks, the heap and libraries, and every future
mapping, which is why the pipeline uses it; the cost is that every later `mmap` and `malloc`
growth is faulted in and locked at once (slower start-up, more resident memory), and the
process needs `CAP_IPC_LOCK` or a large enough `RLIMIT_MEMLOCK`.
