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

---

## Open questions (awaiting decision)

| ID | Question | When to resolve | Note |
|---|---|---|---|
| Q-001 | Is the CL250 vehicle bus classic CAN or FD? Bitrate? Is OBD-II accessible? | Before starting cl250.dbc (signal-map extraction, vehicle-work-plan.md §5.5) | Classic 500 kbps assumed for now |
| Q-002 | What does the safety node do once rt-core data becomes `INVALID` via E2E? (a) continue independently on its own minimal IMU, (b) conservative/low-confidence warning mode | once the safety-node hardware is finalized (Group 7) | The detection side is resolved by D-005 |
| Q-003 | Only one F103 is on hand: is it the io-node prototype or the HIL fault/power node? Will a second F103/G0 be procured? | during HIL hardware setup | |
| Q-004 | H7 ↔ ESP32-S3 SPI/UART bridge frame format | rt-core + connectivity, jointly | Proposal: COBS + CRC16 + msg-id, defined in defs |
| Q-005 | Will `tr/bitirme-projesi-kapsam.md` be updated per D-001 and re-presented to the advisor? When will the H7 hardware be acquired? | before the advisor meeting | Schedule risk: Ç1-Ç3 can proceed on host tests + Renode before the H7 arrives |
| Q-006 | Where do the HARA/FMEA/requirements files live? (proposal: `moto-vehicle-defs/safety/` + `requirements/`) | at the start of Ç8 (schedule week 1-2) | |
| Q-007 | moto-mobile: Flutter or React Native? | last repo | Flutter by default |
| Q-008 | Time synchronization: how is GPS PPS/NTP distributed to the MCUs? | Logging system (WP-4) | hardware-architecture.md §5b.8 proposes NTP |
| Q-009 | HIL realism level (replayed logs vs. live model) and the first target test function | while setting up the hil-bench host | hardware-architecture.md §10.3 |
| Q-010 | Will suspension potentiometers be added? | Group 11 | |
