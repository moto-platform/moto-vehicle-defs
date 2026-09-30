# moto-platform — Architecture (authoritative summary)

**Version:** 1.0 — 2026-09-25 · Source: `hardware-architecture.md` v1.0 + `DECISIONS.md`
If this file conflicts with the raw document, **this file + DECISIONS.md** govern.

---

## 1. Principles

1. **SDV:** a few powerful units + an isolated safety monitor + as many edge nodes as needed. A new function means a new software module, not a new box.
2. **Real-time and rich workloads on separate chips:** deterministic → MCU (bare-metal/RTOS), rich → Linux.
3. **Loose coupling:** if the Raspi, phone, or server crashes, the critical function keeps running. They add richness, they are not required.
4. **Single source of truth:** all signal/message/DID definitions live in `moto-vehicle-defs`; code is **generated** from them.
5. **Standards as concepts, not as a stack:** DBC (Vector de-facto), COVESA VSS, ISO 15765-2/14229 (ISO-TP/UDS), ASAM XCP, AUTOSAR E2E, and layering concepts. The Classic/Adaptive AUTOSAR stack is NOT USED (D-006).

---

## 2. Units

| Unit | Chip | Memory (RAM / flash) | CAN peripheral | Repo | Role |
|---|---|---|---|---|---|
| Domain controller | STM32H7 (H743/H723) | ~1 MB / 2 MB (H743) | FDCAN x2-3 | `moto-rt-core` | CAN gateway, logging, fusion, UDS/ISO-TP, bootloader, XCP, EKF (Layer 2), context, dyno, anomaly safety net |
| Safety monitor | STM32G4 (G474 class) | 128 KB / 512 KB | FDCAN x3 | `moto-safety-node` | Lean-angle safety decision (Layer 1, closed form, D-041), own fallback IMU (D-042), LED ring (owner: Q-026) |
| Zone/I/O | STM32G0 (G0B1 class); prototype F103 | 144 KB / 512 KB (F103: 20 KB / 64 KB) | FDCAN x2 (F103: bxCAN x1) | `moto-io-node` | Blind spot, immobilizer, park mode, power monitoring |
| Connectivity + audio | ESP32-S3 (WROOM module) | 512 KB (+PSRAM) | TWAI x1 (classic) | `moto-connectivity-node` | Wi-Fi/BLE, ESP-SR voice command, park notification |
| HPC | Raspberry Pi 5 8 GB | 8 GB | 2-channel CAN HAT (SocketCAN) | `moto-linux-node`, `moto-mcp` | Kuksa, CAN→VSS, lane tracking, anomaly model, HMI, OTA distribution, MCP |
| HIL simulator | STM32F4 (F407/F429) | 192 KB / 1 MB | bxCAN x2 | `moto-hil-bench/simulator` | Restbus (CL250 + platform nodes), vehicle dynamics model |
| HIL fault/power | STM32F103 | 20 KB / 64 KB | bxCAN x1 | `moto-hil-bench` | Fault injection, programmable power supply |
| HIL host / CI runner | i7 desktop, Linux | — | SocketCAN (USB-CAN) | `moto-hil-bench/host` | Scenario engine, evaluator, dashboard, self-hosted CI |

Incremental rollout: a unit is not added until its function arrives (see hardware-architecture.md §7).

---

## 3. Bus topology — two separate CAN buses (D-009)

```
 VEHICLE CAN (CL250 DLC, rt-core polls)  ═╤═══════════════════════════╤═══
   500 kbps classic (verified, D-019)     │ FDCAN1 (only tester)       │ can0 optional, listen-only
                                     ┌────┴────┐  ┌─────────┐   ┌─────┴─────┐
                                     │ rt-core │  │ safety  │   │  Raspi 5  │
                                     │ STM32H7 │  │ STM32G4 │   │ linux-node│
                                     └──┬───┬──┘  └────┬────┘   └─────┬─────┘
                               SPI/UART │   │FDCAN2    │FDCAN         │ can1
                                ┌───────┴┐  │          │              │
                                │ESP32-S3│  │          │              │
                                │  conn  │  │          │              │
                                └───┬────┘  │          │              │
 PLATFORM CAN (ours, dedicated) ════╧═══════╧══════════╧═══════╤══════╧═══
   500 kbps classic, 11-bit IDs, 120Ω at both ends          ┌──┴───────┐
                                                            │ io-node  │
                                                            │ STM32G0  │
                                                            └──────────┘
```

