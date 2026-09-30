# Decision Record (ADR) and Open Questions

Format: brief. Each decision states **what**, **why**, and, where relevant, **consequence**. New decisions go at the bottom, with the next number. If a decision changes, the old one is not deleted — it is `~~struck through~~` and linked to the new one.

---

## Decisions

**D-001 — Authoritative document: hardware architecture** _(bus topology in hardware-architecture.md superseded by D-009/D-021/D-037; the Turkish docs moved by D-038)_ (2026-09-25, user)
`hardware-architecture.md` + `ARCHITECTURE.md` are authoritative. `tr/bitirme-projesi-kapsam.md` is partially outdated: the DUT is not the ESP32-S3 but the **STM32H7 (rt-core)**, the HIL simulator is not the ESP32-S3 but the **STM32F4**, and the Raspi 5 is in scope. The Ç1-Ç8 work packages remain valid, but Ç1's target is H7 FDCAN. Updating the scope document → Q-005.

**D-002 — GitHub org: `moto-platform`** (2026-09-25, user)
Repos currently live at `github.com/alihanesentas/*`. They will be transferred once the org is created (GitHub redirects the old URLs). `manifest.yaml` has been updated with the org URLs.

**D-003 — Definition distribution: submodule + per-node codegen** (2026-09-25, user-approved)
Consumer repos pin `external/moto-vehicle-defs` as a git submodule to a **tag**. `tools/codegen` (built on cantools `generate_c_source`) generates, for each node, C code containing only the messages that node sends/receives. The output is committed under `gen/` before tagging, so the firmware build doesn't depend on Python and the generated code can be reviewed. Why: DBC/VSS can't be parsed on the MCU (F103 has 20 KB RAM); the generated code is `const` and malloc-free.

**D-004 — VSS only on the Raspi and above; mapping in the official VSS overlay format** (2026-09-25, user-approved)
Eclipse **kuksa-can-provider** is used for CAN→VSS. Mapping is done through the `dbc2vss` keys in the VSS overlay. The made-up `vss/mappings.yaml` format from the old `can-dbc-conventions` skill is **not used**. Motorcycle-specific signals are kept small and consistent under `Vehicle.Motorcycle.*`; the user is asked before every new extension. The safety path is never wired into VSS.

**D-005 — E2E protection on safety-critical platform messages** (2026-09-25, user-approved)
AUTOSAR E2E Profile 1/2-like scheme: 4-bit alive counter + CRC8 (SAE J1850) + an untransmitted DataID. The receiver checks timeout/counter/CRC. Scope: platform CAN 0x010-0x08F. Code is generated via codegen. Why: lets the safety node detect "data is late/frozen/corrupted"; cost is 1-2 bytes/message.

**D-006 — AUTOSAR: concepts yes, software stack no** (2026-09-25, user-approved)
Classic AUTOSAR BSW (commercial automotive toolchain + MCAL + hundreds of KB of flash) and Adaptive AUTOSAR are not used. The layer mapping (features≈SWC, services≈BSW, hal≈MCAL) and E2E are adopted. ARXML output can be generated from the DBC with canmatrix in Phase 2 (for showcase purposes).

**D-007 — Build/toolchain** (2026-09-25, Claude proposal, user did not object)
- STM32: **CMake + STM32CubeMX (HAL) + arm-none-eabi-gcc**. CubeIDE/VS Code can be opened as the IDE. Why: headless build on the i7 CI runner (Ç6).
- ESP32-S3: ESP-IDF (`idf.py`).
- C unit tests: Unity (host-native, CMake/ctest). Static analysis: cppcheck + MISRA addon.
- Python: `uv` + `pyproject.toml` + `ruff` + `pytest`, src layout, Python 3.11+.

**D-008 — Resolving in-document contradictions** (2026-09-25, Claude — based on the firm decision in the architecture document's §2)
- `anomaly-safety-net/` lives on **rt-core (H7)**. The "ESP32-S3 (H7)" phrasing in §5b.9 is a leftover from before the H7 decision.
- Context-classification inference lives in **rt-core `context/`**. The "ESP32-S3" column in the §5b.0 table is a leftover from before the H7 decision.
- The blind-spot/io-node target chip is **STM32G0**. The STM32F103 in §5b.1 is a **prototype** using the board already on hand. Its overlap with F103's role in HIL → Q-003.

**D-009 — Two separate CAN buses: vehicle (single read-only tester, D-037) + platform (dedicated)** _(bullets on safety-node/Raspi tapping the vehicle bus superseded by D-021; "hardware listen-only" wording superseded by D-037)_ (2026-09-25, Claude architecture proposal — revise if the user objects)
The architecture document stated both that "only the main MCU writes to the vehicle bus" (§4) and that io-node/rt-core publish status onto the vehicle bus (§5b.1, §5b.2); this was a contradiction. Resolution: our nodes talk on their own **platform CAN** bus. The vehicle bus is hardware listen-only; the sole exception is rt-core's OBD/UDS read requests. Why: this removes the risks of OEM ID collisions, confusing the OEM ECU, and added bus load; the two buses are simulated separately in HIL. The platform bus is classic CAN at 500 kbps (F103/ESP32 TWAI don't support FD). Details in `ARCHITECTURE.md` §3-4.

