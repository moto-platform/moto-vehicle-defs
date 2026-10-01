# Changelog

All notable changes to moto-vehicle-defs. Semver (see CLAUDE.md): new message/signal = MINOR, changed or removed message/signal/ID/layout/scale = MAJOR, comment-only = PATCH. Consumers pin a tag; nothing updates automatically.

## [Unreleased]

### Added
- codegen: D-043 no-starvation check (ISSUES E-4, safety-reviewer m3 on defs#13). `yaml_checks.did_sample_gap_bounds()` models the rt-core poller as non-preemptive fixed-priority scheduling (priority, then table order; one request in flight, each holding the slot for `assumed_round_trip_ms`) and bounds every DID's worst-case sample gap: poll period + one blocking round trip + higher-priority interference + its own round trip. `make check` fails if a bound exceeds the DID's `stale_after_ms`. Today's table at 20 ms: 0xF40D 140/300, 0xF40C 110/150, 0xF411 300/600, 0xF405 960/2400, 0xF442 1000/2400 ms. `timing.assumed_round_trip_ms` is now required (without it the polling budget and this check were skipped silently). gen/ is unchanged.

- codegen: D-050/D-051 fault-mode check (ISSUES E-7 (3)). `yaml_checks.did_fault_gap_bounds()` bounds every DID's request gap while a high-priority DID is faulty (extended by D-052 below): that DID competes in the normal class at its table position, holds the slot for at most `response_timeout_base_ms` per read, its reads are at least its period + the base timeout apart, and at most `max_consecutive_timeouts` - 1 faulty reads follow its first failing attempt before the skip. `make check` fails if a bound exceeds the DID's `stale_after_ms`. Today's table, 0xF40D faulty: 0xF40C 150/150 (it must stay the first normal DID in table order; a normal DID ahead of it gives 170), 0xF411 380/600, 0xF405 1640/2400, 0xF442 1720/2400 ms. The sample age adds one round trip on top (D-050 item 2). Not covered (D-051, ISSUES E-8): a faulty normal DID, and an ECU that alternates timeouts with answers just inside the base timeout (each answer resets the skip count). gen/ is unchanged.

- codegen: D-052 poll period rule (ISSUES E-8 (1)). `make check` fails if a DID's `poll_period_ms` is below `timing.response_timeout_base_ms`: a read answered within the base timeout without NRC 0x78 must end before its DID is due again, or a slow normal DID starves the later ones.

### Changed
- `uds/vehicle_cl250.yaml`: 0xF40C (ENGINE_SPEED) `poll_period_ms` 50 → 100 and `stale_after_ms` 150 → 300 (D-052, ISSUES E-8 (1)); now `poll_period_verified: false` with `legacy_poll_period_ms: 50`. gen/ changes: the RPM row of `vehicle_cl250_dids[]` (rt_core, conn, hil_sim) and the Python table. Consumers poll RPM at 10 Hz after their defs bump.
- codegen: the fault-mode check covers any one faulty DID, normal ones included (D-052, ISSUES E-8 (2)), and the chain that alternates timeouts with slow answers (ISSUES E-8 (3)): a faulty DID's reads are at least its period and its period + the base timeout apart in turn, and at most 2 × (`max_consecutive_timeouts` − 1) faulty reads follow its first failing attempt, since a slow answer no longer resets the skip count (rt-core, D-052). It is evaluated only when the period rule holds. Today's table: 0xF40C 240/300, 0xF40D 200/300, 0xF411 460/600, 0xF405 1380/2400, 0xF442 2040/2400 ms; the nominal D-043 bound gives 0xF40C 160/300.

### Fixed
- codegen: `vehicle_cl250.yaml` timing checks refuse YAML `true`/`false` (a Python `bool` is an `int` and passed as 1/0 ms): every `timing.*` value, `requests_in_flight`, each DID's `poll_period_ms` / `stale_after_ms` and `legacy_poll_period_ms` must be a positive integer that is not a bool (ISSUES E-6 n3). gen/ is unchanged.

## [0.3.1] — 2026-10-01

MISRA C:2012 gate on `gen/c` (ISSUES C-2), single-exit D-020 gate (ISSUES C-6) and runtime tests of the generated C (ISSUES C-7). Only generated source text and tests change: no API, signal, ID, layout, scale, `tester_policy` or D-020 golden-copy change, and no behaviour change, so this is a PATCH release.

### Added
- Runtime tests of the generated cantools C (ISSUES C-7, `tools/codegen/tests/test_cantools_c.py`): per node, pack/unpack/decode against cantools Python with boundary values and 10 000 random payloads per message, `*_init(NULL)`, every short size (rejected, nothing written), longer frames, `*_is_in_range()` at the raw limits, `*_encode()`, out-of-width members not leaking into neighbours, and pack/unpack scope = the DBC senders/receivers (safety-node's 0x020/0x022 decode included). A synthetic DBC test for `_MISRA_FIXUPS`. E2E BAD_ARGUMENT tests: NULL data/state, size < 2 and `max_delta` outside 1..14 leave the data and state untouched.

### Changed
- MISRA C:2012 is a blocking CI gate on `gen/c` (D-046 item 2, ISSUES C-2): `make misra` (cppcheck 2.22.0, canary, header-only files, `unix32`), deviation register `misra/README.md` (DEV-001..DEV-004).
- codegen: the D-020 gate in `vehicle_cl250.c` (`vehicle_cl250_find()`, `_decode()`, `_request_allowed()`, `_frame_allowed()`, `_parse_response()`) is single-exit, with `break`-terminated switch-clauses (ISSUES C-6). DEV-004 no longer covers `vehicle_cl250.c` and DEV-005 (16.1/16.3) is closed. Same behaviour: `tools/codegen/tests/test_gate_equivalence.py` compares it with the previous gate at `-O0` and `-O2` over every byte the request and frame gates read (all 2^24 frame prefixes × 12 sizes), every DID and every data value of the table's DIDs (synthetic 3/4-byte entries sampled). A test pins one `return` per gate function and the fail-closed `bool ok = false` default. A narrowed policy with `subfunctions: []` now emits `ok = false` only (it built with an unused variable before). Accepted and refused frames, `tester_policy` and the D-020 golden copy are unchanged; `find()` now always scans the whole 5-entry table and keeps the first match.
- codegen: `platform.c` gets `(void)memset`, braced `*_init()` NULL guards and widen-before-mask in `unpack_*_shift_*` (17.7, 15.6, 10.8); `moto_e2e_crc()` declares its loop variable in the `for`. Source text only: the `-O2` object code of every node is byte-identical. No API, ID, signal or `tester_policy` change.

## [0.3.0] — 2026-09-30

Layer 1 thresholds, rt-core speed rules and DID poll priority (ISSUES E-1, B-8 DBC part). Decisions D-041, D-043, D-048 (user, 2026-09-30). The 0x021 bit layout and scale are unchanged, but generated APIs change (see Breaking), so this is released as v0.3.0 (0.x: breaking changes bump the minor version).

### Added
- `limits/platform_limits.yaml`: `k_yellow` 0.6 and `k_red` 0.8 (provisional), the friction-utilisation thresholds of the Layer 1 cornering decision (D-041), generated as `PLATFORM_LIMIT_K_YELLOW` / `PLATFORM_LIMIT_K_RED` and in `moto_defs/limits.py`. codegen checks 0 < k_yellow < k_red < 1.
- `limits/platform_limits.yaml` → `scope`: which nodes' `platform_limits.h` carries each section (`SCOPE` in Python). codegen refuses SAFETY for the speed rules.
- `uds/vehicle_cl250.yaml`: `priority` per DID (`high` | `normal`, D-043); 0xF40D is `high`. Generated as `VEHICLE_CL250_PRIORITY_HIGH` (0u) / `_NORMAL` (1u) and `vehicle_cl250_did_t.priority` (C), and as `PRIORITIES` plus a 10th `DIDS` tuple field (Python). `tester_policy` and the D-020 gates are unchanged.
- codegen: `SAFETY_RX_ALLOWED` (EkfLean, EkfFrictionMass, HeartbeatRtCore): the DBC check refuses any other message with SAFETY as a receiver (D-041/D-042). `k_red` ≤ 0.8 until Q-022 (D-041 item 3).

### Breaking
- `dbc/platform.dbc` 0x021: `VEHICLE_SPEED` maximum 300 → 255 km/h, so the generated range check (`platform_vehicle_speed_vehicle_speed_is_in_range`) now refuses 255-300 km/h for every node. SAFETY is no longer a receiver, so `gen/c/safety` loses the VehicleSpeed pack/unpack and E2E functions.
- `gen/c/safety/platform_limits.h` no longer defines `PLATFORM_LIMIT_VEHICLE_SPEED_*`; `PLATFORM_LIMIT_VEHICLE_SPEED_MAX_AGE_MS` is 300 (was 400) for rt_core and hil_sim.
- `vehicle_cl250_did_t` gains `priority` after `length` (positional initialisers of the struct break; field access by name does not). Python `DIDS` tuples gain a 10th field.
- safety-node has no code yet; rt-core and conn read the table by field name only.

### Changed
- Speed rules re-scoped to rt-core (D-041 item 4): `vehicle_speed_max_age_ms` 400 → 300 ms (= `stale_after_ms` of 0xF40D; codegen checks poll period + assumed round trip < value ≤ `stale_after_ms`). The accel margin is now applied by rt-core to the speed in its lean estimate. The limits header text is rewritten: Q-002 was resolved by D-042.
- `dbc/platform.dbc` 0x021 `VehicleSpeed`: `VEHICLE_SPEED` range 0-300 → 0-255 km/h (the DID 0xF40D range; ID, layout, 0.01 scale and E2E unchanged), the 1 km/h source resolution is documented, and SAFETY is no longer a receiver (D-041). As a result `gen/c/safety` no longer contains the VehicleSpeed pack/unpack/E2E code or the speed limits; safety-node has no code that used them.
- `uds/vehicle_cl250.yaml`: the "Order = poll priority" comment is replaced by the D-043 priority rule; the C index comment now says "table order".

### Fixed
- `moto_defs.vehicle_cl250.decode()` raised `ValueError` on every call (it unpacked 10 fields from a 9-field tuple); now covered by a test.

## [0.2.0] — 2026-09-30

Ç3 UDS server contract and generated ISO 14229 codes. Decision D-040 (user, 2026-09-30); Q-021 resolved.

### Added
- `uds/iso14229.yaml`: generic ISO 14229-1 codes (SIDs 0x10/0x14/0x19/0x22/0x3E, sessions, 0x3E and 0x19 sub-functions, DTC status bits, NRCs, functional NRC suppression, P2/P2* units). Generated as `gen/c/<node>/uds_iso14229.h` for rt_core and hil_sim (full set) and conn (client subset: nothing outside the D-020 allow-list), and in `moto_defs/uds.py`. Replaces rt-core's temporary `uds_iso14229.h` (D-039 item 1).
- `uds/dids.yaml`: platform-bus ISO-TP parameters and the RT_CORE server: physical 0x710 → 0x718, functional 0x7DF, P2 50 ms / P2* 5000 ms / S3 5000 ms, services 0x10 (01/03), 0x3E, 0x22 (≤ 4 DIDs), 0x19 (01/02/0A), 0x14 (extended session only); DIDs 0xF186, 0xF189, 0xFD00 (vehicle-tester status), 0xFD01 (uptime), 0xFD10-0xFD14 (CL250 samples); DTCs U0100-00 (0xC10000) and U3000-00 (0xF00000). Generated as `gen/c/rt_core/platform_uds.{h,c}` (tables plus service/session/sub-function/functional-NRC checks).
- `uds/vehicle_cl250.yaml` → `addressing.functional_watch`: OBD functional request IDs 0x7DF and 0x18DB33F1, **watch-only** (Q-021): generated as `vehicle_cl250_functional_watch[]` and `FUNCTIONAL_WATCH_IDS`. `tester_policy` and the D-020 gates are unchanged.
- Fail-safe vehicle-tester status (safety review): 0xFD00 `FAULT = NOT_RUNNING`, `max_age_ms` 500 → `PLATFORM_UDS_VEHICLE_TESTER_STATUS_MAX_AGE_MS`; per-DID `PLATFORM_UDS_DID_<NAME>_LENGTH` macros. D-040 lists the preconditions for 0x27 and the Q-001 probe of the watch IDs.
- codegen checks: 0x7N0/0x7N8 from the NodeId, P2 < P2*, SAE J2012 code ↔ DTC value, DID ranges/lengths/bitfields, vehicle samples only on a node with the CL250 table, watch IDs watch-only and distinct; tests that the vehicle gate still refuses 0x14 and 0x10 02.

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
