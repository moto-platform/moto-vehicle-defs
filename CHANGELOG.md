# Changelog

All notable changes to moto-vehicle-defs. Semantic versioning: a new message/signal/DID is
MINOR, changing or removing one (ID, layout, scale, name) is MAJOR, comment-only is PATCH.
Consumers pin the submodule to a tag; nothing updates automatically.

## Unreleased (planned v0.1.0 — not tagged yet)

### Added
- `uds/vehicle_cl250.yaml`: verified CL250 engine ECU facts (D-019, D-023): addressing
  (29-bit primary, 11-bit fallback), D-020 service allow-list, session/tester-present and
  timeout/backoff timing, DIDs `0xF40C` `0xF40D` `0xF411` `0xF405` `0xF442`, NRC names.
- `dbc/platform.dbc` draft: nodes with NodeId; `LeanEstimate` (0x020) and
  `CorneringParamEstimate` (0x021) from the rt-core EKF; `VehicleSpeed` (0x030,
  E2E, consumed by safety-node); heartbeats 0x081-0x085; `VehiclePowertrain` (0x110,
  rt-core republish of the polled DIDs, D-021).
- `dbc/cl250.dbc` skeleton (no passive frames known, Q-001).
- `vss/overlay.vspec`: dbc2vss mappings to standard COVESA VSS v6.1 paths only.
- `uds/dids.yaml` skeleton for platform nodes' own DIDs.
- `tools/codegen` (`make gen`/`make check`): source checks (ID classes, E2E layout and
  unique DataIDs, D-020 allow-list, overlay mappings); per-node C (cantools pack/unpack,
  `platform_meta.h`, E2E library, CL250 DID table with the D-020/D-021 frame and
  request guards);
  `gen/python/moto_defs`; `gen/vss/vss.json`.
- E2E receiver re-arms (INITIAL) after a timeout, so a wrapped 4-bit counter or a
  resumed sender is never accepted on its first frame; status enums use 0 = NOT_AVAILABLE
  so an all-zero payload is never valid.
- `docs/legacy-telemetry-notes.md`.