**D-010 — moto-server language: Python** (2026-09-25, Claude)
The document said "Python/Go". Python (FastAPI) was chosen so it shares the same language and toolchain as hil-host, ml, mcp, and linux-node. Starting point: file + Python, or InfluxDB+Grafana (hardware-architecture.md §5b.8).

**D-011 — Language convention** (2026-09-25, user)
All project documentation, CLAUDE.md files, code, identifiers, comments, commit messages and READMEs are in English. Turkish originals are archived under `docs/tr/` (not maintained; moved to `docs/archive/tr/` by D-038). Exception: advisor-facing university documents (`tr/bitirme-projesi-kapsam.md`, `tr/bitirme-raporu-hoca-sunumu.md`) remain Turkish. Commits: Conventional Commits.

**D-012 — RTOS** (2026-09-25, Claude)
rt-core: FreeRTOS (CMSIS-RTOS2, CubeMX). safety-node and io-node: bare-metal super loop + timer interrupt (determinism, verifiability). HIL simulator: bare-metal or FreeRTOS, chosen when the repo is set up.

**D-013 — manifest ref** _(superseded: defs was tagged `v0.1.0` and the manifest pins tags, D-036)_ (2026-09-25, Claude)
`moto-vehicle-defs` is referenced as `main` in the manifest since it hasn't been tagged yet. The first release will be `v0.1.0` (`v1.0.0` once platform.dbc is stable).

**D-014 — Docs archive** _(path changed to `docs/archive/tr/` by D-038)_ (2026-09-25, Claude)
Turkish source docs moved to `docs/tr/`; English translations are authoritative.

**D-015 — Workspace repo `moto-workspace`** (2026-09-25, Claude; user asked to finish remaining setup) The workspace root is its own repo holding `manifest.yaml`, `setup.sh`, root `CLAUDE.md`, `STATUS.md` and the shared `.claude/` agents/skills. It git-ignores `/moto-*/`. Why: otherwise the shared Claude setup exists on one laptop only and cannot reach GitHub or cloud sessions.

~~**D-016 — Repo visibility: temporarily public**~~ (superseded by D-017) (2026-09-25, user) The planned default stays **private**, but all 12 repos in `moto-platform` are public for now (profile visibility, nothing sensitive at this stage). They can be switched back to private at any time with `gh repo edit moto-platform/<repo> --visibility private --accept-visibility-change-consequences`. No LICENSE yet, so the default is all rights reserved. The license decision is still pending (moto-mcp is intended to be open source). Before committing anything sensitive (real ride GPS data, keys, personal info), re-check visibility.

~~**D-017 — Repo visibility: private**~~ (superseded by D-033) (2026-09-25, user) All 12 repos are back to **private** (D-016 was reverted the same day). They will go public later by user decision, together with the license decision.

**D-018 — Shared Claude assets synced into each repo** (2026-09-25, Claude; user asked for it as the next task) Cloud sessions clone only the selected repo(s). So `moto-workspace` stays the source of truth for `PLATFORM-RULES.md`, `.claude/agents/` and `.claude/skills/`, and `scripts/sync_claude.py` copies the relevant subset into each repo's `.claude/`. Each repo's `CLAUDE.md` imports `@.claude/PLATFORM-RULES.md`. Copies carry a "do not edit" marker and are listed in `.claude/.synced`. Run `--check` to detect drift. Agents use relative doc locations (no absolute paths).

**D-019 — CL250 vehicle bus facts (verified on the real bike)** (2026-09-25, from `github.com/alihanesentas/HondaCl250_Telemetry`, whose CAN/UDS path was validated on the CL250)
- Diagnostic connector (DLC) CAN: **classic CAN, 500 kbps** (ESP32-S3 TWAI).
- ECU data is obtained by **polling**, not by passive broadcast: UDS `0x22 ReadDataByIdentifier`, 29-bit normal-fixed addressing request `0x18DA10F1` → response `0x18DAF110` (11-bit `0x7E0`/`0x7E8` also sent as a fallback).
- DIDs, OBD-mapped (`0xF4xx` = SAE J1979 PID), with J1979 scaling: `0xF40C` RPM = (A·256+B)/4 · `0xF40D` speed km/h = A · `0xF405` coolant °C = A−40 · `0xF411` TPS % = A·100/255 · `0xF442` battery V = (A·256+B)/1000.
- Session handling: `0x10 0x03` (extended session, retried until a positive `0x50`), and `0x3E 0x80` tester-present every 1000 ms.
- Still unknown: whether any passive broadcast traffic exists on this bus (Q-001 remains open only for that part).
Consequences: CL250 signals are defined as **vehicle DIDs in `uds/`** (not as broadcast messages in `cl250.dbc`). The allowed vehicle-bus services must include `0x10` (sub-functions 0x01/0x03 only) and `0x3E` → Q-011.

**D-020 — Vehicle-bus service allow-list** (2026-09-25, user; resolves Q-011) rt-core may send only `0x10` (sub-function 0x01 default / 0x03 extended), `0x3E` tester-present, `0x22`, `0x19`, and OBD `0x01/0x09` to the vehicle. Forbidden: `0x10 0x02` (programming), `0x11` ECU reset, `0x14` clear DTC, `0x27`, `0x2E`, `0x2F`, `0x31`, `0x34`, `0x36`, `0x37`. Why: the verified read path needs an extended session and tester-present (D-019); nothing that changes ECU state is allowed.

