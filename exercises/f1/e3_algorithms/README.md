# Exercise F1.3 (E): Algorithms instead of loops on singles

**Goal.** Answer seven questions about a batch of singles, each with the standard algorithm that
names it: `count_if`, `max_element`, `accumulate`, `sort`, `is_sorted`, `erase_if` and a map. The
function names say what is computed; the algorithm says how, in one line a reviewer can check.

**Time.** 45 minutes.

**Acceptance tests** (`tests/test_singles.cpp`): each function on a small batch and on its empty
case, and a comparison with a plain loop on 5,000 random singles.

**Hint.** The ranges forms (`std::ranges::count_if(s, pred)`) take the whole container and a
projection: `std::ranges::max_element(s, {}, &Single::energy_kev)` compares energies without a
lambda. Sort by time and then by crystal, or two singles at the same time come out in either order.