- **Vehicle bus:** OEM network reached through the diagnostic connector (DLC). CL250 data is **poll-based** (UDS `0x22`, 29-bit `0x18DA10F1` → `0x18DAF110`, D-019), so there must be exactly **one tester: rt-core** (D-021), and it has to transmit: listen-only cannot collect this data (D-037). It sends only the session and read requests listed in `uds/vehicle_cl250.yaml` → `tester_policy` (D-020, the single source; the generated gates enforce it), never anything that changes ECU state. No other node transmits here. The Raspi may tap it strictly listen-only for raw logging. No additional termination resistor is added to the vehicle bus.
- **Platform bus:** the dedicated bus our own nodes talk on. No risk of ID collisions, confusing the OEM ECU, or added OEM bus load. Classic CAN was chosen because F103 and ESP32-S3 TWAI don't support FD (an FD frame produces an error frame on a classic node). Migration will be reconsidered once all nodes support FD.
- **rt-core republishes vehicle signals** (speed, RPM, coolant, TPS, battery) on the platform bus (state range 0x100-0x3FF; vehicle speed keeps its E2E protection for its other consumers, but safety-node does not read 0x021, D-041). Everyone else, including the Raspi's kuksa-can-provider (`platform.dbc`), reads them there (D-021). safety-node takes only lean and µ from rt-core (D-041); when they are not usable it falls back to its own IMU (D-042, Q-002 resolved).
- ~~The safety node also listens to the vehicle bus~~ and ~~rt-core does not forward vehicle signals~~ (D-009 bullets superseded by D-021).
- H7 ↔ ESP32-S3: SPI/UART simple framed messaging (format to be co-designed, Q-004). Phase 2: SOME/IP.

---

## 4. Platform CAN ID plan and reliability

11-bit ID, lower ID = higher priority:

| Range | Class | E2E | Example |
|---|---|---|---|
| 0x000-0x00F | Reserved (emergency/network management) | — | — |
| 0x010-0x07F | **Safety critical** | Mandatory | lean angle/µ (rt-core→safety, D-041; 0x022 also carries total mass, which is not a safety-node input, D-029/D-041), cornering warning level, blind-spot status |
| 0x080-0x08F | Heartbeat (`0x080 + node_id`), 100 ms | Mandatory | node status, operating mode, error counter |
| 0x100-0x3FF | Status/control, context data bus | Optional | context classes, riding profile, immobilizer status |
| 0x400-0x5FF | Telemetry (low priority) | — | statistics, power measurement |
| 0x600-0x6FF | Bridge/log/development | — | — |
| 0x700-0x7FF | UDS diagnostics (platform nodes) | — | physical `0x7N0`/`0x7N8`, functional `0x7DF` |

**Node ID:** 1 RT_CORE · 2 SAFETY · 3 IO · 4 CONN · 5 LINUX · 0xE HIL_SIM · 0xF TESTER

**E2E (AUTOSAR E2E Profile 1/2-like, D-005):** protected messages carry a 4-bit alive counter + CRC8 (SAE J1850, poly 0x1D). The message's `E2E_DataID` is included in the CRC calculation but not transmitted. The receiver checks three things: **timeout** (3 × cycle), **counter jump/freeze**, **CRC**. If any of these fails, the signal is considered `INVALID` and the consumer transitions to its own safe state. For the safety node, an invalid lean/µ switches to its own-IMU fallback (DEGRADED, or UNAVAILABLE if no source is usable; D-042, Q-002 resolved, details in Q-023). Cost is 1-2 bytes per message plus a few lines of generated code.