**D-021 — rt-core is the single vehicle-bus tester and republishes vehicle signals** (2026-09-25, user; resolves Q-012; supersedes two D-009 bullets) Poll-based ECU data allows only one tester. rt-core polls the DIDs in `uds/vehicle_cl250.yaml` and republishes decoded values on the platform bus. Vehicle speed also goes to safety-node, so it is E2E-protected in the safety range. The Raspi reads vehicle signals from the platform bus (kuksa-can-provider with `platform.dbc`) and may tap the vehicle bus listen-only for raw logs. safety-node no longer connects to the vehicle bus. Accepted cost: safety-node depends on rt-core for speed, which raises the priority of Q-002.

**D-022 — Legacy telemetry repo = read-only reference; mobile = Flutter** (2026-09-25, user; resolves Q-007, partly Q-013) `HondaCl250_Telemetry` was transferred to `moto-platform` (private) and is to be archived as a read-only reference. Its knowledge (DIDs, timing, pitfalls) is extracted so nothing is rediscovered. Whether each component is ported or rewritten follows a standards/scope analysis (Q-013 remainder). `moto-mobile` uses Flutter (the legacy Flutter app is its starting point if the analysis says it is worth porting).

**D-023 — Legacy telemetry: hybrid port/extract/rewrite** (2026-09-25, Claude after a component analysis; the user asked for whichever path is most effective; resolves Q-013)
- **EXTRACT → moto-vehicle-defs:** DID table + formulas + poll periods (RPM 50 ms, others 800 ms), addressing, session/tester-present timing (0x10 0x03 retried every 2 s until 0x50; 0x3E 0x80 every 1 s), UDS timeouts (100 ms base, doubling on NRC 0x78 up to 2 s; 5 consecutive timeouts → 5 s DID skip), ECU-absent 3 s, bus-off backoff 1→30 s, the NRC table, the ISO-TP first-frame pitfall, and the pin map. Goes into `uds/vehicle_cl250.yaml` + `docs/legacy-telemetry-notes.md`.
- **PORT → moto-connectivity-node** (temporary telemetry home): HondaCANModule + UDS state machine, `ICanBus`/`TwaiCanBus`, MockCANModule, BLEServerModule + packet schema, NextionModule, SerialLogger, the native test pattern + CI. Toolchain: **PlatformIO with Arduino as an ESP-IDF component** (`framework = arduino, espidf`), which keeps the working code and still allows ESP-SR (refines D-007 for this repo). Hand-written DIDs are replaced by generated `gen/c/conn/` once codegen exists.
- **REWRITE:** WiFiServerModule (Arduino `String` → static buffers), and later in moto-rt-core (C): UDS client with full multi-frame ISO-TP plus the SystemState/IModule health/staleness pattern on FreeRTOS.
- **PORT → moto-mobile:** `mobile_app/flutter_app` as the initial skeleton.
- **DROP:** the web PWA (`mobile_app/*.html/js/css/py`), and the complementary-filter lean angle (known to be wrong; replaced by rt-core EKF).
- **Single tester:** until rt-core exists, connectivity-node is the temporary sole poller. When rt-core starts polling, connectivity-node's poller must be disabled (never two testers, D-021).
- Nextion is in scope (hardware-architecture §5b.4: target is UART to rt-core). The connectivity-node driver is temporary.

**D-024 — VSS base: COVESA VSS 6.0 via pinned release files** (2026-09-25, Claude proposal; user-confirmed 2026-09-26)
`gen/vss/vss_dbc.json` = VSS 6.0 release (`vss.yaml`, `units.yaml`, `quantities.yaml`, sha256-pinned in `gen_vss.py`) + `vss/overlay.vspec`, exported with vss-tools **6.0** (6.1 rejects the 6.0 `units.yaml` with a duplicate-unit error). Why: 6.0 is the newest release kuksa-can-provider ships a mapping for (`mapping/vss_6.0`). Consequences: VSS 6 has no `Vehicle.OBD` branch and uses `CombustionEngine.EngineCoolant.Temperature`; Kuksa Databroker on linux-node must load the same JSON; a VSS upgrade is a deliberate MAJOR/MINOR change here.

**D-025 — platform.dbc v0.1 message set** (2026-09-25, Claude proposal; user-confirmed 2026-09-26)
Safety range (E2E): `EkfLean` 0x020 / 20 ms, `VehicleSpeed` 0x021 / 50 ms, `EkfFrictionMass` 0x022 / 100 ms, all RT_CORE → SAFETY, LINUX (speed also CONN). Each EKF estimate carries a quality % and a 2-bit state (ESTIMATED / CLAMPED / DEFAULT fallback / INVALID, per hardware-architecture §5b.2); `VehicleSpeed` carries VALID + AGE (ms since the ECU sample) because the ECU speed DID is polled every 800 ms. Heartbeats 0x081-0x085 / 100 ms (E2E): NODE_MODE, ERROR_COUNT, UPTIME. State range: `VehicleEngine` 0x110 / 50 ms (RPM, battery, coolant, TPS with the J1979 source scaling, per-signal VALID + ECU_PRESENT). `E2E_DataID` convention `0x1000 + CAN ID`; `NodeId` is a BU_ attribute. CoG height and a cornering-warning output message are not defined yet (later MINOR). `uds/vehicle_cl250.yaml` gets a platform-chosen `stale_after_ms` = 3 × poll period per DID (not a legacy value). rt-core sends `*_STATE = INVALID`, `QUALITY = 0` until the EKF has converged.

