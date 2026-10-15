# Vehicle data catalog — every signal we read, can read, or can derive

Working list (2026-10-15), **not a decision**. It collects what the platform reads today, what it could read, and what can be derived, so the anomaly and context models can pick features (D-068). The sources of truth stay where they are: `uds/vehicle_cl250.yaml` (ECU DIDs), `ble/ble_schema.json` (conn BLE), `dbc/platform.dbc`, `uds/dids.yaml`. Nothing here is polled, sent or computed because it is listed; each new item goes through `/signal-change` or a D-xxx.

Status legend:

| Tag | Meaning |
|---|---|
| **LIVE** | Read and recorded today (conn Phase 0 build, verified DID or sensor) |
| **POLLED?** | Polled since D-068, `verified: false`: flows only if the CL250 ECU serves it |
| **DEF** | Standard, but needs a decode definition before it can be polled |
| **DISC** | Exists only if discovery finds it (proprietary DID, passive CAN broadcast, Q-001) |
| **HW** | Needs a sensor or a wiring tap (hardware decision) |
| **PLAN** | Planned on a node that does not run yet (rt-core board, Q-019) |
| **DERIV** | Computed from the above (offline, server or rt-core) |

## 1. Vehicle bus load today

The vehicle bus (the CL250 DLC: classic CAN 500 kbps; rt-core's FDCAN1 once the board exists, conn's TWAI today) carries only our tester's requests and the ECU's answers. Per DID read: a request on the 29-bit and on the 11-bit ID, one 29-bit answer (8-byte frames, ~131/111 bits, ~155/134 with worst-case stuffing); tester present every 1000 ms.

| Table | Reads/s | Data bytes/s | Bus load (nominal / worst stuffing) | ECU slot budget (D-029, ≤ 0.8) |
|---|---|---|---|---|
| Before D-068 (5 DIDs) | 25.7 | 36 | 9.8 kbit/s = 2.0 % / 2.3 % | 0.514 |
| D-068, all 40 served | 36.8 | 51 | 14.0 kbit/s = 2.8 % / 3.3 % | 0.736 |