**Heartbeat:** every node publishes one. The safety node monitors rt-core's heartbeat, rt-core monitors the other nodes. The Raspi health dashboard displays this.

---

## 5. Signal definition pipeline (D-003, D-004)

```
moto-vehicle-defs/
  uds/vehicle_cl250.yaml  vehicle ECU DIDs polled by rt-core (addressing, DID, formula, poll rate; verified per D-019)
  dbc/cl250.dbc         vehicle-bus broadcast frames — only if passive traffic is ever found (Q-001); skeleton for now
  dbc/platform.dbc      platform bus (ours; GenMsgCycleTime, E2E_DataID, E2E_Protected attributes), incl. rt-core's republished vehicle signals
  vss/overlay.vspec     motorcycle extensions (Vehicle.Motorcycle.*) + dbc2vss mappings (from platform.dbc)
  uds/dids.yaml         our platform nodes' UDS servers (IDs, timing, DIDs, DTCs)
  uds/iso14229.yaml     generic ISO 14229-1 codes
  tools/codegen/        python: cantools + vss-tools wrapper
        │ make gen  (run before tagging, output is committed)
        ▼
  gen/c/<node>/         per-node filtered: pack/unpack + E2E protect/check + ID constants + DID table (const, no malloc)
  gen/python/           signal constants for host/server/hil
  gen/vss/              VSS JSON for Kuksa (+ dbc2vss mapping)
```

- MCUs only include `gen/c/<their own node>/`. The only place that parses DBC/VSS files at runtime is the Linux/host side.
- VSS **lives only on the Raspi and above** (Kuksa, moto-mcp, server, mobile, ML). Raspi applications don't touch SocketCAN directly — they read from Kuksa.
- The safety path (cornering, blind spot) never enters VSS.
- Consumers pin the `external/moto-vehicle-defs` submodule to a **tag**. The schema-change process lives in the `/signal-change` skill.

---

## 6. Software layers (MCUs) — AUTOSAR concept mapping

```
src/features/<module>/  ≈ SWC      independent function; modules do NOT include each other
src/services/           ≈ BSW      signal pool, time base, logging, com (pack/unpack+E2E), diag, NVM
src/hal/                ≈ MCAL     thin wrapper over CubeMX HAL (can, imu, gps, gpio)
cubemx/                 generated code (Core/Drivers) — not hand-edited, except USER CODE blocks
external/moto-vehicle-defs  submodule (tagged)
tests/host/             host-native unit tests with Unity (pure logic: EKF, ISO-TP, E2E, decision)
```

- features → services → hal (one direction). If a feature is removed, the others still build and run.
- Safety-critical tasks run at the highest priority. A delay in a low-priority module doesn't affect them (freedom from interference).
- RTOS: FreeRTOS for rt-core (CubeMX CMSIS-RTOS2). Safety-node and io-node use a bare-metal super loop + timer interrupt (determinism, simplicity). If this changes, write it into DECISIONS.

---

## 7. Data flows

| Flow | Path | Channel | Criticality |
|---|---|---|---|
| Cornering warning | IMU/GPS/vehicle CAN → rt-core EKF → lean + µ [platform CAN, E2E] → safety-node decision (no speed, D-041; own-IMU fallback when rt-core data is unusable, D-042) → LED ring (owner: Q-026) | CAN | µs-ms, safety |
| Blind spot | radar x2 → io-node decision → mirror LED; status → platform CAN | local + CAN | reflex, safety |
| Context data bus | rt-core `context/` + EKF + measurements → platform CAN 0x100-0x3FF → consumers | CAN | ms |
| Telemetry/logging | rt-core → microSD (binary, block CRC) → Wi-Fi (ESP/Raspi) → moto-server → MDF4/Parquet | SD/Wi-Fi | latency-tolerant |
| VSS | vehicle + platform CAN → kuksa-can-provider → Kuksa Databroker → Raspi applications (gRPC) | local | ms |
| Cloud | Kuksa → MQTT/Zenoh → moto-server (InfluxDB+Grafana) | Wi-Fi | latency-tolerant |
| LLM assistant | moto-linux-node → moto-mcp (localhost, read-only) → cloud LLM; raw GPS is never sent | local/HTTPS | none |
| OTA | moto-server → Raspi → UDS bootloader (platform CAN) → MCU A/B bank | CAN | controlled |