**D-026 — E2E profile details** (2026-09-25, Claude proposal refining D-005; user-confirmed 2026-09-26)
CRC-8/SAE-J1850 (0x1D, init 0xFF, xorout 0xFF) over DataID low, DataID high, bytes 1..n-1; 4-bit counter 0..15; receiver max delta counter 1 (a single lost frame invalidates that cycle); timeout 3 × cycle, enforced both by `check_timeout()` and inside `check()` (a frame after a gap longer than the timeout resyncs as `INITIAL`, so a stalled sender never resumes as `OK`); `INITIAL` is not usable. Spec: `docs/e2e-profile.md`. Generated C is cross-checked against the Python reference.

**D-027 — codegen targets and vehicle-bus guard** (2026-09-25, Claude proposal refining D-003; user-confirmed 2026-09-26)
C is generated for RT_CORE, SAFETY, IO, CONN, HIL_SIM (`gen/c/<node>/`, cantools `use_float`, C99, no heap); HIL_SIM gets every message (restbus impersonation). LINUX and TESTER use the DBC/VSS at runtime and get Python/VSS only. The CL250 DID table goes to rt_core, conn (temporary tester, D-023) and hil_sim (ECU simulator), together with generated `vehicle_cl250_request_allowed()` (payload) and `vehicle_cl250_frame_allowed()` (raw ISO-TP Single Frame only) implementing D-020, which every vehicle-bus transmission must pass, and `vehicle_cl250_parse_response()` (checks SID 0x62 + DID echo). codegen holds a golden copy of the D-020 allow-list: the YAML policy may narrow it but never widen it (safety-reviewer finding).

**D-028 — First `Vehicle.Motorcycle.*` VSS extensions** (2026-09-25, user: "add as many as you can, we will revisit"; partly resolves Q-016)
Added to `vss/overlay.vspec` (whitelisted in `gen_vss.APPROVED_EXTENSIONS`): `LeanAngle`, `FrictionCoefficient`, `EstimatedMass`, each with `...Quality` (uint8 %) and `...State` (string ESTIMATED/CLAMPED/DEFAULT/INVALID); `ThrottlePosition` (throttle valve %, since VSS 6 has no `Vehicle.OBD` and `Chassis.Accelerator.PedalPosition` is driver demand); `IsEcuPresent`. For display, logging, MCP and ML only; safety decisions keep reading platform CAN. Not mapped yet: heartbeats (same signal names in five messages; kuksa-can-provider maps by name, so they need unique names first) and the `*_VALID` bits. The set is provisional and will be revisited.

**D-029 — Provisional base values until the measurement system exists** (2026-09-25, user: "put the basic values that can be changed later; measurements come from a separate test device + server"; provisional answers to Q-014/Q-015; safety-reviewer findings applied)
- Poll periods: speed `0xF40D` 800 → **100 ms**, TPS `0xF411` 800 → **200 ms** (not a safety input), both `poll_period_verified: false` with `legacy_poll_period_ms: 800`; RPM 50 ms, coolant/battery 800 ms. `stale_after_ms` = 3 × poll period. A budget check requires sum(`assumed_round_trip_ms` / period) ≤ 0.8, with `assumed_round_trip_ms: 20` (provisional).
- `limits/platform_limits.yaml` (new; generated into `platform_limits.h` for rt_core/safety/hil_sim and `moto_defs/limits.py`):
  - DEFAULT µ **0.5**, clamp **0.1-1.2**, applied by both rt-core and safety-node. 1.2 is the ceiling ML may never raise.
  - µ rule: ESTIMATED/CLAMPED → clamp; DEFAULT → max(0.1, min(received, 0.5)); INVALID/RESERVED/unknown → the received value is ignored. The result is always finite.
  - **No default lean angle**: rt-core sends INVALID, and `LEAN_ANGLE_STATE` value 2 becomes RESERVED. Generated `platform_estimate_state_usable()` accepts only ESTIMATED/CLAMPED.
  - DEFAULT total mass **252 kg** (172 kg wet + 80 kg rider). Mass is not a Layer 1 cornering input; heavier is the conservative side elsewhere.
  - Speed: safety-node uses it only if VALID, E2E OK and effective age (AGE + time since the frame arrived) ≤ **400 ms**. It adds age × **5 m/s²** as an acceleration margin.
- Not decided here: what safety-node does when a value or the whole frame is not usable (Q-002 stays open). If it keeps computing, it uses these defaults.
- Every value carries `status: provisional` and a rule. Changing one is a `/signal-change` + safety-reviewer, and it is revisited with measured data. Why: consumers need concrete numbers now, both sides must use the same ones, and the conservative side is always chosen (hardware-architecture §5b.2).
**D-030 — Temporary tester safeguards and private-submodule CI** (2026-09-26, Claude proposal from the connectivity-node realignment and its safety review — pending user confirmation)
- connectivity-node, the temporary sole tester (D-023), gains four safeguards:
  - A foreign-tester latch: any frame received on the ECU request IDs stops the poller and the TWAI driver until reboot (D-021).
  - A latch-off after 5 bus-off events (local constant for now; candidate for `uds/vehicle_cl250.yaml`).
  - A cap on NRC 0x78 extensions at `response_timeout_max_ms` total, and only NRCs for 0x22 can resolve the pending read.
  - A poller-off build (`CONN_VEHICLE_TESTER=0`, env `esp32-s3-devkitc-1-no-tester`) that never installs the TWAI driver and holds CAN TX recessive.
