# The recorded change: "Add a run log with a header and an index"

This change was written by a coding assistant and is frozen here as it was proposed. Review it as
you would review a colleague's change, then fix it.

## Specification given to the assistant

> Add `RunLog`, which holds the header of a run (the run number and the operator's note) and an
> index of up to `capacity` block offsets. `capacity` must be at least 1; a capacity of 0 is a
> configuration error and throws `std::invalid_argument`. Both parts live as long as the log.

## Transcript (excerpt)

> **Assistant:** I added `RunLog` in `run_log.hpp`. The constructor allocates the header and the
> index on the heap and the destructor deletes both, so there is no leak. `Index` validates its
> capacity and throws on 0, as specified. The unit tests pass.

## The patch

```diff
+class RunLog {
+ public:
+  RunLog(int run, std::string note, std::size_t capacity)
+      : header_{new Header{run, std::move(note)}}, index_{new Index{capacity}} {}
+  ~RunLog() {
+    delete index_;
+    delete header_;
+  }
+  ...
+ private:
+  Header* header_;
+  Index* index_;
+};
```

The whole file is `starter/run_log.hpp`.
