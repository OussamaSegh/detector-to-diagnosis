# Exercise 1.6 (M, extra): Constraining event processors with concepts

**Goal.** MiniDAQ stages accept "anything that can consume singles". Define:
- `ex::SingleSink<T>`: `t.consume(const Single&)` is valid and `t.count()` returns
  something convertible to `std::uint64_t`.
- `ex::SingleFilter<T>`: `f.accept(const Single&)` returns `bool`.
- `ex::feed(std::span<const Single>, Filter&, Sink&)`: passes accepted singles to the sink
  and returns how many were accepted. It must not compile for types that do not model the
  concepts.

**Time.** 45 to 60 minutes.

**Acceptance tests.** Trait variables `ex::is_sink_v<T>` and `ex::is_filter_v<T>` (defined
from your concepts) are true for the provided good types and false for the bad ones;
`feed` with an energy-window filter keeps exactly the singles in [350, 650] keV.
