# Exercise 18.2 with a uniform generator

Measured 2026-10-25. The solution's five properties were compiled with the generator below in
place of the solution's (`exercises/ch18/e2_sorter_properties/solution/test_sorter_properties.cpp`,
`make_case`), against the subject with `EX_MUTANT=0..8`, g++ 13, `-O1`, 200 cases per property
(the default). The batch cuts are unchanged.

```diff
-    switch (src.pick(5)) { ... five kinds of time step ... }
-    double kev = 0.0;
-    switch (src.pick(4)) { ... edges of the gate, inside, anywhere ... }
+    t += src.draw_signed(-3'000, 5 * c.cfg.window.count());
+    const double kev = src.uniform(0.0, 1'000.0);
```

| Variant | Result |
|---|---|
| original | every property holds |
| mutant 1 (window excludes its edge) | survives |
| mutant 2 (paralyzable window) | survives |
| mutant 3 (second single opens the next window) | caught |
| mutant 4 (open window dropped at a batch end) | caught |
| mutant 5 (gate excludes its upper edge) | survives |
| mutant 6 (out-of-order singles not dropped) | caught |
| mutant 7 (lone last single not counted) | caught |
| mutant 8 (take_winner keeps the lowest sum) | survives |

Four of eight survive. Mutants 1 and 5 need an exact edge, which a uniform draw almost never
produces; mutants 2 and 8 need three singles inside one window, which uniform steps of up to
five windows produce too rarely for 200 cases. With the solution's generator all eight are
caught (CTest `ch18/e2_sorter_properties/solution/mutant_*`).
