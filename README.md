# moto-vehicle-defs

Single source of truth for the signals of the [moto-platform](https://github.com/moto-platform) motorcycle platform (first vehicle: Honda CL250): the platform CAN message map, the CL250 diagnostic (UDS) data, the VSS mapping and the platform documentation. Every other repo consumes the generated code under `gen/` through a submodule pinned to a tag.

| Path | Content |
|---|---|
| `uds/vehicle_cl250.yaml` | CL250 engine ECU DIDs polled by the single vehicle-bus tester (verified, D-019) |
| `dbc/platform.dbc` | Platform bus (our nodes), incl. rt-core's republished vehicle signals |
| `dbc/cl250.dbc` | Vehicle-bus broadcast frames (skeleton, Q-001) |
| `vss/overlay.vspec` | dbc2vss mappings on top of COVESA VSS v6.1 |
| `uds/dids.yaml` | Platform nodes' own DIDs/DTCs/routines |
| `tools/codegen/` | Generator (Python, uv) |
| `gen/` | Generated output, committed; never edit by hand |
| `docs/` | Platform documentation (start at `docs/ARCHITECTURE.md`) |

## Build

Requires [uv](https://docs.astral.sh/uv/), git and gcc.

```bash
make gen     # validate sources and regenerate gen/ (commit the result)
make check   # CI: regenerate and fail if gen/ differs from the commit
make test    # codegen tests, incl. compiling and running the generated C on the host
make lint    # ruff
```

`make gen` clones COVESA VSS `v6.1` once into `.cache/` for the VSS export.

## Consumers

MCU repos include only `external/moto-vehicle-defs/gen/c/<node>/` (`rt_core`, `safety`, `io`, `conn`, `hil_sim`); host tools use `gen/python/moto_defs` or load the DBC with cantools; Kuksa uses `gen/vss/vss.json`. Signal changes follow the `/signal-change` workflow and `CHANGELOG.md`.

## License

To be decided.
