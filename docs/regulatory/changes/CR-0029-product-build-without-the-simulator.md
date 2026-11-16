# CR-0029: A product build without the simulator

| Field | Value |
|---|---|
| Status | implemented |
| Requested | 2026-11-15, by the software lead |
| Source | problem report MDQ-PR-009; hazard H-06; roadmap 2.0.0, theme B |
| Decision | approved, 2026-11-15, under the software lead's standing delegation of 2026-11-15 |
| Commits | 0fd885b (the product build) and the commit that records this |

## Description

The synthetic source, the detector simulator and the simulated front-end boards are part of the
shipped server today: a configuration with `"source": {"type": "synthetic"}` or a hardware
description with `"backend": "simulated"` makes `minidaq_server` invent data. The change makes
the product build leave all of them out:

1. **A build option.** `MINIDAQ_WITH_SIMULATOR` (default `ON`). With it `OFF`, `src/sim/` and
   `src/hw/fake_board.cpp` are not compiled into any library the server links; they form the
   library `minidaq_sim`, which only the development programs (`minidaq_sim`, `minidaq_send`,
   `minidaq_latency`), the tests, the benchmarks and the exercises link.
2. **A refusal, not a missing feature.** A server built without the simulator refuses
   `configure` with source type `synthetic` and a hardware description with backend `simulated`
   with a message that names the reason ("this is a product build: the simulator is not part
   of it"), before anything starts: the synthetic source at `configure`, the simulated boards
   at start-up. The `hello` reply says whether the build has the simulator (`"simulator"`).
3. **A `product` preset.** The hardened preset with the simulator, the tests, the benchmarks
   and the exercises off: what `tools/repro_check.sh` and `tools/release_bundle.py` build and
   package. The `hardened` preset keeps the simulator, so that the tests and the soak run on
   the same compiler, flags and hardening as the product.
4. **CI.** A job builds the `product` preset and runs the product's system tests: those that
   feed the server over UDP (`minidaq_send` from a development build) and the new test that
   the product refuses the simulator. A test checks that the product server contains no symbol
   of the `minidaq::sim` namespace and no `FakeBoard`.

## Reason

Hazard H-06: a configuration at the scanner that selects the synthetic source stores invented
data as a patient's scan. The control today is information only (RC-15: the metadata says
`simulated`), and its residual risk names this change as the remaining reduction. A control by
design ranks above a control by information (ISO 14971, 7.1): what the product does not contain
it cannot be configured to do. Without the change, the safety of the data rests on whoever
writes the configuration and on every reader checking the metadata.

## Impact analysis

### Requirements

Added: SRS-PLT-012 (a product build contains no simulator and refuses a configuration that
asks for one) and a change to SRS-OUT-012's rationale. The source and hardware requirements of
the simulator (SRS-SIM, SRS-HW for simulated boards) stay, as requirements of the development
build. Verification repeated: SRS-OUT-012, the system tests over UDP, the reproducible build.

### Software items and safety class

Item `sim` leaves the product: it is class B today only because it runs in the server
(`docs/architecture/software-items.json`, MDQ-PR-009), and becomes a development item that is
not shipped. Items `service` and `config` gain the refusal; `hw` loses `FakeBoard` from the
product. No class of a shipped item changes.

### Risk

H-06 gains RC-52 (type: inherent safety by design): the product build has no simulator and
refuses a configuration that asks for one, verified by test. Probability after: P1. The new
risk is a product build that cannot be tested like the development build: the tests of the
hardened build cover the same code except the refusal, and the product's own system tests run
in CI on every change.

### SOUP

None.

### Interfaces and data formats

Breaking for a site that ran the shipped server with the synthetic source: it must use a
development build. The configuration schema is unchanged by this request (CR-0030 changes it);
the source type `synthetic` stays valid in the schema and is refused by the product.

### Documents

SRS, hazards file (H-06), architecture (the items of the product), SDP section 8 (the product
preset in the release), the tool list (TL-01's builds), and the release package description.

### Regulatory

The intended use does not change. The change removes a function the intended use never
included; it reduces a risk. Not a significant change.

## Verification

Tests: `Product.test_the_product_refuses_the_synthetic_source_when_it_is_configured`,
`Product.test_the_product_refuses_simulated_boards_at_start_up`,
`Product.test_the_product_server_contains_no_code_of_the_simulator`; and the checks below.

- Unit tests of the refusal in both builds (the development build accepts, a service built
  with `MINIDAQ_WITH_SIMULATOR=OFF` refuses).
- The product's system tests in CI and in the release checks.
- A symbol check of the product server (`nm -C`: no `minidaq::sim::`, no `FakeBoard`).
- The reproducible build of the product preset at the next release.

## Decision

Approved on 2026-11-15 by the coordinator under the software lead's standing delegation of
2026-11-15, as proposed. The one change of behaviour, the shipped server refusing the synthetic
source and simulated boards, is recorded as a breaking change in the CHANGELOG and the release
notes of 2.0.0.
