# Change brief: acquisition PC from Ubuntu 22.04 to Ubuntu 24.04

## Change

The acquisition PC's operating system moves from Ubuntu 22.04 LTS to 24.04 LTS, because
22.04's standard support ends in 2027. The DAQ software itself does not change.

## Software items affected

None. Only the operating system changes, and the DAQ binaries are rebuilt unchanged.

## Risk

TODO

## Verification

The unit tests pass on the new image, so there is no need to retest the scanner.

## EU

No regulatory impact: the device software is unchanged.

## Documents to update

The installation guide.

## Decision

Go ahead.
