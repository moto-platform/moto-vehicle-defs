# moto-vehicle-defs

Single source of truth for signals in [moto-platform](https://github.com/moto-platform): CAN message maps (DBC), the VSS overlay, UDS/DID definitions, and the code generated from them. Every other platform repo consumes this one as the `external/moto-vehicle-defs` submodule pinned to a tag; none defines its own signals. Platform documentation lives in [`docs/`](docs/README.md).

| Path | Content |
|---|---|
| `uds/vehicle_cl250.yaml` | Honda CL250 ECU DIDs polled over UDS (addressing, formulas, poll rates, timing; verified, D-019) |
| `dbc/platform.dbc` | Platform CAN bus between our nodes (ID plan, E2E attributes) |
| `dbc/cl250.dbc` | CL250 passive broadcast frames (skeleton, Q-001) |
| `vss/overlay.vspec` | COVESA VSS 6.0 overlay + `dbc2vss` mappings for kuksa-can-provider |
| `uds/dids.yaml` | UDS servers of our platform nodes: addressing, timing, services, DIDs, DTCs (RT_CORE so far, D-040) |
| `uds/iso14229.yaml` | Generic ISO 14229-1 codes, generated as `uds_iso14229.h` (D-040) |
| `limits/platform_limits.yaml` | Shared cornering/speed limits and fallback values (provisional, D-029) |
| `tools/codegen/` | Generator and checks (Python, uv) |
| `gen/` | Generated output, committed — never edit by hand |

## Generated output

- `gen/c/<node>/` for `rt_core`, `safety`, `io`, `conn`, `hil_sim`: `platform.{h,c}` (cantools pack/unpack of only the node's messages), `moto_e2e.{h,c}` + `platform_e2e.{h,c}` (E2E, [`docs/e2e-profile.md`](docs/e2e-profile.md)), for rt_core/safety/hil_sim `platform_limits.h`, and for vehicle-bus nodes `vehicle_cl250.{h,c}` (DID table, response parser, D-020 request/frame allow-list that every vehicle-bus transmission must pass). C99, no heap. A firmware includes only its own node directory.
- `gen/python/moto_defs/`: IDs, cycle times, DataIDs, CL250 constants, E2E reference.
- `gen/vss/vss_dbc.json`: VSS JSON with `dbc2vss` for Kuksa / kuksa-can-provider.

## Commands

Requires [uv](https://docs.astral.sh/uv/) and a C compiler (for the C tests).

```bash
make check   # strict DBC parse + consistency checks + ruff + pytest
make gen     # regenerate gen/ (downloads the pinned COVESA VSS release once)
make drift   # regenerate and fail if gen/ changed (CI)
```

Changing a signal: follow the `/signal-change` skill, add a `CHANGELOG.md` line, `make gen`, commit. Tags are cut deliberately; consumers bump their submodule deliberately.

## License

MIT, see `LICENSE` (D-036).
