# SPDX-License-Identifier: MIT
"""A review of tests/change.diff (Exercise 21.1, solution). See NOTES.md."""
FINDINGS = [
    {"line": 63, "severity": "blocker", "category": "concurrency",
     "text": "counts_ and total_ are written by the receive thread and read by rate() on the control "
             "thread with no lock and no atomics: a data race, undefined behavior, and torn or stale "
             "sums. The relaxed store of latest_s_ orders nothing. Give the meter a mutex, or make "
             "the slots atomics and say what each memory order pairs with."},
    {"line": 70, "severity": "blocker", "category": "correctness",
     "text": "i <= window_ reads counts_[16] when the window is 16: one past the array. And slots 0 "
             "to window-1 are not the last window seconds: the slots are indexed by second modulo "
             "16, so the window has to start from latest_s_ and go backwards."},
    {"line": 79, "severity": "blocker", "category": "lifetime",
     "text": "label() returns a string_view of a std::string temporary that is destroyed at the end "
             "of the return statement: every caller reads freed memory. Return std::string."},
    {"line": 83, "severity": "major", "category": "error-path",
     "text": "set_window() stores the value before it checks it, so a rejected 0 or 100 still "
             "becomes the window: 0 divides by zero in rate() (line 73), 100 reads far past the "
             "array. Check first, then assign; a failed call leaves the meter unchanged."},
    {"line": 60, "severity": "major", "category": "correctness",
     "text": "latest_s_ starts at 0, so the first add() with a real time in seconds (about 1.8e9) "
             "runs the loop 1.8e9 times on the receive thread, and so does any long gap. Only "
             "kSeconds slots can need clearing: bound the loop by min(now_s - last, kSeconds), and "
             "decide what a time that goes backwards means."},
    {"line": 110, "severity": "major", "category": "tests",
     "text": "The test sleeps a second for nothing (add() takes the time as an argument), checks "
             "only rate() > 0, which the off-by-one and the window bug both pass, and names no "
             "requirement. Test exact rates for a full window, a gap, and a window of 1, and the "
             "refusal of set_window(0)."},
    {"line": 64, "severity": "minor", "category": "correctness",
     "text": "total_ is written and never read. Remove it, or say what it is for in the status."},
    {"line": 1, "severity": "question", "category": "tests",
     "text": "The description says the meter is in the status as link_rate, but the diff does not "
             "touch the status or status_fields: is that a second change? A new status field is a "
             "new minor API version (ADR 0013)."},
]
