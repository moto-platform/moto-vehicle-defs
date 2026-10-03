# Hardware integration — Phase 0 data-collection build (CL250)

**Status:** working guide, started 2026-10-03. **Scope:** the first on-vehicle build that collects data with the code that exists today. It does not change any decision. Authority: `DECISIONS.md` > `ARCHITECTURE.md` > `vehicle-work-plan.md` / `phase0-data-collection-plan.md` > this file. Items marked **CONFIRM** are not documented anywhere yet. Fill them in from the bike or the parts on the desk; never guess them.

## 1. What this build is

- **Node:** `moto-connectivity-node` on an ESP32-S3 DevKitC-1. Until rt-core runs on the bike, it is the **temporary sole vehicle-bus tester** (D-021, D-023, D-037).
- **Path:** CL250 ECU → DLC Y-cable → CAN transceiver → ESP32-S3 TWAI → BLE → phone (`moto-mobile`) → session zip → `moto-server` (D-032).
- **No on-vehicle storage:** conn keeps no local copy. Data lost while the phone is disconnected is accepted, and the server report shows the gaps (D-045). Persistent logging (microSD, safe shutdown) is rt-core's job later, so the Phase 0 plan's microSD and supercapacitor items are not part of this build.
- **IMU:** an MPU-6050-class IMU on the same ESP32 at 100 Hz, streamed over BLE. It is for offline analysis only: it is not a vehicle signal, not a safety input, and no lean is estimated from it (D-032, D-044).
- **Not in this build:** rt-core (H7, Q-019), the platform bus, safety-node, io-node, Raspi. GPS joins it per D-060 (see §9).

```
 CL250 DLC ──Y-cable (CANH, CANL, GND; < 50 cm, twisted)──┐
                                                          │
 12 V ignition-switched ─ fuse 2 A ─ reverse-polarity ─ TVS ─ LC ─ buck 6-40 V → 5 V
                                                          │            │
                                              ┌───────────┴────────────┴───────────┐
                                              │ SN65HVD230 ── GPIO4 TX / GPIO5 RX  │
                                              │ ESP32-S3 DevKitC-1 (conn firmware) │
                                              │ MPU-6050 ── I2C GPIO1 SDA / GPIO2 SCL (0x68, 400 kHz)
                                              │ Nextion (optional) ── UART2 GPIO17 TX / GPIO18 RX
                                              └──────────────┬─────────────────────┘
                                                             │ BLE "Honda-CL250-Telemetry"
                                                    phone: moto-mobile ── session zip ──► moto-server (laptop)
```

## 2. Parts list for this build

Sources: `phase0-data-collection-plan.md` §9, `hardware-procurement-list.md` (groups 1-3, 10, "Already On Hand"), `vehicle-work-plan.md` §3.

| Part | Spec | Role | On hand |
|---|---|---|---|
| ESP32-S3 DevKitC-1 | WROOM module | conn firmware | listed as "probably": **CONFIRM** |
| CAN transceiver | SN65HVD230 (3.3 V) | TWAI ↔ vehicle CAN | **CONFIRM** |
| IMU | MPU-6050 class, must deliver ±8 g / ±500 dps at 100 Hz (D-032) | raw motion data | **CONFIRM** (part provisional, D-032) |
| DLC Y-cable | Parallel to the OEM connector, no cut | bus access | **CONFIRM** connector type |
| Fuse + holder | 2 A, blade or glass | input protection | **CONFIRM** |
| Reverse-polarity protection | Series Schottky or P-MOSFET | input protection | **CONFIRM** |
| TVS diode | Bidirectional, 24-30 V clamp | load-dump / transients | **CONFIRM** |
| Buck converter | Wide input 6-40 V → 5 V, 2-3 A | supply | **CONFIRM** |
| Input filter | Electrolytic + ceramic, LC | EMC | **CONFIRM** |
| INA226 (optional) | Current/voltage monitor | sleep-current check (§7) | **CONFIRM**, or use a multimeter |
| Enclosure | ABS or aluminium, ≥ IP54, < 100 × 70 × 30 mm target | protection | **CONFIRM** |
| Connectors, glands, wrap | Locking connector (one detachable plug), PG7 glands, spiral wrap | assembly | **CONFIRM** |
| Nextion display | UART2 | optional local display | on hand |
| Phone | Android with the `moto-mobile` APK | BLE receiver, session files | **CONFIRM** |
| Laptop | `moto-server` (uv or Docker) | ingest + report | on hand (i7 desktop or laptop) |

## 3. Electrical integration

Rules from `vehicle-work-plan.md` §3.2, §3.3 and §4; vehicle bus facts from D-019.

### 3.1 Vehicle CAN

