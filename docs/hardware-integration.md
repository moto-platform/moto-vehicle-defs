# Hardware integration — Phase 0 data-collection build (CL250)

**Status:** working guide, started 2026-10-03; parts on hand and the phone-only display recorded 2026-10-11 (user). **Scope:** the first on-vehicle build that collects data with the code that exists today. It does not change any decision. Authority: `DECISIONS.md` > `ARCHITECTURE.md` > `vehicle-work-plan.md` / `phase0-data-collection-plan.md` > this file. Items marked **CONFIRM** are not documented anywhere yet. Fill them in from the bike or the parts on the desk; never guess them.

## 1. What this build is

- **Node:** `moto-connectivity-node` on an ESP32-S3 DevKitC-1. Until rt-core runs on the bike, it is the **temporary sole vehicle-bus tester** (D-021, D-023, D-037).
- **Path:** CL250 ECU → DLC Y-cable → CAN transceiver → ESP32-S3 TWAI → BLE → phone (`moto-mobile`) → session zip → `moto-server` (D-032).
- **No on-vehicle storage:** conn keeps no local copy. Data lost while the phone is disconnected is accepted, and the server report shows the gaps (D-045). Persistent logging (microSD, safe shutdown) is rt-core's job later, so the Phase 0 plan's microSD and supercapacitor items are not part of this build.
- **IMU:** an MPU-6050-class IMU on the same ESP32 at 100 Hz, streamed over BLE. It is for offline analysis only: it is not a vehicle signal, not a safety input, and no lean is estimated from it (D-032, D-044).
- **Display:** the phone (`moto-mobile`) is the only live telemetry view in this build. The Nextion stays unconnected for now (user, 2026-10-11) and comes back in a later prototype; `NextionModule` with nothing on UART2 is harmless.
- **Not in this build:** rt-core (STM32H755 M7, D-072), the platform bus, the M4 safety partition (io-node retired, D-072), Raspi, the Nextion (for now). GPS joins it per D-060 (see §9).

```
 CL250 DLC ──Y-cable (CANH, CANL, GND; < 50 cm, twisted)──┐
                                                          │
 12 V ignition-switched ─ fuse 2 A ─ reverse-polarity ─ TVS ─ LC ─ buck 6-40 V → 5 V
                                                          │            │
                                              ┌───────────┴────────────┴───────────┐
                                              │ SN65HVD230 ── GPIO4 TX / GPIO5 RX  │
                                              │ ESP32-S3 DevKitC-1 (conn firmware) │
                                              │ MPU-6500 ── I2C GPIO7 SDA / GPIO6 SCL (0x68, 400 kHz)
                                              │ NEO-M8N ── UART1: module TX → GPIO15 / module RX ← GPIO16 (pins CONFIRM, §7.3)
                                              │ Nextion (later, unconnected now) ── UART2 GPIO17 TX / GPIO18 RX
                                              └──────────────┬─────────────────────┘
                                                             │ BLE "Honda-CL250-Telemetry"
                                                    phone: moto-mobile ── session zip ──► moto-server (laptop)
```

## 2. Parts list for this build

Sources: `phase0-data-collection-plan.md` §9, `hardware-procurement-list.md` (groups 1-3, 10, "Already On Hand"), `vehicle-work-plan.md` §3. On hand as of 2026-10-11 (user): ESP32-S3, MPU-6050, SN65HVD230, NEO-M8N; everything else is still to be bought or confirmed. Desk bring-up 2026-10-15: the board and the working IMU are recorded in the rows below.

| Part | Spec | Role | On hand |
|---|---|---|---|
| ESP32-S3 DevKitC-1 | WROOM module | conn firmware | **on hand**: ESP32-S3 rev v0.2, 16 MB flash, 8 MB embedded PSRAM, FTDI FT232R USB-UART (shows as `/dev/cu.usbserial-*`), flashes and boots with the DevKitC-1 envs (2026-10-15). GPIOs used: 4, 5, 6, 7, 8, 15, 16 |
| CAN transceiver | SN65HVD230 (3.3 V) | TWAI ↔ vehicle CAN | **on hand**; **CONFIRM** whether the breakout carries a 120 Ω termination resistor: it must be removed or left open, since the vehicle line is already terminated (§3.1) |
| IMU | MPU-6050 class, must deliver ±8 g / ±500 dps at 100 Hz (D-032) | raw motion data | **on hand**: the working part is an MPU-6500 (WHO_AM_I 0x70, accepted by conn; ±8 g / ±500 dps meet D-032; the part stays provisional). The first module (MPU-6050 class) gave no I2C answer on the desk |
| GPS | u-blox NEO-M8N, 3.3 V logic on its UART, own antenna (D-060) | ground speed, heading | **on hand** |
| DLC Y-cable | Parallel to the OEM connector, no cut | bus access | **CONFIRM** connector type |
| Fuse + holder | 2 A, blade or glass | input protection | **CONFIRM** |
| Reverse-polarity protection | Series Schottky or P-MOSFET | input protection | **CONFIRM** |
| TVS diode | Bidirectional, 24-30 V clamp | load-dump / transients | **CONFIRM** |
| Buck converter | Wide input 6-40 V → 5 V, 2-3 A | supply | **CONFIRM** |
| Input filter | Electrolytic + ceramic, LC | EMC | **CONFIRM** |
| INA226 (optional) | Current/voltage monitor | sleep-current check (§7) | **CONFIRM**, or use a multimeter |
| Enclosure | ABS or aluminium, ≥ IP54, < 100 × 70 × 30 mm target | protection | **CONFIRM** |
| Connectors, glands, wrap | Locking connector (one detachable plug), PG7 glands, spiral wrap | assembly | **CONFIRM** |
| Nextion display | UART2 | local display | on hand, **not used in this build** (later prototype) |
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