The limit is not the bus but the ECU: one request in flight and an assumed 20 ms round trip (provisional, D-029; measured by D-058's round-trip records). Unserved D-068 DIDs stop after their first reads (D-068 item 2), so the real load is lower.

Sampling rates of the verified DIDs: engine speed and vehicle speed 9.1 Hz (110 ms), throttle 5 Hz, coolant and battery 1.25 Hz.

## 2. ECU data over UDS (`uds/vehicle_cl250.yaml`)

Engine column: **run** = meaningful only with the engine running (key-on engine-off reads 0 or a fixed value, or the ECU may refuse it); **key** = meaningful at key-on too. These are expectations from J1979 practice, not CL250 facts; V0 (key on) and V1 (idle) in `hardware-integration.md` will show it. Caveat: under D-068 item 2 a DID refused or ignored at key-on stays stopped until the next session confirmation; re-asking stopped DIDs once at engine start is proposed (conn branch `claude/d068-engine-rearm`, needs a D-068 amendment).

| Signal | DID | Unit | Period | Status | Engine |
|---|---|---|---|---|---|
| Engine speed | F40C | rpm | 110 ms | LIVE | run |
| Vehicle speed | F40D | km/h | 110 ms | LIVE | key |
| Throttle position | F411 | % | 200 ms | LIVE | key |
| Coolant temperature | F405 | °C | 800 ms | LIVE | key |
| Control module voltage | F442 | V | 800 ms | LIVE | key |
| Calculated load | F404 | % | 2 s | POLLED? | run |
| Ignition timing advance | F40E | deg | 2 s | POLLED? | run |
| Absolute load | F443 | % | 2 s | POLLED? | run |
| Relative throttle | F445 | % | 2 s | POLLED? | key |
| Throttle B | F447 | % | 2 s | POLLED? | key |
| Grip position D | F449 | % | 2 s | POLLED? | key |
| Commanded throttle | F44C | % | 2 s | POLLED? | key |
| Relative grip | F45A | % | 2 s | POLLED? | key |
| Intake MAP | F40B | kPa | 2 s | POLLED? | key (≈ baro engine off) |
| Mass air flow | F410 | g/s | 2 s | POLLED? | run |
| Commanded lambda | F444 | ratio | 2 s | POLLED? | run |
| Short-term fuel trim | F406 | % | 2 s | POLLED? | run (closed loop only) |
| Injection timing | F45D | deg | 2 s | POLLED? | run |
| Engine fuel rate | F45E | L/h | 2 s | POLLED? | run |
| Demanded torque | F461 | % | 2 s | POLLED? | run |
| Actual torque | F462 | % | 2 s | POLLED? | run |
| Barometric pressure | F433 | kPa | 5 s | POLLED? | key |
| Long-term fuel trim | F407 | % | 5 s | POLLED? | run (learnt value) |
| Fuel pressure | F40A | kPa | 5 s | POLLED? | run |
| Rail pressure (relative) | F422 | kPa | 5 s | POLLED? | run |
| Rail pressure (gauge) | F423 | kPa | 5 s | POLLED? | run |
| EVAP purge | F42E | % | 5 s | POLLED? | run |
| Fuel level | F42F | % | 5 s | POLLED? | key |
| Ethanol | F452 | % | 5 s | POLLED? | key |
| Intake air temperature | F40F | °C | 5 s | POLLED? | key |
| Catalyst temperature | F43C | °C | 5 s | POLLED? | run |
| Ambient air temperature | F446 | °C | 5 s | POLLED? | key |
| Engine oil temperature | F45C | °C | 5 s | POLLED? | key |
| Run time since start | F41F | s | 10 s | POLLED? | run |
| Distance with MIL | F421 | km | 10 s | POLLED? | key |
| Warm-ups since clear | F430 | count | 10 s | POLLED? | key |
| Distance since clear | F431 | km | 10 s | POLLED? | key |
| Time with MIL | F44D | min | 10 s | POLLED? | key |
| Time since clear | F44E | min | 10 s | POLLED? | key |
| Reference torque | F463 | Nm | 10 s | POLLED? | key |

Standard but not yet defined (**DEF**, multi-value or enum, D-068 "Still open"): 0x01 monitor status (MIL, DTC count, readiness), 0x03 fuel system status (open/closed loop: tells when trims are valid), 0x12 secondary air, 0x13/0x1D O2 sensor location, 0x14–0x1B O2 voltage + trim, 0x24–0x2B / 0x34–0x3B wide-band O2 (lambda + voltage/current), 0x1C OBD standard, 0x1E auxiliary input (PTO), 0x51 fuel type. The CL250 has one cylinder and likely one O2 sensor, so 0x01, 0x03 and one O2 PID matter most.

One-shot data (D-059 probe scan, not a time series): supported-PID bitmaps, VIN (masked to the WMI, never published), CalID, CVN, ECU name, DTC count and list.

## 3. Switches and chassis data the ECU may or may not have

None of these is defined anywhere yet. J1979 has no PID for them.

| Signal | Likely source on the CL250 | Paths to get it | Status |
|---|---|---|---|
| Clutch lever switch | Start/ignition interlock circuit; on Honda PGM-FI the ECU usually reads it (to verify) | (a) proprietary Honda DID found by strategy stage 2: read candidate DIDs while pulling the lever; (b) passive broadcast if any (Q-001); (c) wiring tap, optocoupler, high-impedance, parallel to the switch | DISC / HW |
| Neutral switch | Same interlock; dash neutral lamp | (a), (b), (c) as above | DISC / HW |
| Side stand switch | Same interlock (ignition cut in gear) | (a), (b), (c) | DISC / HW |
| Gear position | A gear position sensor only if the bike has one (to verify) | (a) proprietary DID; else **DERIV** from RPM/speed ratio (§5) | DISC / DERIV |
| Front/rear brake switch | Brake-light circuit (12 V when braking); ABS unit | (b) ABS broadcast if any; (c) tap the brake-light feed (easiest, 12 V, opto-isolated input); **DERIV** braking from IMU deceleration (§5) | DISC / HW / DERIV |
| Wheel speeds (front/rear) | ABS modulator wheel sensors | (b) only if the ABS unit broadcasts on the DLC bus (Q-001); its own diagnostics are a second ECU, not in our tester policy | DISC |
| ABS active / intervention | ABS unit | (b) | DISC |
| Kill switch, engine stop | Interlock / ECU | (a), (c) | DISC / HW |
| Turn signals, lights | Lighting circuit | (c); planned io-node input for blind spot (hardware-architecture §5b.1) | HW / PLAN |
| Horn, high beam | Lighting circuit | (c) | HW |

Notes:
- (a) means new read-only discovery of non-standard DIDs (0x22 only, so inside `tester_policy`), but a range scan is a new probe mode: it needs a D-xxx (budget, which ranges, stop rules) before it is coded. The strategy note's 0x1000–0x2FFF range is an example, not a known range.
- (b) is the Q-001 listen-only capture (`esp32-s3-devkitc-1-listen-only`, `hardware-integration.md` §7.1). It costs nothing on the bus; do it first.
- (c) never cuts the OEM harness (vehicle-work-plan: parallel or via connectors). A tap is a hardware decision (which node reads it: io-node per §5b.1, or conn in Phase 0) and must not load the switch circuit.

## 4. Node sensors and platform data

| Signal | Source | Rate | Status |
|---|---|---|---|
| Acceleration ax/ay/az (±8 g), rotation gx/gy/gz (±500 dps) | conn MPU-6050 (D-032), BLE IMU block | 100 Hz | LIVE (offline analysis only, not a safety input) |
| GPS ground speed, heading, their accuracies, fix type, satellites | conn NEO-M8N NAV-PVT (D-060), BLE GPS block | 10 Hz | LIVE (never a position, invariant 7) |
| CAN health: bus state, TX/RX error counters, bus-offs, unanswered DIDs, latch flags | conn telemetry v4 | 10 Hz | LIVE |
| Tester stats: step gap max/over count, per-DID round trip min/max/sum/count, NRC 0x78 count | conn telemetry v4 (D-058) | rotating | LIVE |
| Per-DID state (valid/stale/skipped/NRC) and age | conn vehicle-signal block (D-066) | 5 Hz per page | LIVE |
| Session metadata: rider weight, load, ambient, weather, tyre pressures, fuel level, condition, route type | moto-mobile `meta.json`, hand-entered | per ride | LIVE |
| Chassis IMU (LSM6DSO/BMI270 class) for the EKF | rt-core (D-044, D-065) | 100–200 Hz to EKF | PLAN |
| Engine-block accelerometer (vibration) | rt-core (D-044, Q-025) | ≥ 1 kHz | PLAN |
| Safety-node fallback IMU | safety-node (D-042) | ~1 kHz | PLAN |
| Lean angle, its state and quality | rt-core EKF, 0x020 (D-065) | 50 Hz | PLAN (code in SIL) |
| Friction coefficient, total mass | rt-core, 0x022 | 10 Hz | PLAN |
| Node heartbeats (mode, error count, uptime) | every node, 0x081–0x085 | 10 Hz | PLAN |
| rt-core health 0xFD02, lean health 0xFD03 | rt-core UDS (D-055, D-067) | on request | PLAN |
| Microphone / acoustic, thermal | anomaly model inputs (hardware-architecture §5b.9) | — | PLAN / HW |
| Phone sensors (phone IMU, phone GPS) | not recorded by moto-mobile today | — | possible, not planned |

## 5. Derived signals (DERIV)

Computed offline (moto-ml / moto-server) first; anything safety-related only on rt-core per its decisions. Inputs refer to §2–4.

| Derived signal | From | How | Use |
|---|---|---|---|
| Longitudinal acceleration, jerk | vehicle speed, GPS speed, IMU ax | d(speed)/dt, filtered; cross-check with IMU | braking/accel events, aggressiveness (F9) |
| Distance, trip time, idle time, stops | speed | ∫speed dt; speed = 0 and RPM > 0 | usage profile, context |
| Gear estimate | RPM, speed, gear ratios + wheel radius (vehicle-work-plan §2) | RPM / speed ratio matched to the nearest gear | F4, shift events |
| Clutch disengaged / slipping | RPM, speed, gear estimate, throttle | ratio matches no gear while moving; ratio drift under load = slip | clutch anomaly (strategy note) |
| Neutral / coasting | RPM, speed, throttle | moving, ratio undefined, throttle closed | context |
| Shift events and shift time | RPM, speed | RPM step with continuous speed | riding style |
| Braking events, deceleration peak | speed derivative, IMU ax | threshold on decel; stand-in for the brake switch | context, anomaly |
| Speedometer error / effective tyre radius | ECU speed vs GPS speed | ratio at steady speed, good fix | calibration, tyre wear |
| Wheel slip (approx.) | ECU speed vs GPS speed (vs wheel speeds if found) | relative difference under accel/brake | R8 |
| Yaw rate, lateral acceleration, turn radius | IMU gz, speed, GPS heading rate | a_lat ≈ v·ω, r = v/ω | cornering context, lean cross-check |
| Pitch events (wheelie/stoppie), road roughness | IMU gy, az | pitch-rate peaks; RMS of az in bands | context (road type), anomaly |
| Engine vibration features | IMU (later engine accelerometer), RPM | RMS, crest factor, order spectrum vs RPM | anomaly (D-044) |
| Engine torque estimate | actual torque %, reference torque | Nm = % × reference / 100 | dyno, load |
| Engine power estimate | torque, RPM; or virtual dyno | P = T·ω; or m·a·v + drag + rolling (§5b.10) | F3 |
| Air–fuel ratio | commanded lambda | AFR ≈ λ × 14.7 (gasoline) | fueling anomaly |
| Fuel consumption, L/100 km, range | fuel rate, or MAF and lambda; speed; fuel level | MAF/(AFR·ρ_fuel); per distance | F5 |
| Volumetric efficiency (approx.) | MAP, RPM, IAT, displacement | speed-density | intake/valve anomaly |
| Fuel-trim drift | STFT, LTFT over rides | trend of LTFT; STFT variance | fueling, O2 sensor ageing |
| Throttle–torque response lag | throttle, actual torque %, RPM | cross-correlation lag | drivability anomaly |
| Warm-up curve, thermal rate | coolant, oil, IAT, ambient, run time | dT/dt, time to operating temperature | cooling anomaly |
| Heat soak | IAT − ambient at low speed | difference vs speed | context, anomaly |
| Charging health | battery voltage vs RPM | regulated voltage plateau, ripple, dip at crank | rectifier/regulator anomaly |
| Cranking dip | battery voltage, RPM 0 → > 0 | minimum voltage during start | battery health |
| ECU/bus health trends | CAN errors, NRC counts, round trips | rates per ride | data-quality flag for the models |
| Data quality per sample | ages, states, valid flags | stale/never/NRC masks | feature masking in training |

## 6. What to do next to grow the data set

1. Ride with conn on defs v0.12.0: the vehicle-signal block shows which D-068 DIDs the CL250 serves (LIVE vs NRC 0x31 vs skipped) at key-on and after the engine start.
2. Q-001 listen-only capture at key-on and while riding: any broadcast frame (ABS, dash) is a free source of wheel speeds, brake or gear.
3. Define the DEF PIDs that matter for one cylinder: 0x01, 0x03 and the O2 sensor the bitmap reports.
4. Decide (D-xxx) on proprietary-DID discovery (strategy stage 2) and/or switch taps (§3), with `architecture-guard` (which node) and `safety-reviewer` (tester or wiring).
5. Tune the D-068 tiers from the first rides: faster for the DIDs that carry information, drop the dead ones.
