# Changelog

All notable changes to moto-vehicle-defs. Semver (see CLAUDE.md): new message/signal = MINOR, changed or removed message/signal/ID/layout/scale = MAJOR, comment-only = PATCH. Consumers pin a tag; nothing updates automatically.

## [Unreleased]

## [0.1.0] — 2026-09-26

First definitions and tooling. Decisions: D-019..D-029 (D-024..D-027 user-confirmed 2026-09-26). Provisional values (D-029) are marked in the sources.

### Added
- `uds/vehicle_cl250.yaml`: CL250 ECU polling definition extracted from the legacy telemetry firmware (D-019, D-023): 29-bit addressing + unverified 11-bit fallback, five J1979 DIDs (`0xF40C`, `0xF40D`, `0xF411`, `0xF405`, `0xF442`) with formulas and poll periods, session/tester-present, timeouts, bus-off backoff, and the D-020 tester allow-list; every value carries `file:line` evidence.
- `dbc/platform.dbc`: nodes `RT_CORE SAFETY IO CONN LINUX HIL_SIM TESTER` (`NodeId`), attributes `GenMsgCycleTime`/`E2E_Protected`/`E2E_DataID`; E2E messages `EkfLean` 0x020, `VehicleSpeed` 0x021, `EkfFrictionMass` 0x022, heartbeats `0x081-0x085`; rt-core republish `VehicleEngine` 0x110 (RPM, battery, coolant, TPS + validity).
- `dbc/cl250.dbc`: skeleton only (Q-001).
- `vss/overlay.vspec`: dbc2vss mappings to standard COVESA VSS 6.0 paths (speed, engine speed, coolant, battery) and the first `Vehicle.Motorcycle.*` extensions (D-028): lean angle, friction coefficient, estimated mass (each + quality + state), throttle position, ECU presence.
- `uds/dids.yaml`: skeleton for platform-node DIDs.
- `limits/platform_limits.yaml`: provisional cornering/speed limits shared by rt-core and safety-node (D-029), generated into `platform_limits.h` and `moto_defs/limits.py`.
- Provisional poll periods: `0xF40D` 100 ms, `0xF411` 200 ms (legacy 800 ms kept as `legacy_poll_period_ms`), polling budget check with `assumed_round_trip_ms`; `LEAN_ANGLE_STATE` value 2 is RESERVED (no default lean angle); generated `platform_estimate_state_usable()`.
- `tools/codegen`: per-node C (`gen/c/{rt_core,safety,io,conn,hil_sim}`: cantools pack/unpack, E2E protect/check, CL250 DID table with `stale_after_ms`, D-020 payload allow-list `vehicle_cl250_request_allowed()`, raw-frame gate `vehicle_cl250_frame_allowed()` and response parser `vehicle_cl250_parse_response()`), Python constants (`gen/python/moto_defs`), VSS JSON (`gen/vss/vss_dbc.json`); ID-plan, E2E-layout, DataID, naming, evidence checks and a golden D-020 allow-list the YAML may narrow but never widen; pytest suite incl. C/Python cross-checks.
- `docs/e2e-profile.md`, `docs/legacy-telemetry-notes.md`.
- codegen rejects 29-bit diagnostic IDs (0x18DA/0x18DB) as `cl250.dbc` broadcast frames.
- `Makefile` (`gen`, `check`, `drift`) and GitHub Actions CI (strict parse, checks, lint, tests, gen drift).
