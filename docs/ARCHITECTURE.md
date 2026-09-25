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
| Safety monitor | STM32G4 (G474 class) | 128 KB / 512 KB | FDCAN x3 | `moto-safety-node` | Lean-angle safety decision (Layer 1, closed form), LED ring |
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
 VEHICLE CAN (CL250, OEM — listen only) ══╤════════════╤══════════════╤═══
   500 kbps classic (verify, Q-001)       │ FDCAN1     │ FDCAN silent │ can0 listen-only
                                     ┌────┴────┐  ┌────┴────┐   ┌─────┴─────┐
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

- **Vehicle bus:** OEM network. Hardware-level **silent/listen-only mode** (FDCAN bus-monitoring, SocketCAN `listen-only on`). ONE exception: rt-core's OBD-II/UDS **read** requests (0x01/0x09/0x22/0x19). 0x2E/0x31/0x34/0x36/0x27 are NEVER sent to the vehicle. No additional termination resistor is added to the vehicle bus.
- **Platform bus:** the dedicated bus our own nodes talk on. No risk of ID collisions, confusing the OEM ECU, or added OEM bus load. Classic CAN was chosen because F103 and ESP32-S3 TWAI don't support FD (an FD frame produces an error frame on a classic node). Migration will be reconsidered once all nodes support FD.
- **The safety node also listens to the vehicle bus** (silent): it receives vehicle signals such as wheel speed without depending on rt-core. Only the EKF outputs (lean angle, µ, mass) come from rt-core.
- **The Raspi listens to both buses:** kuksa-can-provider feeds from both `cl250.dbc` and `platform.dbc`. rt-core does **not** forward vehicle signals onto the platform bus (so bus load doesn't double).
- H7 ↔ ESP32-S3: SPI/UART simple framed messaging (format to be co-designed, Q-004). Phase 2: SOME/IP.

---

## 4. Platform CAN ID plan and reliability

11-bit ID, lower ID = higher priority:

| Range | Class | E2E | Example |
|---|---|---|---|
| 0x000-0x00F | Reserved (emergency/network management) | — | — |
| 0x010-0x07F | **Safety critical** | Mandatory | lean angle/µ/mass (rt-core→safety), cornering warning level, blind-spot status |
| 0x080-0x08F | Heartbeat (`0x080 + node_id`), 100 ms | Mandatory | node status, operating mode, error counter |
| 0x100-0x3FF | Status/control, context data bus | Optional | context classes, riding profile, immobilizer status |
| 0x400-0x5FF | Telemetry (low priority) | — | statistics, power measurement |
| 0x600-0x6FF | Bridge/log/development | — | — |
| 0x700-0x7FF | UDS diagnostics (platform nodes) | — | physical `0x7N0`/`0x7N8`, functional `0x7DF` |

**Node ID:** 1 RT_CORE · 2 SAFETY · 3 IO · 4 CONN · 5 LINUX · 0xE HIL_SIM · 0xF TESTER

**E2E (AUTOSAR E2E Profile 1/2-like, D-005):** protected messages carry a 4-bit alive counter + CRC8 (SAE J1850, poly 0x1D). The message's `E2E_DataID` is included in the CRC calculation but not transmitted. The receiver checks three things: **timeout** (3 × cycle), **counter jump/freeze**, **CRC**. If any of these fails, the signal is considered `INVALID` and the consumer transitions to its own safe state. The safety node's behavior in this case is open in Q-002. Cost is 1-2 bytes per message plus a few lines of generated code.

**Heartbeat:** every node publishes one. The safety node monitors rt-core's heartbeat, rt-core monitors the other nodes. The Raspi health dashboard displays this.

---

## 5. Signal definition pipeline (D-003, D-004)

```
moto-vehicle-defs/
  dbc/cl250.dbc         vehicle bus (reverse-engineered, UNVERIFIED signals flagged)
  dbc/platform.dbc      platform bus (ours; GenMsgCycleTime, E2E_DataID, E2E_Protected attributes)
  vss/overlay.vspec     motorcycle extensions (Vehicle.Motorcycle.*) + dbc2vss mappings
  uds/dids.yaml         DID/DTC/routine definitions (per node)
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
| Cornering warning | IMU/GPS/vehicle CAN → rt-core EKF → [platform CAN, E2E] → safety-node decision → LED ring | CAN | µs-ms, safety |
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

The thesis core (Ç1-Ç8) is covered by steps 1-4 above, plus HIL, in this order. Ç1's target is now H7 FDCAN (D-001).
