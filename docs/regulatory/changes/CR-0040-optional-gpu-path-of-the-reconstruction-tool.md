# CR-0040: An optional GPU path for the reconstruction tool, and its dependencies

| Field | Value |
|---|---|
| Status | proposed |
| Requested | 2026-11-25, by the software lead |
| Source | improvement: roadmap 3.0.0, Theme G (docs/ROADMAP-3.0.0-foundations.md, sections 4 and 5) |
| Decision | pending |
| Commits | none yet |

## Description

Part XII of the Third Edition (Chapters 46 to 49) teaches parallel computing, GPU programming,
GPU image reconstruction and deep learning on the reconstruction tool. This change adds three
dependencies to the tool, none of them to the acquisition product:

- **OpenMP**, from the compiler's own runtime (GCC's `libgomp`), for the CPU-parallel projector
  of Chapter 46, behind a CMake option that is on when the compiler supports it.
- **The CUDA toolkit** (the compiler `nvcc`, the CUDA runtime and `compute-sanitizer`), for an
  optional projector `recon_cuda` with the interface of `recon_cpp` (Chapters 47 and 48). It is
  built only with `MINIDAQ_BUILD_CUDA=ON`, which is off by default; without it the build, the book
  and `ctest -L unit` are unchanged. Tests that need a device carry the CTest label `gpu` and
  report skipped when none is found. A CI job installs the toolkit and compiles the target
  without a GPU.
- **PyTorch**, CPU build, as an optional test oracle for the numpy network of Chapter 49, in the
  "Test only" section of `analysis/requirements.lock`, as pydicom and pynetdicom are; the test that
  uses it is skipped when it is not installed.

Intel TBB, which libstdc++ needs to run the parallel algorithms in parallel, is not added.

## Reason

The author asked on 2026-11-25 for the book to teach parallel computing, CUDA, GPUs for image
reconstruction and deep learning (roadmap 3.0.0, section 8, answer 7). Teaching GPU
reconstruction without GPU code would leave the reader with no code to run or test. Making the
GPU path optional keeps the project's rule that every reader and every CI runner can build and
test everything, with or without a GPU.

## Impact analysis

### Requirements

New requirements of the reconstruction tool, numbered from the next free SRS-REC ID (today
SRS-REC-009 is the last; grep before choosing): the GPU projector gives the projections of
`recon_cpp` (SRS-REC-004) to a stated tolerance and passes the dot-product test of SRS-REC-001
on the device; OSEM on the device gives the CPU image within a stated bound after a stated number
of iterations; the OpenMP projector gives the same result for any thread count within a stated
tolerance. SRS-REC-004 and SRS-REC-005 are verified again on the OpenMP path.

### Software items and safety class

The reconstruction tool only (class "tools" in the SRS). No item of the acquisition product
changes, and no class or segregation changes.

### Risk

No hazard of the product changes: the tool's images are not used for diagnosis (intended use).
The tool's own failure (a GPU result that differs from the CPU) is controlled by the CPU oracle in
every test and the tolerances in the requirements.

### SOUP

Added for the tool: OpenMP runtime (with the compiler), CUDA runtime (version pinned in CI's job;
verify the release that supports Theme N's compiler as a host compiler). Added as tools: `nvcc`
and `compute-sanitizer` (T2), PyTorch as a test oracle (T2), from TL-53 on. Each gets its
known-anomaly review in the SOUP list before Theme G is released.

### Interfaces and data formats

None. `recon_cuda` takes and returns the arrays of `recon_cpp`.

### Documents

SRS (new SRS-REC requirements), SOUP list, tool list, SBOM, `docs/architecture/architecture.md`
(the tool's optional projector), Appendix A (the decision "a reconstruction moved to a GPU"
becomes an ADR).

### Regulatory

No change to the intended use or to a safety-relevant function. Chapter 49's network stays a
research tool outside the product.

## Verification

`ctest -L unit` on a machine without a GPU (the CPU path, the `gpu` tests skipped); the
compile-only CUDA job in CI; `ctest -L gpu` on one machine with a GPU, its output kept in the
chapter's measurement record; the SBOM and SOUP checks.

## Decision

Pending. To be decided before Theme G starts.
