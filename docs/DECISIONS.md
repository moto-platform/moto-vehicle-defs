# Decision Record (ADR) and Open Questions

Format: brief. Each decision states **what**, **why**, and, where relevant, **consequence**. New decisions go at the bottom, with the next number. If a decision changes, the old one is not deleted — it is `~~struck through~~` and linked to the new one.

---

## Decisions

**D-001 — Authoritative document: hardware architecture** (2026-09-25, user)
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

**D-009 — Two separate CAN buses: vehicle (listen) + platform (dedicated)** _(bullets on safety-node/Raspi tapping the vehicle bus superseded by D-021)_ (2026-09-25, Claude architecture proposal — revise if the user objects)
The architecture document stated both that "only the main MCU writes to the vehicle bus" (§4) and that io-node/rt-core publish status onto the vehicle bus (§5b.1, §5b.2); this was a contradiction. Resolution: our nodes talk on their own **platform CAN** bus. The vehicle bus is hardware listen-only; the sole exception is rt-core's OBD/UDS read requests. Why: this removes the risks of OEM ID collisions, confusing the OEM ECU, and added bus load; the two buses are simulated separately in HIL. The platform bus is classic CAN at 500 kbps (F103/ESP32 TWAI don't support FD). Details in `ARCHITECTURE.md` §3-4.

**D-010 — moto-server language: Python** (2026-09-25, Claude)
The document said "Python/Go". Python (FastAPI) was chosen so it shares the same language and toolchain as hil-host, ml, mcp, and linux-node. Starting point: file + Python, or InfluxDB+Grafana (hardware-architecture.md §5b.8).

**D-011 — Language convention** (2026-09-25, user)
All project documentation, CLAUDE.md files, code, identifiers, comments, commit messages and READMEs are in English. Turkish originals are archived under `docs/tr/` (not maintained). Exception: advisor-facing university documents (`tr/bitirme-projesi-kapsam.md`, `tr/bitirme-raporu-hoca-sunumu.md`) remain Turkish. Commits: Conventional Commits.

**D-012 — RTOS** (2026-09-25, Claude)
rt-core: FreeRTOS (CMSIS-RTOS2, CubeMX). safety-node and io-node: bare-metal super loop + timer interrupt (determinism, verifiability). HIL simulator: bare-metal or FreeRTOS, chosen when the repo is set up.

**D-013 — manifest ref** (2026-09-25, Claude)
`moto-vehicle-defs` is referenced as `main` in the manifest since it hasn't been tagged yet. The first release will be `v0.1.0` (`v1.0.0` once platform.dbc is stable).

**D-014 — Docs archive** (2026-09-25, Claude)
Turkish source docs moved to `docs/tr/`; English translations are authoritative.

**D-015 — Workspace repo `moto-workspace`** (2026-09-25, Claude; user asked to finish remaining setup) The workspace root is its own repo holding `manifest.yaml`, `setup.sh`, root `CLAUDE.md`, `STATUS.md` and the shared `.claude/` agents/skills. It git-ignores `/moto-*/`. Why: otherwise the shared Claude setup exists on one laptop only and cannot reach GitHub or cloud sessions.

~~**D-016 — Repo visibility: temporarily public**~~ (superseded by D-017) (2026-09-25, user) The planned default stays **private**, but all 12 repos in `moto-platform` are public for now (profile visibility, nothing sensitive at this stage). They can be switched back to private at any time with `gh repo edit moto-platform/<repo> --visibility private --accept-visibility-change-consequences`. No LICENSE yet, so the default is all rights reserved. The license decision is still pending (moto-mcp is intended to be open source). Before committing anything sensitive (real ride GPS data, keys, personal info), re-check visibility.

**D-017 — Repo visibility: private** (2026-09-25, user) All 12 repos are back to **private** (D-016 was reverted the same day). They will go public later by user decision, together with the license decision.

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

**D-024 — VSS base: COVESA VSS 6.0 via pinned release files** (2026-09-25, Claude proposal during the defs bootstrap — revise if the user objects)
`gen/vss/vss_dbc.json` = VSS 6.0 release (`vss.yaml`, `units.yaml`, `quantities.yaml`, sha256-pinned in `gen_vss.py`) + `vss/overlay.vspec`, exported with vss-tools **6.0** (6.1 rejects the 6.0 `units.yaml` with a duplicate-unit error). Why: 6.0 is the newest release kuksa-can-provider ships a mapping for (`mapping/vss_6.0`). Consequences: VSS 6 has no `Vehicle.OBD` branch and uses `CombustionEngine.EngineCoolant.Temperature`; Kuksa Databroker on linux-node must load the same JSON; a VSS upgrade is a deliberate MAJOR/MINOR change here.

