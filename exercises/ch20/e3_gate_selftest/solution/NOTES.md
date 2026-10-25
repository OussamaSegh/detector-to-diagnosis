# Exercise 20.3: notes on the solution

**Verdicts.** The control comes first: a gate that reports a problem on the correct tree would
"catch" every fault, so that case wins over the others. A gate that fails with a report that
does not match the planted reason did not show it can see the fault: it may have failed on
something the fault broke on the way (here a vague mutant that says "something is wrong").

**Faults.** The first set one would write has one fault per rule: a `.cpp` file without its
header and a TODO without an issue. Run against the broken gates, that set leaves three of the
seven unnoticed: `ignores_headers` (never looks at `.hpp` files), `header_anywhere` (accepts the
header on any line) and `any_number_will_do` (accepts `TODO(anna)`). Each needs a fault at a
boundary of the promise: the other file type, the header just past line two, a TODO with a
parenthesis that is not an issue. The final five faults catch all seven broken gates.

**For `tools/gate_selftest.py`.** Its faults follow the same rule. A fault per gate shows the gate
runs and reports; the boundaries of what each gate promises need faults of their own, and the
cheap way to find the missing ones is the one used here: break the gate in plausible ways and see
which breakage the self-test does not notice.
