# The recorded change: "Add a peak region and a label to Spectrum"

This change was written by a coding assistant and is frozen here as it was proposed. Review it,
then fix it.

## Specification given to the assistant

> `Spectrum` holds the counts of an energy histogram for one detector material. Add
> `peak_region(first, last)`, which gives the caller the counts of bins `first` to `last - 1`
> without copying them, and `label()`, which returns the material's name followed by
> " spectrum" for the plot title. Neither may change the spectrum.

## Transcript (excerpt)

> **Assistant:** I added both functions. `peak_region` returns a `std::span<const int>`, so it
> does not copy, and `label` returns a `std::string_view`, which is cheaper than a string. Both
> are `const`. It compiles without warnings and the example plot shows the right title.

## The patch

```diff
+  // The counts of bins [first, last), without a copy.
+  std::span<const int> peak_region(std::size_t first, std::size_t last) const {
+    return std::span<const int>{counts()}.subspan(first, last - first);
+  }
+
+  // "LSO spectrum", for the plot title.
+  std::string_view label() const { return material_ + " spectrum"; }
```

The whole file is `starter/spectrum.hpp`.