**D-025 — platform.dbc v0.1 message set** (2026-09-25, Claude proposal — revise if the user objects)
Safety range (E2E): `EkfLean` 0x020 / 20 ms, `VehicleSpeed` 0x021 / 50 ms, `EkfFrictionMass` 0x022 / 100 ms, all RT_CORE → SAFETY, LINUX (speed also CONN). Each EKF estimate carries a quality % and a 2-bit state (ESTIMATED / CLAMPED / DEFAULT fallback / INVALID, per hardware-architecture §5b.2); `VehicleSpeed` carries VALID + AGE (ms since the ECU sample) because the ECU speed DID is polled every 800 ms. Heartbeats 0x081-0x085 / 100 ms (E2E): NODE_MODE, ERROR_COUNT, UPTIME. State range: `VehicleEngine` 0x110 / 50 ms (RPM, battery, coolant, TPS with the J1979 source scaling, per-signal VALID + ECU_PRESENT). `E2E_DataID` convention `0x1000 + CAN ID`; `NodeId` is a BU_ attribute. CoG height and a cornering-warning output message are not defined yet (later MINOR). `uds/vehicle_cl250.yaml` gets a platform-chosen `stale_after_ms` = 3 × poll period per DID (not a legacy value). rt-core sends `*_STATE = INVALID`, `QUALITY = 0` until the EKF has converged.

**D-026 — E2E profile details** (2026-09-25, Claude proposal refining D-005 — revise if the user objects)
CRC-8/SAE-J1850 (0x1D, init 0xFF, xorout 0xFF) over DataID low, DataID high, bytes 1..n-1; 4-bit counter 0..15; receiver max delta counter 1 (a single lost frame invalidates that cycle); timeout 3 × cycle, enforced both by `check_timeout()` and inside `check()` (a frame after a gap longer than the timeout resyncs as `INITIAL`, so a stalled sender never resumes as `OK`); `INITIAL` is not usable. Spec: `docs/e2e-profile.md`. Generated C is cross-checked against the Python reference.

**D-027 — codegen targets and vehicle-bus guard** (2026-09-25, Claude proposal refining D-003 — revise if the user objects)
C is generated for RT_CORE, SAFETY, IO, CONN, HIL_SIM (`gen/c/<node>/`, cantools `use_float`, C99, no heap); HIL_SIM gets every message (restbus impersonation). LINUX and TESTER use the DBC/VSS at runtime and get Python/VSS only. The CL250 DID table goes to rt_core, conn (temporary tester, D-023) and hil_sim (ECU simulator), together with generated `vehicle_cl250_request_allowed()` (payload) and `vehicle_cl250_frame_allowed()` (raw ISO-TP Single Frame only) implementing D-020, which every vehicle-bus transmission must pass, and `vehicle_cl250_parse_response()` (checks SID 0x62 + DID echo). codegen holds a golden copy of the D-020 allow-list: the YAML policy may narrow it but never widen it (safety-reviewer finding).

---

## Open questions (awaiting decision)

| ID | Question | When to resolve | Note |
|---|---|---|---|
| Q-001 | ~~Classic CAN or FD, bitrate, OBD access~~ resolved by D-019; still open: does any passive broadcast traffic exist? | Before starting cl250.dbc (signal-map extraction, vehicle-work-plan.md §5.5) | Classic 500 kbps assumed for now |
| Q-002 | What does the safety node do once rt-core data becomes `INVALID` via E2E? (a) continue independently on its own minimal IMU, (b) conservative/low-confidence warning mode | once the safety-node hardware is finalized (Group 7) | The detection side is resolved by D-005 |
| Q-003 | Only one F103 is on hand: is it the io-node prototype or the HIL fault/power node? Will a second F103/G0 be procured? | during HIL hardware setup | |
| Q-004 | H7 ↔ ESP32-S3 SPI/UART bridge frame format | rt-core + connectivity, jointly | Proposal: COBS + CRC16 + msg-id, defined in defs |
| Q-005 | Will `tr/bitirme-projesi-kapsam.md` be updated per D-001 and re-presented to the advisor? When will the H7 hardware be acquired? | before the advisor meeting | Schedule risk: Ç1-Ç3 can proceed on host tests + Renode before the H7 arrives |
| Q-006 | Where do the HARA/FMEA/requirements files live? (proposal: `moto-vehicle-defs/safety/` + `requirements/`) | at the start of Ç8 (schedule week 1-2) | |
| Q-007 | ~~resolved~~ → D-022 (Flutter) | — | — |
| Q-008 | Time synchronization: how is GPS PPS/NTP distributed to the MCUs? | Logging system (WP-4) | hardware-architecture.md §5b.8 proposes NTP |
| Q-009 | HIL realism level (replayed logs vs. live model) and the first target test function | while setting up the hil-bench host | hardware-architecture.md §10.3 |
| Q-010 | Will suspension potentiometers be added? | Group 11 | |
| Q-011 | ~~resolved~~ → D-020 | — | — |
| Q-012 | ~~resolved~~ → D-021 | — | — |
| Q-013 | ~~resolved~~ → D-023 | — | — |
| Q-014 | How conservative must the rt-core DEFAULT fallback values be (µ, mass, lean)? E.g. DEFAULT µ = low bound (wet/gravel) vs. safety-node ignoring DEFAULT and using its own constant | before rt-core EKF / safety-node decision code | safety-reviewer S4; must never loosen the ceiling (§5b.2) |
| Q-015 | Maximum acceptable VEHICLE_SPEED_AGE for safety-node, and should DID 0xF40D be polled faster than the legacy 800 ms (e.g. 100 ms, second priority after RPM)? | before safety-node uses speed | safety-reviewer S3; 800 ms at 0.5 g ≈ 14 km/h error |
| Q-016 | `Vehicle.Motorcycle.*` extensions for lean angle, friction, mass, node health, and where TPS maps (VSS 6 has no `Vehicle.OBD.ThrottlePosition`) | when linux-node needs them | D-004: user approves each path |
