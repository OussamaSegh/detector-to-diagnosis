<!-- Design sample for book/docs/proposals/render.py. Not a chapter of the book.
     The renderer is not called by book/build.sh. -->

# Ownership the next engineer can audit {#ch01}

::: box-why
A scanner stays in service for ten years or more. The DAQ software you lead will be read, changed, and audited long after you wrote it. Ownership that a reader can see in the signature is the part an auditor can check without reading every line.
:::

**A day in the life.** It is 8:40 on a Tuesday. A clinical site reports a faint band in a 40-minute scan. The singles rate for one detector block jumps to about 4.29 billion counts per second, for one sample, just under the limit of a 32-bit counter. Somebody subtracted two `uint32_t` values after a reset, and the subtraction wrapped. Nothing crashed, every test passed, and a patient image was quietly wrong.

This chapter is about making that class of mistake hard to write: one owner for each buffer, views that cannot outlive it, and types that refuse to add a time to an energy.

## Learning objectives {.unnumbered}

After this chapter you can:

1. Tell an owning type from a view by reading a function signature.
2. Apply the Rule of 0, and say when a raw resource still needs the Rule of 5.
3. Name the ways a view dangles, and the tool that catches each one.
4. Choose `std::expected` or an exception, and say why the hot path is different.

## Prerequisites and estimated time {.unnumbered}

You should be comfortable with C++17: classes, templates, `std::unique_ptr`, and the standard containers. Reading time is about three hours. The exercises take five to six hours.

```{=latex}
\clearpage
```

## Ownership and lifetime

### One owner

Every object has exactly one owner that decides when it dies. In a DAQ that is the difference between a pipeline that runs for eight hours and one that corrupts memory after forty minutes. Buffers of singles move from the receiver to the decoder, the sorter, and the writer. At each hand-off somebody must know whether they now own the buffer or are only looking at it.

Owning types live in data members and in local variables. Views travel through function parameters. A function that takes `std::span<const Single>` looks during the call and then forgets what it saw. A function that takes `std::unique_ptr<Buffer>` takes the owner with it.

> If you can avoid defining default operations, do.

::: listing-caption
*minidaq/include/minidaq/core/run_summary.hpp*
:::

```cpp
// Rule of 0: the members already copy and destroy themselves.
class RunSummary {
 public:
  void add(const Single& s) { energies_.push_back(s.energy); }

 private:
  std::string run_id_;
  std::vector<KeV> energies_;
};
```

The compiler writes the copy, the move, and the destructor, and each one does the right thing member by member. You write a destructor only when a member cannot. Then you think about all five special members, not just the one that frees the resource.

| Need | Use | What it costs |
|---|---|---|
| One owner | `std::unique_ptr` | the same as a pointer |
| A view of contiguous data | `std::span` | a pointer and a length |
| Shared, lifetime unclear | `std::shared_ptr` | an atomic reference count |
| May already be dead | `std::weak_ptr` | the cost of `std::shared_ptr` |

::: box-mistakes
- A destructor written "for safety" on a class whose members already clean up. It suppresses the implicit move, so the class silently copies.
- `std::shared_ptr` used because the ownership was unclear. Sharing does not decide who owns the buffer.
- A `std::string_view` returned from a function that built the string. The view dies with the temporary.
:::

::: box-regulated
Record the strong types and the warning set as risk controls, and keep the sanitizer log with the release evidence. An auditor should be able to point at the signature, the build, and the log, and see the same rule.
:::

### Where a view dangles

A view is a pointer and a length. It does not keep the memory alive. Three cases show up in review, and all three have happened in DAQ code.

The function that builds a string and returns a view of it. The string is a local. The view is a copy of its pointer. The caller receives a view of freed memory, and the next use is undefined. Return a `std::string` instead, and let the caller decide if it wants a view of that.

The view stored in a member. A struct that holds a `std::string_view` for a path looks cheap, and it is a dangling pointer waiting for the next refactoring. Store a `std::string` when the struct owns the path. Take a view only as a parameter, for the length of the call.

The view into a container across a reallocation. A reference to the front of a vector does not survive a `push_back` that grows it. The compiler cannot see the mistake. AddressSanitizer reports it at the first use of the old reference.

```cpp
std::string_view crystal_label(int id) {
  std::string s = "crystal-" + std::to_string(id);
  return s; // the view dies with s
}
```

Keep the view honest with three rules. Never return a view of a local or of a temporary: return an owning type. Never store a view in a member unless the class is itself a view and the header says so. Do not hold a view, a reference, or an iterator across a call that may reallocate. Lifetime warnings catch the simple return. The sanitizer catches the container, which the compiler does not.

```{=latex}
\clearpage
\vspace*{1.15in}
\noindent A buffer moves from stage to stage with one owner. A monitor that only reads it during a call receives a span and keeps nothing.

\begin{center}
\resizebox{0.96\textwidth}{!}{%
\begin{tikzpicture}[node distance=0.55in]
  \node[stage] (rx) {receiver};
  \node[stage, right=0.42in of rx] (dec) {decoder};
  \node[stage, right=0.42in of dec] (sort) {sorter};
  \node[stage, right=0.42in of sort] (wr) {writer};
  \draw[arr] (rx) -- (dec);
  \draw[arr] (dec) -- (sort);
  \draw[arr] (sort) -- (wr);
  \node[own, below=0.62in of dec] (buf) {buffer};
  \draw[ownline] (dec.south) -- (buf.north);
  \node[stage, below=0.62in of rx] (hist) {histogram};
  \node[stage, below=0.62in of wr] (mon) {monitor};
  \draw[view] (hist.east) -- (buf.west);
  \draw[view] (mon.west) -- (buf.east);
\end{tikzpicture}}
\captionof{figure}{Owners and views on the pipeline. The buffer has one owner. The histogram and the monitor only look.}\label{fig:owners}
\end{center}

\noindent Read the stem under the decoder as ownership, and the dashed arrows as views. A view is valid for the call and meaningless after it. The same drawing is the pattern for every pipeline figure in the book: one solid owner, and a dashed arrow for anything that only looks.
```