### 3.3 IMU, display and GPS wiring

- IMU on I2C: SDA `GPIO7`, SCL `GPIO6`, address `0x68` (AD0 to GND), 400 kHz (conn#19; the legacy port used GPIO1/2). GPIO4/5 stay with CAN. Keep the I2C wires short, inside the enclosure, and solder the module's header: a header only pushed into the jumpers lost contact on the desk (2026-10-15).
- Nextion (later, unconnected in this build): UART2 TX `GPIO17`, RX `GPIO18`, 115200 8N1.
- `GPIO8` pulses high for each `loop()` pass (scope probe for the step time, §6).
- GPS (D-060): NEO-M8N on UART1, module TX → `GPIO15` (conn RX), module RX → `GPIO16` (conn TX), common GND. **CONFIRM**: candidate pins of the `esp32-s3-devkitc-1-gps` env, confirmed by the procedure in §7.3. The module's UART must be 3.3 V logic.

### 3.4 Chassis sensor harness: twisted-pair rules, shield grounding, insulation & modular split-mezzanine layout

To suppress magnetic induction ($\mathcal{E} = -d\Phi_B/dt$ from the ignition coil/HT lead, regulator/rectifier, and starter cable) and capacitive cross-talk on every sensor run between the motorcycle frame and the `NUCLEO-H755ZI-Q` box:

| Signal Class | Examples on Bike | Twisting Rule (`~30–40 twists/m`) | Shielding & Termination Rule |
|---|---|---|---|
| **Differential Bus** | Vehicle CAN (`CAN_H / CAN_L`), Platform CAN | Twist `CAN_H + CAN_L` tightly together (`120 Ω` only at Platform CAN physical ends; **never** on the `< 50 cm` DLC stub) | Unshielded automotive twisted pair (`FLRY-B 0.35–0.50 mm²`) is sufficient |
| **Single-Ended High-Speed Digital (`SPI / I2C / UART / WS2812B`)** | `ADXL345 ×2` (SPI/I2C), `MAX31856` (SPI), `MLX90614 / VL53L1X / AS5600 / BME280` (I2C), `INMP441` (I2S), `HLK-LD2451 ×2` (UART), `WS2812B` (800 kHz) | **NEVER twist `SCL + SDA`, `SCK + MOSI`, or `TX + RX` with each other** (causes capacitive cross-talk). Instead, twist **`Signal + GND` as Pair 1** and **`VCC + GND` as Pair 2** | Use **`LiYCY 4×0.22 mm²` tinned-copper braided shielded cable**. Connect the braid shield to **`GND` at the `H755` enclosure side ONLY (single-ended drain)** and leave the sensor-side shield floating/insulated (prevents chassis ground loops). Add **`2.2–4.7 kΩ` external I2C pull-ups to `3.3V`** on Board B (`10 kΩ` onboard pull-ups are too weak for `> 30 cm` shielded cable capacitance) |
| **Low-Level Analog / Differential (`mV` / Thermocouple / NTC / Hall)** | `K-type EGT` (`µV/°C`), `M12×1.5 Sump NTC`, `10K Radiator NTC`, `ACS758` (`Analog Out`) | Twist `Signal + Signal_Return (AGND)` tightly; keep the `MAX31856` cold-junction amplifier close to the K-type stainless braid exit | Keep **`> 15 cm` away from the ignition coil and spark-plug HT lead**; clamp **`5–7 mm` snap-on ferrite cores** on the engine-bay `ADXL345`, `EGT`, and `Inductive Spark Clip` cables right before the `PG7` enclosure entry |

- **Flexible Harness Insulation (Never Full-Length Heat-Shrink):** Do **not** encase long chassis cable runs in full-length heat-shrink tubing (`makaron`); cured heat-shrink becomes stiff, transfers frame vibration directly into solder joints, and traps condensation. Instead:
  1. Use **`3–4 cm` adhesive-lined heat-shrink (`3:1`) ONLY at connector backs, solder splices, shield terminations, and `PG7` gland entries** as strain relief.
  2. Wrap the twisted pairs along their length with **`Tesa 51608` automotive fleece/cloth harness tape (`bez bant`)** (`50%` overlap), which stays flexible, damps rattle, and resists `105–150 °C`.
  3. Add **PE spiral wrap** or split corrugated loom (`6–8 mm`) only over high-abrasion pinch zones (headstock steering pivot, swingarm pivot, frame pass-throughs).
- **Modular 3-Board Split-Mezzanine Perfboard Architecture (Inside the `170 × 120 × 55 mm` H755 Box):** Never solder all subsystems onto a single monolithic `9×15 cm` perfboard (which mixes `12V` power transient return currents with analog `AGND` and precludes `Scale 1A` vs. `Scale 1B` hardware separation). Build the 2nd story (`M3 × 18–20 mm` hex standoffs over the `NUCLEO-H755ZI-Q`) as **three independent, side-by-side double-sided epoxy perfboards**:
  1. **Board A (`5 × 7 cm` — Core Power, Dual CAN & `Scale 1A` Base):** `12V → 5V` Buck + `SMBJ24CA` TVS + reverse-polarity P-MOSFET + `SN65HVD230 ×2` (`FDCAN1 / FDCAN2`) + `1 kHz` Battery Voltage ADC divider + `INA226 #1` + `MicroSD SPI`. Required by all tiers (`Scale 1A`).
  2. **Board B (`7 × 9 cm` — `Scale 1B` External Anomaly Sensor Conditioner Mezzanine):** `PC817` 4-Ch Optocoupler (`Clutch / Brake / Fan 12V`), `MAX31856` EGT, `NTC` RC dividers (`10 kΩ 0.1% + 100 nF`), `Inductive Spark Clip` Schmitt input (`10 kΩ + BAT54S`), `2.2–4.7 kΩ` external I2C pull-ups, and the single detachable `Scale 1B Expansion Port` headers. Unplugging Board B cleanly reverts the hardware to `Scale 1A`.
  3. **Board C (`4 × 6 cm` — `M4` Safety Partition & Rigid Dual-IMU Carrier):** `MPU-6500` (`M4` SPI IMU) + `MPU-6590` (`M7` I2C IMU) + `74AHCT125` 5V Cornering LED buffer + `HLK-LD2451 ×2` radar UART headers + Immobilizer driver. Can sit either on rigid `6 mm` brass standoffs directly on the enclosure base or inside its own dedicated **`DT-0505` (`65 × 50 × 35 mm`) rigid frame-mounted CG IMU box** (`< 30 cm` `LiYCY` shielded SPI/I2C link to the main box).

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

### 4.1 Placement on the CL250 for the H755 + Pi 5 build (Q-034, expanded candidate analysis)

The under-seat rule above came from the ESP32-only build. The user found no free space under the seat above the battery (2026-10-18), and the Wave 1/Wave 5 enclosures (`170 × 120 × 55 mm` for `NUCLEO-H755ZI-Q` and `170 × 120 × 55 mm` for `Raspberry Pi 5`) require dedicated exterior or frame-mounted volumes.

**OEM (`Bosch MSC / Ducati / BMW`) & Motorsport (`AiM EVO4S / MoTeC / 2D`) Golden Rule — Decouple `Board C (IMU)` from the Controller Boxes:**
In production motorcycles and race telemetry, the **6-axis IMU (`Board C: 4 × 6 cm` inside a compact `DT-0505` `65 × 50 × 35 mm` box)** is **always separated** from the bulky data-logger/ECU boxes. Putting `Board C` on rigid `6 mm` brass standoffs bolted directly to the **main steel diamond frame spine near the Center of Gravity (CG)** (between the rear of the fuel tank and the front of the seat on the CL250, `< 30 cm` shielded SPI run) frees the large `170 × 120 × 55 mm` `H755` and `Pi 5` enclosures to sit on soft silicone vibration dampers in any cool, accessible location on the bike.

Candidates evaluated across heat, vibration, EMI, DLC `< 50 cm` stub compliance, and tyre/suspension clearance (`Q-034` until the user decides):

| Candidate | Heat (`≥ 15 cm` rule) | Vibration & Clearance | Noise & Cable Routing | Verdict |
|---|---|---|---|---|
| **(a) Around the engine block** | Fails: cylinder, head and exhaust header | Strongest on the bike (combustion, crank) | Next to the ignition coil and plug lead | **Rejected for boxes.** Only the `D-044` engine `ADXL345` (`DT-0505` / `1590A`) belongs here |
| **(b) E-Clutch unit's place (right clutch cover)** | Fails: directly on the hot right crankcase cover near the upswept exhaust | Direct engine primary vibration | Near ignition & stator leads | **Rejected** for the same reasons as (a) |
| **(c) Rear subframe under-fender tray** | Good on the left; CL250 upswept muffler is on the right (**CONFIRM** distance) | Moderate; **must verify `150 mm` rear wheel travel at full bottoming** | Farthest from ignition; `< 50 cm` to under-seat DLC | **Recommended (stealth baseline)** with tire-clearance check & rules below |
| **(d) Left-side pannier carrier plate (`SW-Motech SLC` / `Longride` factory M8 fender bolts, `~127 mm` spacing)** | **Excellent:** opposite side of the bike from the right upswept exhaust (`> 35 cm`), open cooling airflow | Rigid factory `M8` subframe bosses rated for `5–10 kg` luggage; **zero rear-wheel bottoming or mud-spray risk** | **`~30–45 cm` direct run to under-seat DLC & battery**; eye-level `ST-LINK` / microSD access | **Top Recommendation #1 (Best Engineering & Thermal Balance for `H755` + `Pi 5`)** |
| **(e) Pillion seat / `23 × 23 cm` rear luggage rack plate (Academic & Track-Day standard)** | **Excellent:** completely away from engine and exhaust, full ambient airflow | Low; damped on flat `230 × 230 mm` top rack plate or tail-bag base; zero tire contact risk | `~40–50 cm` to under-seat DLC; unobstructed sky view for `GPS`, `BLE` & `Wi-Fi` | **Top Recommendation #2 (Fastest Zero-Modification Prototype Mount)** |
| **(f) Left tubular crash-bar (`koruma demiri`) / front left frame downtube** | **Good on left side:** frontal cold airflow keeps `Pi 5` cool (exhaust header curves right; verify `≥ 15 cm` clearance) | Higher frame vibration than rear (requires `M4/M5` rubber bobbin isolators) | **Too far (`> 70 cm`) for the `H755` `< 50 cm` DLC stub**, but **ideal for `Raspberry Pi 5` (`Platform CAN` has `120 Ω` termination and no `< 50 cm` limit)** or a Front Sensor Hub | **Recommended for Split Architecture (`Pi 5` or Front Hub in front, `H755` at rear/left)** |
| **(g) Behind headlight / scrambler number-plate cowl (MotoGP / WSBK nose-box practice)** | **Excellent:** completely isolated from engine/exhaust heat | Steering-head inertia (keep weight `< 400 g`; unsuitable for dual `170×120×55` boxes) | **Ideal for compact `DT-0508` (`83×58×33 mm`) Front Hub (`ESP32-S3`, `IMX462 Camera`, `PN532 NFC`, `BME280`, `Cornering LEDs`)** | **Recommended for Front Satellite Modules (`Part 1B / 3B`)** |
| **(h) Behind left side number-plate cover (factory document-pouch cavity)** | **Good:** shielded plastic side panel on the cool left side | Protected inside the main frame triangle right next to battery/DLC | Too shallow (`< 45 mm`) for the `170×120×55 mm` box, but **ideal for `Board C` Rigid CG IMU (`DT-0505`), `ACS758`, or `Immobilizer Relay` (`DT-0508`)** | **Recommended for `Board C` Rigid CG IMU & Battery/Starter Tap Boxes** |

Rules across candidates `(c)`, `(d)`, `(e)`, `(f)`, `(g)`, and `(h)`:
- **Recommended Dual-Box Split on the CL250:**
  - **Option 1 (Left-Flank Carrier Plate `(d)`):** Bolt a `3–4 mm` aluminum mounting plate (or lockable hard ABS side case) to the CL250's **two factory left-side `M8` fender/pannier bosses (`~127 mm` pitch)**. Mount both the `170 × 120 × 55 mm` `NUCLEO-H755ZI-Q` box and the `170 × 120 × 55 mm` `Raspberry Pi 5` box side-by-side on silicone dampers with `PG7` glands pointing down. This keeps the DLC stub `< 40 cm`, eliminates rear-tire bottoming risk, and places `Pi 5` in cool left-side airflow opposite the right exhaust.
  - **Option 2 (Rear Rack `(e)` or Subframe Tray `(c)` + Left Crash-Bar `(f)` Split):** Mount the `H755` box on the rear subframe tray `(c)` or left pannier plate `(d)` (`< 50 cm` to DLC) and mount the `Raspberry Pi 5` box on the **left crash bar `(f)` or rear luggage rack `(e)`** over the terminated `120 Ω` `Platform CAN` bus (`FDCAN2`), which has no `50 cm` stub restriction and shortens the `CSI-2` / USB camera lead to the front headlight.
- **IMUs (`Board C`) never on a damped tray, pannier plate, or cantilevered rack:** The chassis IMU (`M7` `MPU-6590`) and the `M4`'s own IMU (`D-042`, `Q-023` `MPU-6500`) sit on **`Board C` (`4 × 6 cm`) inside a dedicated `DT-0505` (`65 × 50 × 35 mm`) enclosure bolted with rigid `6 mm` brass standoffs to the main steel frame spine near the Center of Mass** (under the front of the seat / behind the left side cover `(h)`), aligned with the bike's axes. Reason: a gyro sees the same angular rate anywhere on a rigid body, but an accelerometer at an offset $r$ also sees $\omega \times (\omega \times r) + \alpha \times r$, and a bracket that flexes adds its own resonance. Record the offset $r$ and the axis directions in the session metadata (§9). The `M4` IMU's `LiYCY` shielded SPI run stays short (`≤ ~30 cm`, single-ended shield drain to `H755` GND).
- **Vehicle CAN stub:** The DLC Y-cable is an unterminated stub on the vehicle bus; its `< 50 cm` limit (§3.1) stays. Because the CL250 DLC is under the seat near the battery (**CONFIRM**, §10 item 1), candidates `(c)`, `(d)`, `(e)`, and `(h)` all stay within `< 35–50 cm`; measure before building. Never add termination to extend it.
- **Platform CAN** (`H755 FDCAN2` ↔ bike `ESP32-S3` and `Raspberry Pi 5`): a proper bus with `120 Ω` at both physical ends, so its length is not the limit (allows placing `ESP32-S3` behind the headlight `(g)` and `Pi 5` on the left crash-bar `(f)` or rear rack `(e)`).
- **Power:** The ignition-switched tap, fuse, reverse protection, TVS and LC filter sit at the box input (§3.2, `Board A`). The ground goes on its own wire straight to the battery negative (star point, no chassis return, no second ground path for the same unit).
- **Front-end lines** (LED rings beside the gauge, mirror LEDs): drive the `800 kHz` `WS2812B` data line through a 5 V buffer (`74AHCT125` class) with a `~330 Ω` series resistor, run it twisted with its ground (`Data + GND`), and leave steering slack through the headstock.
- **Rear-end lines:** both `HLK-LD2451` blind-spot radars (`DT-0508` boxes facing rear-left and rear-right), the `Q-033` indicator inputs (`D-075` item 4, opto-isolated on `Board B`) and the GPS antenna (on top under plastic, never under metal) sit close to `(c)/(d)/(e)`. The immobilizer relay (`DT-0508`) goes next to the starter relay (`(h)`, **CONFIRM**), coil circuit only (Invariant 6).
- **Noise sources to keep the boxes and cables away from:** ignition coil and plug lead (`≥ 15 cm`), regulator/rectifier, starter motor cable (high cranking current), fuel pump and injector wiring.

**Measure on the bike before Q-034 is decided** (photos + dimensions; never commit photos showing the plate or the location): free volume under the tail/rear fender and between the subframe rails `(c)`; spacing and thread depth of the left-side `M8` fender/pannier bosses `(d)`; cavity dimensions behind the left side cover `(h)`; muffler distance on both sides; DLC position and its cable path to `(c)/(d)/(e)`; battery, starter relay, fuse box and regulator/rectifier positions; a rigid steel frame point near the centre of mass for the `DT-0505` `Board C` IMU box.

## 5. Firmware and software setup

| Step | Command / action | Repo |
|---|---|---|
| Build + flash (real CAN) | `pio run -e esp32-s3-devkitc-1 -t upload` (needs `platformio_local.ini` with `AP_PASSWORD`) | moto-connectivity-node |
| GPS bring-up (until the pins are confirmed) | `pio run -e esp32-s3-devkitc-1-gps -t upload`, procedure in §7.3 | moto-connectivity-node |
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

Recommended first contact with the bike: the §7.1 listen-only capture, before V0. Its image never transmits, so it is the lowest-risk first connection and it answers Q-001 before the tester polls.

Road tests (T2, T3) come only after V3 passes, and the rules in §8 apply. T4 is out of scope for this build.

## 7. What to measure in the first sessions

| Measurement | Why | How with this build |
|---|---|---|
| Tester step gap | D-053 assumes `client_step_max_ms` = 10 ms; conn's step is unbounded (conn README) | D-058 item 2: the poller's step-gap max and over-10-ms count in BLE telemetry v4 (server report, §7.2); the G0.1 serial report still gives the per-module `loop()` durations; scope on `GPIO8` |
| ECU round trip | D-029, A-4 polling budget (assumed 20 ms) | D-058 item 1: per DID min/max/sum/count and 0x78 count, one rotating record per BLE telemetry v4 packet (server report, §7.2) |
| Passive broadcast traffic | Q-001 (VWP §5.5 step 1: 5 min listen-only) | D-058 item 4: flash the `esp32-s3-devkitc-1-listen-only` env (no TX at all), log USB serial for 5 min with the ignition on, then flash the tester env again (§7.1). Record the result on Q-001 |
| PID support, vehicle info, DTCs | A-4: MAP, fuel trim, wheel speed | D-059: flash the `esp32-s3-devkitc-1-probe` env once (0x01 bitmaps, 0x09, 0x19, 0x22 0xF4xx support DIDs, segmented answers with one FC.CTS); the serial output goes into defs with `/signal-change`, `verified: false`. Never commit the VIN |
| Sleep current | VWP §4.3, < 1 mA | Multimeter or INA226 in series, ignition off |
| Engine-on noise | VWP §4.2 | The same idle recording with the engine stopped and running; compare CAN error counters and IMU noise |
| IMU zero and axis offset | VWP §3.4, §5.4 | Upright on flat ground, then a known tilt (side stand) |
| BLE loss | D-045 | Server report: seq and tick gaps per session |
| GPS rate, BLE path and the step gap with GPS notify | D-060 item 2 (10 Hz; step gap measured with the GPS running), D-062, D-063 | §7.3: serial `[GPS]` report at the desk, a bonded phone session uploaded to the laptop, then the step gap on the bike |

### 7.1 Listen-only capture (Q-001, D-058 item 4)

Nothing else on the DLC (no scan tool, no tester build). From `moto-connectivity-node`, with `platformio_local.ini` in place:

```bash
pio run -e esp32-s3-devkitc-1-listen-only -t upload
# 921600 baud. Write the log outside every repo (D-033); stop it after the FINAL lines (300 s).
mkdir -p "$MOTO_DATA_DIR/captures"
pio device monitor -e esp32-s3-devkitc-1-listen-only | tee "$MOTO_DATA_DIR/captures/q001-$(date +%Y%m%d-%H%M).csv"
# afterwards, back to the tester:
pio run -e esp32-s3-devkitc-1 -t upload
```

Run it once with the ignition on and the engine off, and once idling. Line format (conn `src/CanCaptureCore.h`): `F,<t_us>,<id>,<S|X>,<dlc>,<data>` per frame; `S,…` per-ID rows (count, min/max period in ms, `W` = an OBD functional request ID, D-040) every 10 s; `S,END,…,frames=,ids=,overflow=,lost=,dropped=`; the same once as `FINAL,…` after 300 s.

| FINAL shows | Means | Record on Q-001 |
|---|---|---|
| `frames=0` | No passive broadcast on the DLC | "none found", with the date and ignition/engine state |
| Rows with a steady period | Broadcast frames: ID, DLC, period | IDs and periods; they go into `dbc/cl250.dbc` only through `/signal-change` |
| One frame repeated back to back | Its sender gets no ACK (conn never ACKs in listen-only): the ECU broadcasts with nobody else on the bus | The ID; a finding too (D-058 item 4) |
| A `W` row | Another tester is on the bus | Stop: remove it before any tester session (§8) |
| `lost` or `dropped` > 0 | The capture missed frames or serial lines | Repeat; note the counts |

The capture never transmits: no `twai_transmit` in its image, and the listen-only errata workaround keeps the controller error passive so it sends no error flag either (CI checks both). Still to verify on the bench: a CRC-corrupted frame from the HIL with a scope on the bus, and a 10-minute run without a watchdog reset.

### 7.2 Tester statistics (BLE telemetry v4, D-058 items 1-2)

Record a normal session with the tester env (V0/V1), upload or import it, then:

```bash
uv run moto-server report <session_id>
```

`tester_stats` in the report:
- `step_gap_max_ms`, `step_gap_over_count`: since-boot maximum gap between two poller steps and the count of gaps above `client_step_max_ms` (10 ms). A count above 0 means the D-053 assumption does not hold for conn; compare with the G0.1 serial report to find the slow module.
- `rtt["0xXXXX"]`: per DID `min_ms`, `max_ms`, `avg_ms`, `count`, `nrc78_count`, from the last record seen for that DID. One step is included in every sample. Requests answered after 0x78, and requests sent within `response_timeout_max_ms` (2 s) after a timeout, give no sample. Compare `max_ms` with `assumed_round_trip_ms` (20 ms); a larger value changes the D-029 budget (A-4).

### 7.3 GPS bring-up and the step gap with GPS notify (D-060, D-062, D-063)

Steps 1-4 run at the desk (no bike). Step 5 turns the result into the pin confirmation, and step 6 runs on the bike with the build CI checks.

**1. Wiring.** As in §3.3: module TX → `GPIO15`, module RX → `GPIO16`, common GND, the module powered as its breakout board specifies (3.3 V logic on its UART). The antenna needs a clear sky view (outdoors or at a window); a cold start can take minutes to the first fix.

**2. Serial report.** With `CONN_GPS_PINS_CONFIRMED=0` the firmware never installs the UART, so set it to `1` in the `esp32-s3-devkitc-1-gps` env **in your local copy only**, then from `moto-connectivity-node`:

```bash
pio run -e esp32-s3-devkitc-1-gps -t upload
pio device monitor -e esp32-s3-devkitc-1-gps
# afterwards: git checkout platformio.ini   (the confirmed pins arrive through a PR, step 5)
```

conn first tries 38400 baud, then the factory 9600 with a CFG-PRT that moves the receiver to 38400, and configures UBX only with NAV-PVT at 10 Hz (RAM only; conn sends no CFG-GNSS, so the receiver's default GNSS set applies). Every 10 s it prints one line with the rate, fix and error counters only, never speed, heading or position:

`[GPS] link=<state> pvt/s=<rate> fix=<type> sv=<count> ck_err=<n> len_err=<n> ovf=<n> lost=<n>`

| Field | Pass | If not |
|---|---|---|
| `link` | `OK` | `PENDING`: not configured yet, wait. `NO_RECEIVER`: no valid UBX at 38400 or 9600; check TX/RX crossed, GND, supply. `(UART install failed)`: the driver did not install on these pins |
| `pvt/s` | `10.0` on every line for ≥ 5 min with `fix=3` | Record the value and `sv`: the receiver does not hold 10 Hz with its default GNSS set (D-060 item 2 asks for 10 Hz; VWP §3.5 needs ≥ 5 Hz). A decision, not a code fix |
| `fix` | `3` (3D) after the first fix | Stays `0`-`2`: sky view or antenna |
| `sv` | Record it | — |
| `ck_err`, `len_err` | `0` and not rising | Noise or a baud mismatch on the wires |
| `ovf` | `0` | The UART driver's buffer overflowed: the GPS task was starved |
| `lost` | `0` | The receiver went silent for 3 s; check power and the connector |

**3. Phone, bonding and the `gps` subscription (Android).** Install the moto-mobile APK (v0.2.0 or later) and connect to `Honda-CL250-Telemetry`. The app starts pairing on connect (Just Works, no passkey); telemetry and IMU work without it, the `gps` characteristic does not (D-062). Record a session of ≥ 5 min and check:
- the session has a non-empty `gps.csv` next to `telemetry.csv` and `imu.csv`;
- after a disconnect and reconnect, GPS rows arrive again: conn clears the subscription on every connect, so the app must subscribe again (D-062 item 1).

iOS: moto-mobile has no iOS project yet (§10 item 8).

**4. Upload to the laptop and the report.** On the laptop:

```bash
export MOTO_API_TOKEN=…        # same token in the app's Settings
uv run moto-server serve       # listens on 0.0.0.0:8000
ipconfig getifaddr en0         # the laptop's LAN IP (macOS, Wi-Fi)
scutil --get LocalHostName     # its mDNS name, add ".local"
```

In the app's Settings set the server URL to `http://<LAN IP>:8000` (or `http://<name>.local:8000` if the phone resolves it), phone and laptop on the same Wi-Fi; allow incoming connections if the macOS firewall asks. Then:
- upload the session; it must succeed (D-063 allows a private address or a `.local` name);
- set a non-local URL (for example `https://example.com`) and upload again: the app must refuse before any network call, naming D-063; set the local URL back;
- `uv run moto-server report <session_id>`. The GPS lines read `GPS: N block(s), L lost or MTU-skipped (p%), effective rate R Hz, usable for the speed check U%` and the fix types.

Pass: the effective rate matches the serial `pvt/s`; lost or MTU-skipped near 0 with the phone next to the unit; no decode error, parse error, UART overflow or app/server mismatch. Many lost or skipped blocks with a good serial rate mean radio loss or an MTU too small for the GPS block (the node advances `seq` for a block it skips, D-062 item 2).

**5. Confirm the pins.** Once steps 2-4 pass, the pins go into §3.3 without **CONFIRM**, conn sets `CONN_GPS_PINS_CONFIRMED=1`, GPS moves into the main tester env and the `-gps` env is removed (conn `platformio.ini` comment), each through a PR.

**6. Step gap with GPS notify on (bike).** D-060 item 2 measures the step gap of D-058 with the GPS running. With the main tester env from step 5 and the phone bonded and subscribed to `gps` for the whole session, record ≥ 5 min at V0 (ignition on, engine off) and at V1 (idling, closed area, §8). The baseline is a V0/V1 session under the same conditions with the tester env before step 5 (no GPS). Read `step_gap_max_ms` and `step_gap_over_count` in each report (§7.2): the difference is the cost of the GPS task and its notify. An over count above 0 is a measurement for D-053 and rt-core, recorded with the session conditions, not a reason to change the tester.

**What to record.** The pins used; `pvt/s`, `sv` and the fix time from step 2; the phone model and Android version, whether pairing, the reconnect and the D-063 refusal behaved as described; the report's GPS line; the step-gap pairs of step 6. Numbers only: `gps.csv`, sessions and screenshots never go into a repo or an issue (D-033, D-060 item 5).

## 8. Safety rules on the bike

- **One tester only, and it only reads** (D-037). Never connect a scan tool, another dongle or a second build while conn is on the DLC. conn latches off if it sees one, but the rule is to not let it happen.
- Nothing that writes, clears, resets, unlocks, controls or reprograms the ECU, ever (D-020). The gate enforces it; do not flash a firmware that bypasses it.
- First engine-on session in a closed area, engine idling (VWP §3.2).
- Check that recording works **before** riding, never while riding. Full protective gear; T4 limit tests only on a closed area with a second person (VWP §7, §12).
- The unit must not change how the bike behaves: power from the ignition-switched line, a 2 A fuse, the harness never cut, one plug to remove it.

## 9. Data handling

- **Session = one ride.** Files per `moto-mobile/docs/session-format.md`: `meta.json`, `telemetry.csv`, `events.csv`, `summary.json`, `imu.csv`, and `gps.csv` when the GPS block is subscribed.
- Fill the metadata of the Phase 0 plan §3.2 / VWP §6.2: ambient temperature and weather, tyre pressures, fuel level, rider weight and load, vehicle configuration, condition label (healthy / fault type), route type, notes. Add the unit and IMU mounting (§4).
- **Never commit ride data to any repo** (all repos are public, D-033). Sessions live under `$MOTO_DATA_DIR` on the server machine, with a second copy off the laptop.
- **GPS (D-060):** a u-blox NEO-M8N on a conn UART (UBX-NAV-PVT, 10 Hz; pins **CONFIRM**, §7.3). Only ground speed, heading, their accuracies, fix type and satellite count leave conn, on the BLE GPS block; latitude, longitude and height never do. The phone writes them to `gps.csv`, which goes to the server with the session. A speed + heading series can rebuild the route's shape, so sessions stay on your own machine and never in a repo; moto-mobile uploads a session with `gps.csv` only to a local server (D-063).

## 10. Open items (fill in, then move facts into the sections above)

| # | Item | Blocks |
|---|---|---|
| 1 | CL250 DLC location, connector type and pinout | §3.1, Y-cable |
| 2 | Parts actually on hand: ESP32-S3, MPU-6050, SN65HVD230 and NEO-M8N recorded (2026-10-11); board and IMU (MPU-6500) confirmed on the desk (2026-10-15); the the transceiver's termination resistor, the Y-cable, the power chain, the enclosure and the phone are still **CONFIRM** (§2) | Build start |
| 3 | Ignition-switched tap point on the CL250 harness | §3.2 |
| 4 | IMU bracket location and axis directions | §4, metadata |
| 9 | Main enclosure placement for the H755 build (Q-034): the measurements of §4.1 | §4.1, Wave 1 on-bike build |
| 5 | ~~GPS source and privacy handling~~ decided in D-060; UART pins still **CONFIRM** (procedure §7.3) | T1 speed check, §9 |
| 6 | ~~Listen-only capture tool for Q-001~~ decided in D-058 item 4 (conn `-listen-only` env) | §7 |
| 7 | ~~ECU round-trip instrumentation~~ decided in D-058 items 1-3 (BLE telemetry v4) | D-029, A-4 |
| 8 | moto-mobile has no iOS project yet (Android only), so the D-062 bonding check on iOS waits for one | §7.3 step 3 on iOS |

## 11. Later: moving to rt-core

When the NUCLEO-H755ZI-Q exists (D-072, Q-019 resolved), rt-core on its Cortex-M7 becomes the tester (D-021). conn is then built with `-e esp32-s3-devkitc-1-no-tester` (no TWAI driver at all), so there are never two testers. rt-core needs two transceivers (vehicle FDCAN1, platform FDCAN2, A-5), takes over microSD logging (D-045) and republishes the vehicle signals on the platform bus (D-056).