- Generic ISO 14229/11898 protocol constants (SIDs, NRCs, max 11-bit ID) may live in a consumer's own header. Vehicle IDs, DIDs, formulas and timings still come only from `gen/`.
- CI for private submodules:
  - Check out the repo with the default token, then fetch `external/moto-vehicle-defs` with the `MOTO_DEFS_TOKEN` secret (Contents: read on moto-vehicle-defs only). Never vendor the defs.
  - moto-mobile verifies its BLE schema copy against moto-connectivity-node with an optional `MOTO_CONN_READ_TOKEN`.

**D-031 — CI access to the private defs submodule (Free plan)** (2026-09-27, Claude, verified in moto-connectivity-node CI; refines D-030)
- Org secrets are not passed to private repos on the Free plan. Each consumer repo gets a **repository** secret `MOTO_DEFS_TOKEN`.
- `actions/checkout` must use `persist-credentials: false`. Otherwise its persisted GITHUB_TOKEN (an included credentials config) overrides the URL credentials, and the defs clone fails with 403 "Write access to repository not granted".
- Fine-grained PATs could not be granted access to the org (no org policy option visible, no approval request appeared), and deploy keys are disabled in the org. So the current token is a **classic PAT with `repo` scope, 90-day expiry (~2026-12-26)**. Accepted trade-off: broader than read-only; it lives only in private-repo secrets and is masked in logs. Move to a read-only deploy key or GitHub App once the org setting is found.


**D-032 — BLE telemetry v3, raw IMU stream and the session upload path** (2026-09-27, Claude proposal from the data-pipeline task; user-confirmed 2026-09-28)
- BLE layouts stay single-sourced in `moto-connectivity-node/docs/ble_telemetry_packet_schema.json`:
  - **Telemetry v3** (37 B): node clock `deviceTimeMs`, per-signal ages (65535 = never received; valid bits from the generated `stale_after_ms`, D-029), and CAN/tester health (TWAI state, TEC/REC, bus-off count, unanswered DIDs, D-030 latch flags).
  - v2 (16 B) stays as the fallback when the negotiated MTU cannot carry v3. Nothing is truncated.
  - Lean fields are deprecated, do not use them for analysis (D-023).
  - Fields carry `defsSignal` + `scale`, so decoders map them to `gen/python` DIDs without hand tables.
- **Raw IMU for data collection:**
  - connectivity-node samples an MPU-6050-compatible IMU (I2C on GPIO1/2, the legacy wiring) at 100 Hz, ±8 g / ±500 dps (4096 LSB/g, 65.5 LSB/(deg/s)).
  - It sends blocks of up to 10 samples at 10 Hz on a second characteristic. Each block has `deviceTimeMs`, `seq` and a tick index for exact loss counting.
  - Timer-driven task on core 0, static ring; the CAN poller never waits for it.
  - Offline analysis only: not a vehicle signal, not a safety input, not on the platform bus, no lean estimation (that stays in the rt-core EKF).
  - The part is provisional: the procurement list names MPU9250/LSM6DSO, and any part must deliver the schema scale.
- **Session files and upload:**
  - moto-mobile writes `meta.json`, `telemetry.csv` (v3 columns appended to the v2 ones, `raw_hex` authoritative), `events.csv` (including CAN health / MTU / IMU gap events), `summary.json` and `imu.csv`. Format: `moto-mobile/docs/session-format.md`.
  - The app uploads a session zip to moto-server `POST /sessions` (Bearer token, size limit, idempotent per `session_id`; recording and sharing work without a server).
- **moto-server v0:**
  - Re-decodes every row from `raw_hex` / raw IMU counts with the schema JSON.
  - Writes a validation report (JSON + text), Parquet with units in column names and `session_id` in every row, and a SQLite index under `$MOTO_DATA_DIR/sessions/<id>/{raw,parquet,report.json}`. MDF4 is an interface stub for now.
  - It keeps a verbatim copy of the BLE schema with a drift test, the same pattern as moto-mobile: a build-time check, not a runtime dependency on connectivity-node.
- Why: the phase0 plan (§3) needs timestamped CAN + 100 Hz IMU with loss accounting before any model work. The schema stays where the producer lives until Q-017 is decided.

**D-033 — Repo visibility: public** (2026-09-27, user; supersedes D-017) The 12 platform repos are public so the org secret `MOTO_DEFS_TOKEN` works on the Free plan, where org secrets only reach public repos. The full git history of all 12 was scanned for tokens, keys, passwords and credential files before the switch: clean. The archived `HondaCl250_Telemetry` stays private. Consequences: the defs submodule can be cloned anonymously, so the token is now optional for CI (the CI scripts still require it until simplified). ~~No LICENSE yet, so the default is all rights reserved; the license decision is still open.~~ (license: MIT, D-036) Actions minutes are free for public repos. Never commit real ride GPS data, keys or personal data (check before every data-related PR).