| Item | Value | Source |
|---|---|---|
| Access point | Diagnostic connector (DLC), Y-cable parallel to the OEM plug, harness never cut | VWP §3.2, §4.1 |
| Lines | CANH, CANL, GND | VWP §3.2 |
| DLC location and pinout on the CL250 | **CONFIRM** (not documented; the legacy build used it, D-019) | — |
| Bus | Classic CAN, 500 kbps | D-019 |
| Addressing | 29-bit, request `0x18DA10F1` → response `0x18DAF110` | D-019, `uds/vehicle_cl250.yaml` |
| Termination | **None added.** The vehicle line is already terminated at both ends | VWP §3.2 |
| Cable | Twisted pair, shielded if possible, < 50 cm, away from the ignition coil and plug lead | VWP §3.2, §4.2 |
| ESP32 pins | TWAI TX `GPIO4`, RX `GPIO5` (`src/main.cpp`) | `legacy-telemetry-notes.md` §5 |

### 3.2 Power

| Item | Value |
|---|---|
| Tap | Ignition-switched line, not the always-on battery line (no drain when parked). Exact tap point: **CONFIRM** |
| Chain | 2 A fuse at the unit input → reverse-polarity (Schottky or P-MOSFET) → bidirectional TVS (24-30 V) → LC filter → buck 5 V → DevKitC 5 V pin |
| Ground | Directly to the battery negative, not the chassis |
| Sleep current | Target < 1 mA with the ignition off, verified by measurement (§7, T0); above that, switch the supply with the ignition |

### 3.3 IMU and display wiring

- IMU on I2C: SDA `GPIO1`, SCL `GPIO2`, address `0x68`, 400 kHz. Keep the I2C wires short, inside the enclosure.
- Nextion (optional): UART2 TX `GPIO17`, RX `GPIO18`, 115200 8N1.
- `GPIO8` pulses high for each `loop()` pass (scope probe for the step time, §6).

## 4. Mechanical integration

| Item | Rule | Source |
|---|---|---|
| Location | Under the seat (preferred) or inside a side panel; never near the engine block | VWP §3.1 |
| Heat | ≥ 15 cm from exhaust, cylinder, radiator, or a heat shield | VWP §4.1 |
| Unit mount | Silicone mount or vibration-damping tape | VWP §3.1 |
| IMU mount | **Rigid, never on the damped mount** (a damper adds its own resonance); aligned with the bike's longitudinal axis, offset measured and corrected in software | VWP §3.4 |
| IMU vs unit | If the unit sits on a damped mount, the IMU goes on its own rigid bracket on the frame. Exact spot and axis directions: **CONFIRM** and record them in the session metadata | VWP §3.4 |
| Removal | One detachable connector takes the whole unit off the bike | VWP §3.1, §4.1 |
| Cables | Spiral wrap or conduit, clear of steering, suspension and chain, every end labelled, wiring diagram kept with this file | VWP §4.1 |
| Rain | Glands on every cable entry; the enclosure must not collect water at the cable side | VWP §3.1 |

## 5. Firmware and software setup

| Step | Command / action | Repo |
|---|---|---|
| Build + flash (real CAN) | `pio run -e esp32-s3-devkitc-1 -t upload` (needs `platformio_local.ini` with `AP_PASSWORD`) | moto-connectivity-node |
| Desk test without the bike | `pio run -e esp32-s3-devkitc-1-mock -t upload` (synthetic telemetry) | moto-connectivity-node |
| Host tests before every flash | `scripts/native_tests.sh` (or `pio test -e native`) | moto-connectivity-node |
| Phone | Install the `moto-mobile` APK, pair with `Honda-CL250-Telemetry` | moto-mobile |
| Server | `export MOTO_API_TOKEN=…; uv run moto-server serve`, or `uv run moto-server import <zip>` offline | moto-server |
| Check a session | `uv run moto-server report <session_id>` (gaps, MTU, CAN health) | moto-server |

What the tester does on its own, with no setting to change (conn README, Q-018, D-030):
- After boot it **listens only** until it has 2 s of clean traffic (no lost frames, no other tester, no unsolicited ECU answer). Only then does it send its first request.
- It sends only what `tester_policy` allows, through `vehicle_cl250_frame_allowed()` (D-020).
- It latches off when it sees another tester or repeated bus-offs. The latch survives resets until the next power cycle.

## 6. Bring-up sequence (each gate passes before the next)

| Gate | Where | Do | Pass when |
|---|---|---|---|
| B0 | Desk | Native tests; mock firmware; phone receives v3 telemetry + IMU blocks; record a session; `moto-server import` it | Report `ok`, IMU gap count 0 at rest |
| B1 | Desk, bench supply 12-14 V | Power chain only: fuse, TVS, buck; check 5 V under load; reverse the input once (must not conduct) | 5 V stable, no heat on the buck |
| B2 | Desk | Real firmware, transceiver connected, no bus | Stays in its listen window, sends nothing |
| V0 | Bike, ignition on, engine **off** | Plug the Y-cable, power the unit, phone connected | ECU present, all 5 DIDs valid, no latch flags, no bus-off |
| V1 | Bike, engine idling, **closed area** | First polling session with the engine running (VWP §3.2) | RPM changes with a throttle blip; CAN health clean for ≥ 5 min |
| V2 | T0 static set | VWP §7 (sleep current, cranking, idle, warm-up from cold) | §7 checks below |
| V3 | T1 low speed, closed lot, 0-30 km/h (VWP §7.3) | CAN speed against the gear-ratio formula (VWP §2.3); ignition cut mid-session | Deviation explained (speedometer error, VWP §2.3); after the cut the phone keeps the session and the report shows the gap |