---

## 8. Verification pyramid and CI

| Level | What | Where | CI |
|---|---|---|---|
| L0 | Unit tests (Unity / pytest), static analysis (cppcheck MISRA addon, ruff) | host | GitHub-hosted, every push |
| L1 | SIL: firmware on Renode, virtual CAN | host | GitHub-hosted, every PR |
| L2 | HIL: real DUT + STM32F4 restbus + fault injection | i7 bench | self-hosted runner, nightly/labeled PR |
| L3 | On-vehicle T0-T4 | CL250 | manual, per protocol |

Requirement–test traceability (Ç8): requirement IDs (`REQ-<DOMAIN>-NNN`) appear in test names/comments. Where the HARA/FMEA and requirements files live is open in Q-006.

---

## 9. Repo setup order

1. `moto-vehicle-defs` skeleton + codegen + `platform.dbc` draft → `v0.1.0`
2. `moto-hil-bench` host (Python, hardware-free) + Renode
3. `moto-connectivity-node` (migration of existing code)
4. `moto-rt-core` (once H7 arrives)
5. `moto-server` → 6. `moto-ml` → 7. `moto-safety-node` → 8. `moto-io-node` → 9. `moto-linux-node` + `moto-mcp` → 10. `moto-mobile`

The thesis core (Ç1-Ç8) is covered by steps 1-4 above, plus HIL, in this order.

**Thesis work packages** ("Ç" = *çekirdek*, the committed core scope of the thesis; the Turkish advisor document `archive/tr/bitirme-projesi-kapsam.md` §5 predates D-001, this table is current):

| ID | Work package | Current target | Repo |
|---|---|---|---|
| Ç1 | CAN driver layer: error state machine, bus-off recovery | H7 FDCAN behind `hal/can_port` (D-001) | moto-rt-core |
| Ç2 | ISO-TP transport (ISO 15765-2) | `features/uds/isotp_*` (done, v0.2.0) | moto-rt-core |
| Ç3 | UDS (ISO 14229), two parts: **server** for our own nodes on the platform bus (built scope, D-040: 0x10 (01/03), 0x3E, 0x22, 0x19, 0x14 on *our* ECU), and the **vehicle client** (the poller) that only reads the CL250 (D-037). Not offered yet: 0x27, 0x2E, 0x31 and the bootloader services 0x11, 0x34-0x37; D-040 item 7 requires 0x27 (or an equivalent) before any of 0x10 02, 0x11, 0x2E, 0x31, 0x34-0x37 | `features/uds/`; client released in rt-core v0.3.0, server merged (rt-core#9), not yet tagged | moto-rt-core |
| Ç4 | HIL bench hardware: STM32F4 restbus simulator, transceivers, termination, OBD2 connector, programmable supply | D-001, D-035 | moto-hil-bench |
| Ç5 | HIL bench software: scenario engine, fault injection, automatic evaluation, report | log replay + live model (D-035) | moto-hil-bench |
| Ç6 | Test automation: self-hosted runner, build + static analysis + on-hardware regression per commit | needs the H7 board (Q-019) | all firmware repos |
| Ç7 | Data collection: signal logging, timestamps, metadata, storage schema | `phase0-data-collection-plan.md` | connectivity-node, mobile, server |
| Ç8 | Process documentation: HARA, requirement–test traceability, FMEA (ISO 26262 approach) | location open (Q-006) | moto-vehicle-defs |

Extended scope G1-G5 (bootloader, XCP, riding modes, voice, client-server) is in the same Turkish document §5.2.