**D-034 — moto-rt-core skeleton, host platform layer and ISO-TP scope** (2026-09-28, Claude proposal from rt-core#1; user-confirmed 2026-09-28, the user added the host layer)
- Host-first, before the H7 board is chosen (Q-019):
  - Pure logic is built as `moto_rtcore_logic`. Presets: `host-tests` (Unity + ctest, ASan/UBSan) and `target-m7-debug/-release` (arm-none-eabi, `-mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard`, valid for H743 and H723).
  - No CubeMX project, startup code or linker script until the board is decided. The board choice (H743 vs H723) is still open.
  - defs is pulled as a plain public submodule (D-033), without a token.
- **Host platform layer (user):** rt-core also runs on the PC as a host program (SIL), not only as host unit tests. A host port of `hal/` provides:
  - CAN: Linux SocketCAN `vcan`, or an in-process virtual bus on macOS
  - the timebase
  - logging
  The same `services/` and `features/` code runs unchanged on the host and on the H7. This is also what the HIL live-model mode talks to before hardware exists (D-035).
- ISO-TP core (Ç2) scope, ISO 15765-2:2016:
  - In scope: classic CAN 8-byte frames with normal / normal-fixed addressing; 12-bit FF_DL (up to 4095 B); BS; STmin; N_Bs/N_Cr (ISO default 1000 ms, configurable per link); N_WFTmax; FC.OVFLW; optional padding; full duplex per link.
  - Out of scope for now: CAN FD, the 32-bit FF_DL escape, extended/mixed addressing, sending FC.WAIT, N_As/N_Ar (glue).
  - STmin below 1 ms is rounded up to 1 ms (ms timebase); reserved STmin values count as 127 ms.
  - Protocol constants live in the core. Per-link values (padding byte, BS/STmin, timeouts) come from the caller; vehicle values come from `gen/`.
- Static analysis: cppcheck warning/portability/performance is blocking. Style and the MISRA C:2012 addon only report for now. Baseline on rt-core#1: advisory rules only, 15.5 ×28, 8.7 ×1 and 15.7 ×1.

**D-035 — HIL realism: two separate modes** (2026-09-28, user; resolves the realism part of Q-009) moto-hil-bench offers two modes, selected per scenario:
- (a) **Log replay:** it replays recorded CAN/session logs (connectivity sessions, later rt-core logs) with their original timing, plus fault injection on top.
- (b) **Live vehicle model:** a simulated CL250 ECU and vehicle dynamics answer the node under test in closed loop.
Both modes share the scenario format and the evaluation/report. Before hardware exists, the node under test is rt-core's host build (D-034). The first target test function is still open (Q-009).

**D-036 — License and versioning** (2026-09-28, the user delegated the choice to Claude)
- **License: MIT** for all 12 repos (`LICENSE`, "Copyright (c) 2026 The moto-platform authors").
  - It is permissive and short, fits moto-mcp as open source, and is compatible with the dependencies: Unity/FreeRTOS MIT, STM32 HAL BSD-3, ESP-IDF Apache-2.0, Flutter BSD, cantools MIT, vss-tools MPL-2.0 as a tool.
  - Check the university's thesis IP rules before the first public release. The license can still be changed while there are no outside contributors.
- **Versions:** semantic versioning in every code repo, starting at `v0.1.0`.
  - A tag is placed on `main` after a green CI, and the workspace `manifest.yaml` pins tags, not `main`, for a known-good combination.
  - moto-vehicle-defs keeps its own rule: every signal change → CHANGELOG + new tag; docs-only changes need no tag.
  - The build files carry the same version: CMake `project(VERSION)`, `pyproject.toml`, `pubspec.yaml`.

**D-037 — Vehicle bus: a single read-only tester, not listen-only** (2026-09-29, user; clarifies D-009, D-020, D-021)
- The CL250 ECU does not broadcast its data; it answers UDS read requests (D-019). Collecting vehicle data therefore requires transmitting, so "listen-only" is not a possible scope for the vehicle bus. The scope is: **one tester (rt-core, D-021) that only reads**.
- What the tester may send is defined in **one place**: `uds/vehicle_cl250.yaml` → `tester_policy` (D-020). Today that is session control `0x10` 0x01/0x03, tester present `0x3E`, and the reads `0x22`, `0x19`, OBD `0x01`/`0x09`. Anything that writes data, clears DTCs, resets, unlocks security access, controls I/O, runs routines or reprograms the ECU is forbidden.
- codegen keeps its golden copy of the list on purpose (D-027: the YAML may narrow it, never widen it), and the generated gates enforce it at runtime. Docs, rules and agents link to `tester_policy` instead of repeating the list.
- Listen-only remains only for the Q-001 probe (is there passive traffic?) and the Raspi's optional raw-log tap (D-021).
- Q-020 (Flow Control for segmented responses) is deferred: the Ç3 vehicle client works with Single Frame responses only.

**D-038 — Turkish archive moved out of Claude's reading path** (2026-09-29, user)
- `docs/tr/` → `docs/archive/tr/` (nothing deleted; git history kept). The advisor documents (`bitirme-projesi-kapsam.md`, `bitirme-raporu-hoca-sunumu.md`) stay Turkish and live there too.
- Claude sessions do not read `docs/archive/` (a `Read` deny rule in the workspace and moto-vehicle-defs `.claude/settings.json`), so it never bloats the context. To use an archived file, the user removes the rule for that session.
- The thesis work packages Ç1-Ç8 that the English docs use are defined in English, with current targets, in `ARCHITECTURE.md` §9.

---

**D-039 — Ç3 vehicle UDS client: design choices** (2026-09-29, user; items 4-5 from the safety review of rt-core#5)
1. **Temporary ISO codes.** gen/ lacks the generic ISO 14229 codes the client needs: the 0x22 request SID, the 0x7F negative response, and NRCs 0x78/0x7E/0x7F. Until a defs `/signal-change` generates them, they live in rt-core `src/features/uds/uds_iso14229.h`. That header holds no vehicle facts: IDs, DIDs, formulas and timings still come only from gen/. The positive 0x62 check stays in the generated `vehicle_cl250_parse_response()`.
2. **Sample store.** The per-DID samples (raw, physical, receive time) live in rt-core `services/vehicle_signals`. The poller is the single writer. Readers, including the future platform-bus republisher, never include `features/`. VALID/STALE is derived from `stale_after_ms` when a sample is read, and STALE stays sticky until the next write.
3. **NRC handling.** An NRC other than 0x78 ends the pending request, as the legacy code does. It is not a timeout, and it counts as proof that the ECU is present. NRC 0x7E or 0x7F means the session was lost, and it is re-established with 0x10 03 only.
4. **Fail-closed latch.** The client latches, sends nothing more and reports the reason (`uds_client_fault()`) when:
   - the link refuses a request
   - the `can_if` guard refuses a frame
   - any frame appears on `VEHICLE_CL250_REQUEST_ID` or `FALLBACK_REQUEST_ID`, which means a second tester (parity with connectivity-node's latch, D-030)

   A full TX mailbox is not a fault: the client waits.
5. **Out of scope.** N_As and bus-off handling come with the H7 FDCAN HAL (Ç1). The FDCAN acceptance filters must pass both request IDs.
- Why: the user preferred not to block Ç3 on a defs release. The store has to be readable by other features. The NRC rule keeps the verified legacy behaviour. The latch enforces D-021 in code.

**D-040 — Ç3 platform UDS server and Q-021** (2026-09-30, user)
1. **ISO codes in gen/.** `uds/iso14229.yaml` holds the generic ISO 14229-1 codes (SIDs, sessions, 0x19 sub-functions, DTC status bits, NRCs, functional NRC suppression). Codegen emits `uds_iso14229.h` per node. CONN, a vehicle-bus tester only, gets the client subset: nothing outside the D-020 allow-list is emitted for it. A name in this file never allows sending: `tester_policy` and the golden copy still decide (D-020, D-027). This ends D-039 item 1.
2. **rt-core server** (`uds/dids.yaml` → `gen/c/rt_core/platform_uds.{h,c}`): physical 0x710 → 0x718, functional 0x7DF (Single Frame only), ISO 14229-2 default timing P2 50 ms, P2* 5000 ms, S3 5000 ms. Services 0x10 (01/03; 02 → NRC 0x12 until the bootloader), 0x3E, 0x22 (≤ 4 DIDs), 0x19 (01/02/0A), 0x14. Platform-bus ISO-TP parameters (padding 0xAA, BS 0, STmin 0, N_Bs/N_Cr 1000 ms) are platform choices.
3. **DIDs:** 0xF186 active session, 0xF189 SW version, 0xFD00 vehicle-tester status (ECU present, session up, latched, latch reason), 0xFD01 uptime, and 0xFD10-0xFD14 samples of the five CL250 DIDs (state, age, raw).
4. **DTCs:** U0100-00 (0xC10000) CL250 ECU communication lost, U3000-00 (0xF00000) vehicle UDS client latched. Status availability 0x09 (testFailed, confirmedDTC), reported level-triggered every pass. **0x14 runs in the extended session only** (there is no 0x27 yet), clears rt-core's own DTC records only, never the client latch, and never touches the vehicle bus. DTC memory is RAM only until the H7 flash driver exists.
5. **Q-021 resolved:** `vehicle_cl250.yaml` → `addressing.functional_watch` lists the OBD functional request IDs 0x7DF and 0x18DB33F1 as **watch-only**. rt-core never sends on them. A frame seen there latches the client with `FOREIGN_TESTER` (D-039 item 4), like the physical request IDs.
6. **Fail-safe status** (safety review of the Ç3 server, MAJOR-1): 0xFD00 carries `FAULT = NOT_RUNNING` (4). A status older than `max_age_ms` (500 ms), or none since boot, reads as not running, and U3000-00 fails. So a client that never opened or stopped looks faulty, never healthy.
7. **Preconditions (safety review):**
   - Before the DTC memory becomes flash-backed, 0x14 needs a rate limit or 0x27, because a platform node looping 0x14 would wear the flash.
   - Before any of 0x10 02, 0x11, 0x2E, 0x31 or 0x34-0x37 is offered on the platform server, 0x27 or an equivalent is mandatory. The platform bus is reachable from connectivity-node (Wi-Fi/BLE) and counts as unauthenticated.
   - The functional watch IDs are not verified on the CL250. Include 0x7DF and 0x18DB33F1 in the Q-001 listen-only probe before the first rt-core ride: OEM traffic on them would latch the client at boot.
- Why: D-039 asked for the codes in gen/. The DID/DTC set lets a platform tester see the vehicle poller's health without a second vehicle tester. Generic OBD dongles use functional addressing, so the D-021 watch must cover it.

## Open questions (awaiting decision)

| ID | Question | When to resolve | Note |
|---|---|---|---|
| Q-001 | ~~Classic CAN or FD, bitrate, OBD access~~ resolved by D-019; still open: does any passive broadcast traffic exist? | Before starting cl250.dbc (signal-map extraction, vehicle-work-plan.md §5.5) | Classic 500 kbps assumed for now |
| Q-002 | What does the safety node do once rt-core data becomes `INVALID` via E2E? (a) continue independently on its own minimal IMU, (b) conservative/low-confidence warning mode | once the safety-node hardware is finalized (Group 7) | The detection side is resolved by D-005 |
| Q-003 | Only one F103 is on hand: is it the io-node prototype or the HIL fault/power node? Will a second F103/G0 be procured? | during HIL hardware setup | |
| Q-004 | H7 ↔ ESP32-S3 SPI/UART bridge frame format | rt-core + connectivity, jointly | Proposal: COBS + CRC16 + msg-id, defined in defs |
| Q-005 | Will `archive/tr/bitirme-projesi-kapsam.md` be updated per D-001 and re-presented to the advisor? When will the H7 hardware be acquired? | before the advisor meeting | Schedule risk: Ç1-Ç3 can proceed on host tests + Renode before the H7 arrives |
| Q-006 | Where do the HARA/FMEA/requirements files live? (proposal: `moto-vehicle-defs/safety/` + `requirements/`) | at the start of Ç8 (schedule week 1-2) | |
| Q-007 | ~~resolved~~ → D-022 (Flutter) | — | — |
| Q-008 | Time synchronization: how is GPS PPS/NTP distributed to the MCUs? | Logging system (WP-4) | hardware-architecture.md §5b.8 proposes NTP |
| Q-009 | Realism level resolved by D-035 (log replay and live model as separate modes). Still open: the first target test function | while setting up the hil-bench host | hardware-architecture.md §10.3 |
| Q-010 | Will suspension potentiometers be added? | Group 11 | |
| Q-011 | ~~resolved~~ → D-020 | — | — |
| Q-012 | ~~resolved~~ → D-021 | — | — |
| Q-013 | ~~resolved~~ → D-023 | — | — |
| Q-014 | Provisional answer in D-029 (DEFAULT µ 0.5 + min rule, no default lean, mass 252 kg). Final values after measurement | with the measurement system | safety-reviewer S4 |
| Q-015 | Provisional answer in D-029 (speed poll 100 ms, TPS 200 ms, effective speed age ≤ 400 ms + accel margin). Confirm the ECU round-trip time and load, and add an EKF-fused high-rate speed | with the measurement system | safety-reviewer S3 |
| Q-016 | Partly resolved by D-028. Still open: VSS paths for node health (heartbeats) and the `*_VALID` bits, and a final review of the D-028 names | when linux-node needs them | D-004: user approves each path |
| Q-017 | Should the BLE packet schema move into moto-vehicle-defs (generated C/Dart/Python like the DBC) instead of verbatim copies + drift tests in moto-mobile and moto-server? | before BLE v4 | D-032 |
| Q-018 | ~~Temporary tester hardening~~ done in moto-connectivity-node#3 (2026-09-28): persistent latch + bus-off budget (RTC no-init, CRC, fail-safe restore), ≥2 s listen-only window, RX drained before TX and the timeout check. Remaining: bench/scope checks on target (reset reasons, TX during boot and the mode switch, TXD pull-up) | before the next vehicle-bus session | D-030 |
| Q-019 | Which H7 board: STM32H743 or H723 (flash/RAM, FDCAN count, package, price, Renode model)? Not decided (user, 2026-09-28) | before the CubeMX project, Renode L1 and Ç6 | D-001, D-034 |
| Q-020 | Should the D-020 frame gate (`vehicle_cl250_frame_allowed()`) let rt-core send a Flow Control (FC.CTS) on the vehicle bus? It passes Single Frames only today, so the tester cannot receive segmented responses: 0x19 with several DTCs and OBD 0x09 (VIN) end in N_TIMEOUT_CR. All current DIDs fit in a Single Frame. If yes: a versioned defs change with a byte-exact FC.CTS (fixed BS/STmin, padding), sent only while a reception runs for an allowed request (a link-state check in rt-core, not in the stateless can_if guard), capped FF_DL, requests stay Single Frame; safety-reviewer before the tag (conditions in moto-rt-core `src/features/uds/README.md`) | **Deferred by the user (2026-09-29, D-037):** the Ç3 client works with Single Frame responses only; revisit when 0x19 / 0x09 are needed | D-020, D-021, moto-rt-core#2 |
| Q-021 | ~~Should `uds/vehicle_cl250.yaml` define the OBD functional request IDs (0x7DF, 0x18DB33F1)?~~ | **Resolved by D-040 (2026-09-30):** watch-only, latches the client | safety re-review of rt-core#5, MINOR-2 |
