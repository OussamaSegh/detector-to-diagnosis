# 0005. A table-driven acquisition state machine

Date: 2026-10-24
Status: Accepted

## Context

An acquisition moves through a small number of states, and the dangerous bugs are commands
accepted in the wrong one: reconfiguring a running acquisition, starting twice, resetting
away a fault before anyone has seen it. Commands come from several clients and from the
system itself (a run that ends, a detector that fails), on different threads. The set of
allowed transitions is a design decision that reviewers, testers and the risk analysis
(Chapter 15) must be able to read without reading the code.

## Options

1. **Boolean flags and `if` statements in each command** (`running_`, `configured_`, ...).
   Quick to start; the allowed combinations are implicit and spread across functions, and
   impossible combinations (running but not configured) are representable.
2. **The State pattern** (one class per state with virtual handlers). Each state's behavior
   is local, but the complete transition set is again spread over many classes.
3. **A library** such as Boost.MSM or Boost.SML. Expressive, compile-time checked tables;
   adds SOUP and template-heavy code for a 5-state machine.
4. **An explicit enum of states, an enum of events, and one `constexpr` transition table**,
   with a small thread-safe wrapper that applies events and notifies a listener.

## Decision

Option 4. States are idle, configured, running, stopping and fault; events are configure,
start, stop, drained, error and reset. The table in `acquisition_state.hpp` is the single
source of truth: `next_state(state, event)` looks it up, and any pair not in the table is an
illegal transition that changes nothing and is reported as "cannot EVENT in state STATE".
`docs/architecture/acquisition-states.json` is a machine-readable copy for diagrams and
documents, and a unit test fails if it differs from the code. Every transition is written to
the audit trail by the listener, in order.

Two rules in the table are deliberate: `reset` is not allowed while running (stop first, so
the data in flight is drained and counted), and `fault` can only be left through `reset`, so
a fault is always acknowledged by someone.

## Consequences

### Positive

- The whole behavior fits on one screen and in one diagram; tests can enumerate all 30
  state/event pairs.
- Illegal commands are harmless by construction.
- Adding a state or event is a visible table change that review and the risk analysis see.

### Negative

- Behavior attached to a transition (starting threads, opening files) lives in the service,
  not in the table, so the table alone does not show everything that happens.
- The machine has no hierarchy or history; if later requirements need sub-states (for
  example calibration modes) we must revisit this decision.