Road tests (T2, T3) come only after V3 passes, and the rules in §8 apply. T4 is out of scope for this build.

## 7. What to measure in the first sessions

| Measurement | Why | How with this build |
|---|---|---|
| Tester step gap | D-053 assumes `client_step_max_ms` = 10 ms; conn's step is unbounded (conn README) | D-058 item 2: the poller's step-gap max and over-10-ms count in BLE telemetry v4 (server report); the G0.1 serial report still gives the per-module `loop()` durations; scope on `GPIO8` |
| ECU round trip | D-029, A-4 polling budget (assumed 20 ms) | D-058 item 1: per DID min/max/sum/count and 0x78 count, one rotating record per BLE telemetry v4 packet (server report) |
| Passive broadcast traffic | Q-001 (VWP §5.5 step 1: 5 min listen-only) | D-058 item 4: flash the `esp32-s3-devkitc-1-listen-only` env (no TX at all), log USB serial for 5 min with the ignition on, then flash the tester env again. Record the result on Q-001 |
| PID support, vehicle info, DTCs | A-4: MAP, fuel trim, wheel speed | D-059: flash the `esp32-s3-devkitc-1-probe` env once (0x01 bitmaps, 0x09, 0x19, 0x22 0xF4xx support DIDs, segmented answers with one FC.CTS); the serial output goes into defs with `/signal-change`, `verified: false`. Never commit the VIN |
| Sleep current | VWP §4.3, < 1 mA | Multimeter or INA226 in series, ignition off |
| Engine-on noise | VWP §4.2 | The same idle recording with the engine stopped and running; compare CAN error counters and IMU noise |
| IMU zero and axis offset | VWP §3.4, §5.4 | Upright on flat ground, then a known tilt (side stand) |
| BLE loss | D-045 | Server report: seq and tick gaps per session |

## 8. Safety rules on the bike

- **One tester only, and it only reads** (D-037). Never connect a scan tool, another dongle or a second build while conn is on the DLC. conn latches off if it sees one, but the rule is to not let it happen.
- Nothing that writes, clears, resets, unlocks, controls or reprograms the ECU, ever (D-020). The gate enforces it; do not flash a firmware that bypasses it.
- First engine-on session in a closed area, engine idling (VWP §3.2).
- Check that recording works **before** riding, never while riding. Full protective gear; T4 limit tests only on a closed area with a second person (VWP §7, §12).
- The unit must not change how the bike behaves: power from the ignition-switched line, a 2 A fuse, the harness never cut, one plug to remove it.

## 9. Data handling

- **Session = one ride.** Files per `moto-mobile/docs/session-format.md`: `meta.json`, `telemetry.csv`, `events.csv`, `summary.json`, `imu.csv`.
- Fill the metadata of the Phase 0 plan §3.2 / VWP §6.2: ambient temperature and weather, tyre pressures, fuel level, rider weight and load, vehicle configuration, condition label (healthy / fault type), route type, notes. Add the unit and IMU mounting (§4).
- **Never commit ride data to any repo** (all repos are public, D-033). Sessions live under `$MOTO_DATA_DIR` on the server machine, with a second copy off the laptop.
- **GPS (D-060):** a u-blox NEO-M8N on a conn UART (UBX-NAV-PVT, 10 Hz; pins **CONFIRM**). Only ground speed, heading, their accuracies, fix type and satellite count leave conn, on the BLE GPS block; latitude, longitude and height never do. The phone writes them to `gps.csv`, which goes to the server with the session. A speed + heading series can rebuild the route's shape, so sessions stay on your own machine and never in a repo.

## 10. Open items (fill in, then move facts into the sections above)

| # | Item | Blocks |
|---|---|---|
| 1 | CL250 DLC location, connector type and pinout | §3.1, Y-cable |
| 2 | Parts actually on hand (every **CONFIRM** in §2) | Build start |
| 3 | Ignition-switched tap point on the CL250 harness | §3.2 |
| 4 | IMU bracket location and axis directions | §4, metadata |
| 5 | ~~GPS source and privacy handling~~ decided in D-060; UART pins still **CONFIRM** | T1 speed check, §9 |
| 6 | ~~Listen-only capture tool for Q-001~~ decided in D-058 item 4 (conn `-listen-only` env) | §7 |
| 7 | ~~ECU round-trip instrumentation~~ decided in D-058 items 1-3 (BLE telemetry v4) | D-029, A-4 |

## 11. Later: moving to rt-core

When the H7 board exists (Q-019), rt-core becomes the tester (D-021). conn is then built with `-e esp32-s3-devkitc-1-no-tester` (no TWAI driver at all), so there are never two testers. rt-core needs two transceivers (vehicle FDCAN1, platform FDCAN2, A-5), takes over microSD logging (D-045) and republishes the vehicle signals on the platform bus (D-056).
