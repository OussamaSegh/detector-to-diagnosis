# CAPA-0003: Input values at the limits of their types

| Field | Value |
|---|---|
| Status | closed |
| Opened | 2026-10-25, by the software lead |
| Source | MDQ-PR-001 |
| Owner | software lead |
| Effectiveness check | soon |

## Problem

Fuzzing found two crashes.

## Investigation

The two problem reports were read.

## Root cause

Human error: the developer forgot to test large numbers.

## Correction

Both defects are fixed.

## Corrective action

Developers will be more careful with boundary values.

## Preventive action

Training on boundary-value testing.

## Verification of the actions

Done.

## Effectiveness check

Criterion: testing has improved.
Due: soon.
Result: no new problems so far.
