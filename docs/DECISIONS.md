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

**D-009 — Two separate CAN buses: vehicle (listen) + platform (dedicated)** (2026-09-25, Claude architecture proposal — revise if the user objects)
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
| Q-007 | moto-mobile: Flutter or React Native? | last repo | Flutter by default |
| Q-008 | Time synchronization: how is GPS PPS/NTP distributed to the MCUs? | Logging system (WP-4) | hardware-architecture.md §5b.8 proposes NTP |
| Q-009 | HIL realism level (replayed logs vs. live model) and the first target test function | while setting up the hil-bench host | hardware-architecture.md §10.3 |
| Q-010 | Will suspension potentiometers be added? | Group 11 | |
| Q-011 | Vehicle-bus rule update: allow `0x10` (0x01 default / 0x03 extended only, NEVER 0x02 programming) and `0x3E` next to `0x22/0x19` and OBD `0x01/0x09`; explicitly forbid `0x11` ECU reset alongside `0x2E/0x31/0x34/0x36/0x27` | Before rt-core UDS client work | Needed because the verified path uses them (D-019) |
| Q-012 | Poll-based vehicle data vs D-009: only ONE tester may poll the ECU. Proposal: rt-core is the single poller and republishes decoded vehicle signals on the platform bus (state range, E2E for speed); Raspi and safety-node read them from the platform bus. safety-node then depends on rt-core for vehicle speed (impacts Q-002; GPS/IMU fallback?) | Before platform.dbc v0.1.0 | Invalidates D-009's "safety-node/Raspi listen to the vehicle bus directly" bullet |
| Q-013 | How to bring `HondaCl250_Telemetry` into the org: transfer it as a read-only legacy repo and port its code into `moto-connectivity-node` (temporary telemetry home) + its `mobile_app/flutter_app` into `moto-mobile` (would resolve Q-007 as Flutter)? Keep PlatformIO/Arduino for the ported telemetry, or migrate to ESP-IDF (D-007)? | Before connectivity-node work | Repo is currently public in the personal account |
