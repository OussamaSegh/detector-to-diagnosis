# The NeuroLF Engineer: MiniDAQ and book sources

Companion repository for *The NeuroLF Engineer: Modern C++, PET Data Acquisition and
Medical Device Software*. It contains:

| Path | What |
|---|---|
| `minidaq/` | MiniDAQ, a simulated PET data acquisition chain in C++20, grown one milestone per chapter |
| `exercises/chNN/` | Every coding exercise: `starter/` (TODOs, failing tests), `solution/`, shared `tests/` |
| `python/` | `minidaq_analysis`, the Python analysis and reconstruction package (from Part II) |
| `docs/` | Architecture, decision records and the regulatory file (from Part III) |
| `benchmarks/`, `fuzz/`, `tools/`, `ci/` | Benchmarks, fuzzers, generators and CI scripts |
| `book/` | The book and solutions manual sources (Pandoc Markdown) and their build script |

MiniDAQ is a learning project, not a medical device.

## Quick start (Ubuntu 24.04, about 10 minutes)

```bash
sudo apt-get install -y build-essential cmake ninja-build git clang-18 libclang-rt-18-dev
git clone <this repo> neurolf && cd neurolf      # or unzip minidaq-vX.Y.Z.zip
ci/run_all.sh                                    # configure, build and test: GCC, Clang, ASan+UBSan
```

`ci/run_all.sh` runs the same gates as CI. To work with one configuration:

```bash
cmake --preset debug            # or: release, clang-release, asan-ubsan, tsan, coverage
cmake --build --preset debug
ctest --preset debug -LE starter
```

**macOS:** install Xcode command line tools, then `brew install cmake ninja llvm`; use the
`clang-release` and `asan-ubsan` presets with `CMAKE_CXX_COMPILER=$(brew --prefix llvm)/bin/clang++`.
Real-time and networking chapters (4, 22, 23, 25) need Linux.
**WSL2:** follow the Ubuntu instructions inside an Ubuntu 24.04 distribution.

Offline builds: configure with `-DMINIDAQ_USE_SYSTEM_DEPS=ON` after
`sudo apt-get install libgtest-dev libgmock-dev`.

## Chapters and tags

Every chapter's milestone is a git tag: `git checkout ch05` gives you the repository at the
end of Chapter 5, which is the starting point of Chapter 6. `ch00` is the empty starting
point. Book releases are tagged `book-vX.Y.Z`.

## Exercises

```bash
cmake --preset debug -DMINIDAQ_BUILD_STARTERS=ON
cmake --build --preset debug
ctest --preset debug -L starter -R ch01        # your work: fails until you solve it
ctest --preset debug -L solution -R ch01       # reference solutions: always green
```

## Building the book

```bash
sudo apt-get install -y pandoc texlive-xetex texlive-latex-extra texlive-fonts-extra \
  fonts-texgyre fonts-inconsolata graphviz librsvg2-bin latexmk epubcheck
book/build.sh            # EPUB + PDF of the book and the solutions manual into book/build/out/
```
