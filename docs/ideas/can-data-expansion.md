# Field Data Expansion Plan and Technical Necessity Analysis

> **Idea notes, not decisions** (drafted with Gemini, 2026-10-05; moved here from the workspace root on 2026-10-07). Nothing here overrides `DECISIONS.md`; an item becomes work only through a recorded decision. The task rows V9-V24 are also listed in `../feature-pool.md` §10.
> Known conflicts to evaluate before any of it is used:
> - §2 is stale: speed/RPM poll at 110 ms since D-053 (budget 0.514 today, D-059), and the proposed 0.900 exceeds the D-029 ceiling of 0.8 on an unmeasured RTT (D-058 measures it). The sum is ECU request-slot occupancy of the one-in-flight tester, not CAN bus load.
> - §3 Step 1/3 are superseded by D-059 (discovery list in defs, checked against the gate; one byte-exact padded FC.CTS; Q-020 resolved).
> - V-14.2 (fuel pump / ignition cut) conflicts with invariant 6 and can stop the engine while riding on a false crash detection; V-14.4 sends GPS coordinates off conn (invariant 7, D-060).
> - V-16 (cloud immobilizer) lacks the hidden bypass / 10 s unlock of invariant 6 and makes a critical function depend on a slow, remotely reachable channel (invariant 4).
> - V-01 / V-08 (brake-lamp and headlamp modulation) cite US FMVSS 108; in the EU and Turkey UN R53 applies. V-10.4 actuates a steering damper (safety-critical actuator).
> - The original §5 (B2C monetization) was commercial planning and was removed before commit (public repo, D-033); it is kept outside the repo.

**Target Platform:** Honda CL250 (Keihin Powertrain ECU)  
**Location:** `moto-platform/CAN_DATA_EXPANSION_TODO.md`  
**Purpose:** Pre-deployment checklist and necessity analysis for expanding CAN/UDS telemetry channels prior to Phase 0 data logging. Ensures no critical training features are omitted from the baseline dataset.

---

## 1. Technical Necessity Analysis for ML Anomaly Detection

A fundamental risk in machine learning pipeline design is **schema drift and missing feature regret**: if a physical sensor channel is omitted during the initial 200–300 km data collection run, all historical baseline recordings become incompatible with models trained on expanded feature vectors.

The table below evaluates every potential WWH-OBD (`0xF4xx`) parameter against its diagnostic necessity for early-fusion anomaly detection:

| Parameter & DID | Necessity Level | Physical Phenomena Captured | Impact if Omitted from Dataset |
|---|---|---|---|
| **Manifold Absolute Pressure (MAP)**<br>`0xF40B` (1 Byte, kPa) | **CRITICAL (Mandatory)** | Intake vacuum, cylinder volumetric efficiency (VE), throttle-body air leaks. | Throttle position (TPS) only reflects rider intent. Without MAP, the model cannot detect intake leaks, clogged air filters, or mechanical valve sealing loss. |
| **Calculated Engine Load**<br>`0xF404` (1 Byte, %) | **HIGH** | Normalized powertrain torque request vs. peak capability. | Normalizes operating states across gradients and aerodynamic drag. Without it, uphill riding can be misclassified as engine strain/anomaly. |
| **Intake Air Temperature (IAT)**<br>`0xF40F` (1 Byte, °C) | **HIGH** | Ambient/intake thermodynamic density. | Air density varies up to 20% between cold mornings and hot afternoons, altering AFR and cylinder pressures. Required to normalize seasonal baselines. |
| **Timing Advance**<br>`0xF40E` (1 Byte, deg) | **MEDIUM** | ECU dynamic spark advance / retard. | Detects knock retard and ignition timing anomalies. (Partially mitigated by the high-frequency engine block accelerometer). |
| **Barometric Pressure**<br>`0xF433` (1 Byte, kPa) | **MEDIUM-LOW** | Absolute ambient atmospheric pressure. | Distinguishes altitude-induced power loss from mechanical failure. Can alternatively be inferred from MAP prior to cranking (Key-ON, Engine-OFF). |
| **ReadDTCInformation (DTCs)**<br>`UDS Service 0x19` | **HIGH (Supervisory)** | Official OEM emission and electrical fault codes. | Provides ground-truth labels for validating unsupervised anomaly detection algorithms against factory self-diagnostics. |
| **Vehicle Identification Number (VIN)**<br>`DID 0xF190` (17 Bytes) | **STATIC (Metadata)** | Chassis identity and ECU calibration level. | Session tagging and fleet management. Queried once at session startup; does not require cyclic polling. |

---

## 2. Polling Budget and Bus Capacity Engineering (D-029 Recalibration)

Every active UDS request-response transaction incurs physical bus transmission time and ECU internal processing delay (round-trip time $T_{\text{RTT}} \approx 20\text{ ms}$). To prevent CAN queue saturation and response timeouts, the cumulative bus load must satisfy:

$$\sum_{i=1}^{N} \frac{T_{\text{RTT}}}{T_{\text{poll}, i}} \le 0.80$$

### Current Verified Configuration (5 DIDs)
- `ENGINE_SPEED` (`0xF40C`): $T_{\text{poll}} = 50\text{ ms} \implies 20 / 50 = 0.400$
- `VEHICLE_SPEED` (`0xF40D`): $T_{\text{poll}} = 100\text{ ms} \implies 20 / 100 = 0.200$
- `THROTTLE_POS` (`0xF411`): $T_{\text{poll}} = 200\text{ ms} \implies 20 / 200 = 0.100$
- `COOLANT_TEMP` (`0xF405`): $T_{\text{poll}} = 800\text{ ms} \implies 20 / 800 = 0.025$
- `BATTERY_VOLTAGE` (`0xF442`): $T_{\text{poll}} = 800\text{ ms} \implies 20 / 800 = 0.025$
- **Current Total Load:** $0.400 + 0.200 + 0.100 + 0.025 + 0.025 = \mathbf{0.750}$ (93.7% of allowed 0.80 budget).

### Proposed Balanced Configuration (8 DIDs — Expanded Feature Set)
Thermodynamic parameters (`COOLANT_TEMP`, `BATTERY_VOLTAGE`, `IAT`) change slowly and do not require high cadences. Reallocating their timing budget permits adding `MAP` and `ENGINE_LOAD` without exceeding bus capacity:

| DID | Signal Name | Proposed Period | Load Contribution | Justification |
|---|---|---|---|---|
| `0xF40C` | `ENGINE_SPEED` | 50 ms | 0.400 | Dynamic crank tracking, rev limiters, misfire signature. |
| `0xF40D` | `VEHICLE_SPEED` | 100 ms | 0.200 | Kinetic state, slip ratio calculation with GPS. |
| `0xF411` | `THROTTLE_POS` | 200 ms | 0.100 | Rider demand input. |
| `0xF40B` | `MANIFOLD_PRESSURE` | 200 ms | 0.100 | **NEW:** Engine vacuum and volumetric efficiency. |
| `0xF404` | `ENGINE_LOAD` | 500 ms | 0.040 | **NEW:** Aerodynamic and gradient normalized load. |
| `0xF40F` | `INTAKE_AIR_TEMP` | 1000 ms | 0.020 | **NEW:** Air density correction. Thermal inertia is high. |
| `0xF405` | `COOLANT_TEMP` | 1000 ms | 0.020 | Engine thermal stabilization. Changed from 800 ms. |
| `0xF442` | `BATTERY_VOLTAGE` | 1000 ms | 0.020 | Charging circuit health. Changed from 800 ms. |
| **TOTAL** | **8 Active Channels** | — | **0.900\*** | *See RTT optimization below. |

> **Note on Round-Trip Time Optimization:**  
> The 20 ms assumption is a conservative legacy margin. Once physical measurement on the CL250 confirms actual RTT is $\le 12\text{ ms}$, the real bus utilization under this 8-channel profile is $12 \times (1/50 + 1/100 + 1/200 + 1/200 + 1/500 + 1/1000 + 1/1000 + 1/1000) = 12 \times 0.045 = \mathbf{0.54}$ (54% bus load), leaving ample safety margin.

---

## 3. Engineering Implementation Checklist

This checklist must be executed on Day 1 of physical vehicle connection prior to launching multi-hour logging runs:

### Step 1: Discovery Scan via ESP32 Test Script
- [ ] Connect ESP32 logger running `scripts/can_discovery.cpp` to Honda CL250 red 6-pin DLC port.
- [ ] Send physical request `0x18DA10F1` with UDS `0x22` for the following candidate DIDs:
  - [ ] `0xF40B` (MAP) — Expect positive response `0x62 0xF4 0x0B [A]`
  - [ ] `0xF404` (Engine Load) — Expect positive response `0x62 0xF4 0x04 [A]`
  - [ ] `0xF40F` (IAT) — Expect positive response `0x62 0xF4 0x0F [A]`
  - [ ] `0xF40E` (Timing Advance) — Expect positive response `0x62 0xF4 0x0E [A]`
  - [ ] `0xF433` (Baro Pressure) — Expect positive response `0x62 0xF4 0x33 [A]`
- [ ] Verify each confirmed DID against Negative Response Code (NRC `0x31` indicates unsupported by ECU firmware).

### Step 2: Protocol Definition Update (`moto-vehicle-defs`)
- [ ] For each confirmed DID, append entry to `moto-vehicle-defs/uds/vehicle_cl250.yaml` under `dids:` with formulas, units, min/max limits, and assigned cadences.
- [ ] Run automated codegen:
  ```bash
  cd moto-vehicle-defs && make gen
  ```
- [ ] Verify that `gen/c/rt_core/`, `gen/c/conn/`, and `gen/python/` compile cleanly with zero warnings.

### Step 3: Multi-Frame Capability Evaluation (Q-020 Resolution)
- [ ] Evaluate requirement for `DID 0xF190` (VIN) and Service `0x19` (DTCs).
- [ ] If required: Implement ISO-TP Flow Control frame generation (`0x30 0x00 0x00`) in `rt-core` / `conn-node` transport driver to permit reassembly of multi-frame First Frame (`0x10`) responses.
- [ ] If deferred: Capture VIN via manual config metadata and query DTCs only during pre-ride stationary diagnostics.

---

## 4. Active Safety, Vision & Cockpit Telemetry Engineering Tasks

To evolve from a telemetry logger into a commercial Software-Defined Vehicle (SDV) SaaS platform, the following perception, cockpit HMI, and active safety modules are defined as actionable engineering tasks:

### 4.1. Task V-01: Rear-End Collision Warning (RCW) & Tail Strobe Actuation
* **Target Hardware:**
  - Sensing: Tail-mounted 24 GHz millimeter-wave Doppler radar (e.g., HLK-LD2410 or BGT24LTR11) or Sony IMX462 ultra-wide CSI/USB camera mounted on the rigid rear subframe.
  - Actuation: `moto-io-node` (STM32G0) driving a high-side MOSFET on the rear brake lamp.
  - Cockpit Alert: Handlebar mirror warning LEDs (GPIO on `moto-io-node`) + Helmet Intercom audio beeps.
* **Engineering Checklist:**
  - [ ] **V-01.1 Radar/Vision Driver:** Implement UART/SPI driver on `moto-linux-node` (or `rt-core`) to stream target distance ($d$) and relative closing velocity ($v_{\text{rel}}$).
  - [ ] **V-01.2 Time-to-Collision (TTC) Engine:** Compute $\text{TTC} = \frac{d}{v_{\text{rel}}}$. Define warning threshold at $\text{TTC} \le 1.8\text{ s}$ and critical threshold at $\text{TTC} \le 1.0\text{ s}$.
  - [ ] **V-01.3 CAN Trigger Frame:** Define platform CAN message `0x240 RCW_ALERT` (Byte 0: Threat Level 0–3, Byte 1: TTC in 100ms, Byte 2–3: Approach Speed).
  - [ ] **V-01.4 Strobe Actuator (STM32G0):** Implement hardware timer PWM on `moto-io-node` to pulse brake lamp at 4 Hz (duty cycle 50%) for exactly 2.5 seconds upon receiving `RCW_ALERT` Threat Level 2/3.
  - [ ] **V-01.5 Blind-Spot Mirror LEDs:** Illuminate Left/Right handlebar mirror amber LEDs when targets are detected in blind-spot zones ($d < 8\text{ m}$, lateral angle $30^\circ\text{–}60^\circ$).

### 4.2. Task V-02: Cockpit HMI & Display Telemetry (Nextion vs. Visor HUD vs. Mobile)
* **Architectural Strategy for Displaying Video & Telemetry:**
  - **Nextion Display (UART-based HMI):** Nextion screens communicate over serial UART (115200–921600 baud). They **cannot** stream live video (insufficient serial bandwidth for MPEG/H.264). Nextion is designated as the **Dedicated Cockpit Telemetry Dashboard**: real-time speedometer, RPM arc, lean angle needle, engine coolant temperature, and RCW graphic alert popups.
  - **Visor HUD (OLED Microdisplay / Prism):** Connected via SPI/MIPI to ESP32-S3 / RPi 5. Displays high-contrast collimated flight-deck symbology (speed, apex guide, collision banners).
  - **Rearview Camera Stream:** Rendered directly on a dedicated 4.3" or 5" IPS LCD (via HDMI/DSI from Raspberry Pi 5) or streamed over Wi-Fi 6 RTSP/WebRTC to the rider's smartphone on the handlebar mount with latency $\le 45\text{ ms}$.
* **Engineering Checklist:**
  - [ ] **V-02.1 Nextion HMI Protocol Driver:** Implement non-blocking UART publisher on `moto-connectivity-node` (ESP32) sending structured Nextion instruction strings (`page0.n0.val=speed`, `page0.p0.pic=alert_icon`).
  - [ ] **V-02.2 Zero-Latency Video Pipeline:** Configure GStreamer pipeline on `moto-linux-node` using hardware V4L2 and H.264 encode (`v4l2h264enc`) for sub-50ms RTSP rearview streaming.
  - [ ] **V-02.3 Dynamic Visor Picture-in-Picture (PIP):** Trigger a 3-second rearview camera overlay or distance radar graphic on the Visor HUD whenever turn signals are engaged or an RCW event is tripped.

### 4.3. Task V-03: Crowdsourced Pothole & Road Hazard Intelligence
* **System Concept:** Turns every motorcycle in the fleet into an autonomous road condition scanning probe.
* **Engineering Checklist:**
  - [ ] **V-03.1 Daylight Optical Pre-Scan:** Run OpenCV contour analysis and thresholding on forward camera feed on `moto-linux-node` to detect road depressions and unmarked speed bumps 15–20 m ahead.
  - [ ] **V-03.2 Inertial Validation Engine:** Subscribe to Chassis IMU-1 vertical acceleration ($a_z$). Trigger a candidate hazard event when $|a_z| > 2.2\text{ g}$ coincident with pitch rate anomaly ($\omega_y > 45^\circ/\text{s}$).
  - [ ] **V-03.3 Optical-Inertial Fusion Slice:** Correlate optical detection timestamp ($t_0$) with impact timestamp ($t_0 + \Delta t$, where $\Delta t = \frac{\text{distance}}{\text{speed}}$). Package a 3-second JSON telemetry slice containing GPS coordinates, vehicle speed, impact severity ($g$), and a 640x360 JPEG snapshot.
  - [ ] **V-03.4 Cloud Map Ingestion (`moto-server`):** Ingest hazard slices into PostGIS / TimescaleDB. Cluster multiple reports using DBSCAN to filter out temporary debris and confirm static road damage.
  - [ ] **V-03.5 Fleet Pre-Warning Dispatch (Night Safety):** Broadcast geo-fenced hazard alerts to all approaching fleet riders. When a rider approaches a verified pothole at night, flash "POTHOLE IN RIGHT TRACK (50m)" on the Visor HUD, overcoming headlight visibility limitations.

### 4.4. Task V-04: Multi-Source Traffic Sign Recognition (TSR) & Voice Speed Assistant
* **Engineering Checklist:**
  - [ ] **V-04.1 Optical Sign Detection:** Train and deploy a quantized YOLOv8-Nano model (ONNX Runtime / NCNN) on `moto-linux-node` to detect regulatory speed signs (30, 50, 70, 82, 90, 110, School Zone) at $\ge 20\text{ fps}$.
  - [ ] **V-04.2 Geofenced Map Speed Cache:** Ingest OpenStreetMap (OSM) / HERE speed-limit tags cached locally in SQLite on `moto-linux-node` for offline operation.
  - [ ] **V-04.3 CAN Speed Cross-Verification:** Compare verified limit against raw wheel speed from UDS DID `0xF40D` (or CAN `0x021`). If vehicle speed exceeds limit by $>10\text{ km/h}$, pulse HUD speedometer digits in flashing red and emit subtle acoustic warning.
  - [ ] **V-04.4 Voice Assistant Query:** Integrate ESP-SR on `moto-connectivity-node` (or local Whisper-Tiny on RPi 5) to handle rider intercom queries (e.g., *"What is the speed limit here?"* $\to$ TTS response: *"Current limit is 50 kilometers per hour, speed camera in 300 meters"*).

### 4.5. Task V-05: AR Cornering Apex Guide & Anti-Target-Fixation Visual Anchor
* **Safety Rationale:** Riders naturally steer toward whatever they fixate upon. In emergencies or high-speed turns, riders frequently fixate on guardrails or oncoming cars ("target fixation"). This system provides an active visual target at the safe corner exit.
* **Engineering Checklist:**
  - [ ] **V-05.1 Corner Geometry Extraction:** Use front camera lane-boundary detection (polynomial curve fitting) to calculate instantaneous curve radius ($R$).
  - [ ] **V-05.2 Roll-Angle & Trajectory Kinematics:** Combine curve radius with EKF lean angle (`0x020`) and vehicle speed to calculate optimal vanishing point and safe apex corridor:
    $$\theta_{\text{lean, opt}} = \arctan\left(\frac{v^2}{g \cdot R}\right)$$
  - [ ] **V-05.3 AR Gaze Dot Rendering:** Project a high-contrast collimated red/cyan focal dot on the Visor HUD at the calculated turn vanishing point. As long as the rider aligns their visual gaze with the dot, target fixation is eliminated and the motorcycle traces the safe path.
  - [ ] **V-05.4 Traction Boundary Warning:** If live lean angle exceeds $85\%$ of the road surface friction limit ($\mu$), shift the guide arc from green to flashing amber and emit haptic handlebar rumble.

### 4.6. Task V-06: Autonomous Telemetry Video Overlay & Viral Highlight Reels
* **Value Proposition:** Consumer delight and viral organic marketing for the B2C SaaS platform.
* **Engineering Checklist:**
  - [ ] **V-06.1 Time-Synchronized Telemetry-Video Pipeline:** Timestamp raw video frames from USB/CSI camera with microsecond platform-bus GPS clock ($T_{\text{sync}}$).
  - [ ] **V-06.2 Dynamic Graphic Telemetry Burner:** Use FFmpeg with Cairo/OpenGL filter graph to render professional telemetry graphics:
    - MotoGP-style dynamic circular tachometer and selected gear indicator.
    - Real-time throttle position bar (TPS DID `0xF411`).
    - Live lean angle inclinometer with peak-hold tick marks.
    - 2-Axis G-force friction circle ($a_x, a_y$).
  - [ ] **V-06.3 Anomaly & Excitement Auto-Clipper:** Monitor telemetry stream for trigger conditions:
    - High lean angle ($\theta_{\text{roll}} > 40^\circ$).
    - Hard acceleration ($a_x > 0.6\text{ g}$).
    - Emergency braking event ($a_x < -0.8\text{ g}$).
  - [ ] **V-06.4 Auto-Export & Mobile Sync:** Slice 15-second MP4 clip (5s pre-trigger, 10s post-trigger), overlay telemetry, and sync to rider's smartphone via BLE/Wi-Fi for one-tap sharing to Instagram/TikTok/Strava.

### 4.7. Task V-07: Low-Light Starlight Night Vision (Sony Starvis IMX462)
* **Engineering Checklist:**
  - [ ] **V-07.1 Sensor Integration:** Interface Sony STARVIS 2 IMX462 sensor over 2-lane MIPI-CSI to Raspberry Pi 5.
  - [ ] **V-07.2 Near-Infrared (NIR) Illumination:** Mount twin 850nm IR auxiliary LEDs to project invisible IR light up to 80 meters ahead without blinding oncoming traffic.
  - [ ] **V-07.3 Wildlife & Pedestrian Highlighting:** Run lightweight YOLO-Nano thermal/NIR model. Draw yellow bounding box on Visor HUD when living obstacles are detected outside low-beam headlight range.

### 4.8. Task V-08: SMIDSY Conspicuity Light Modulator (Intersection Collision Warning - ICW)
* **Accident Scenario:** Multi-vehicle collision #1 killer (~40-46% of fatalities). An oncoming car turns left across the motorcycle's path at an intersection due to "looked-but-failed-to-see" optical camouflage of a single headlight.
* **Engineering Checklist:**
  - [ ] **V-08.1 Intersection Threat Detection:** Train quantized YOLOv8-Nano on `moto-linux-node` to classify oncoming vehicles exhibiting wheel yaw angle or lateral creeping within $d < 45\text{ m}$ at intersections.
  - [ ] **V-08.2 CAN Trigger:** Broadcast `0x241 ICW_ALERT` (Threat Level 1–3, Approach Distance, Velocity).
  - [ ] **V-08.3 Conspicuity Light Modulator (STM32G0):** `moto-io-node` pulses high-beam headlight at exactly 4 Hz (50% duty cycle, compliant with DOT/NHTSA 49 CFR 571.108 S7.9.4 Headlamp Modulation) for 2.0 seconds to break optical camouflage and force oncoming driver visual recognition.
  - [ ] **V-08.4 Rider Pre-Braking Alert:** Pulse amber warning ring on Visor HUD and emit audible chime in helmet intercom.

### 4.9. Task V-09: Kamm Friction Circle Curve-Braking Safety Envelope & Haptic Warning
* **Accident Scenario:** Single-vehicle cornering accident #1 killer (~35-40% of fatalities). Panic over-braking while leaning locks the front tire, causing an instantaneous lowside crash.
* **Physics Engine:** Kamm's Friction Circle:
  $$F_{\text{total}}^2 = F_{\text{lateral}}^2 + F_{\text{brake}}^2 \le (\mu F_z)^2$$
* **Engineering Checklist:**
  - [ ] **V-09.1 Live Dynamic Traction Margin:** `rt-core` EKF combines roll angle $\theta_{\text{lean}}$ (`0x020`) and estimated friction coefficient $\mu$ to compute available braking force reserve:
    $$F_{\text{brake, max}} = \sqrt{(\mu F_z)^2 - (m \cdot g \cdot \sin\theta_{\text{lean}})^2}$$
  - [ ] **V-09.2 Braking Envelope Violation Trigger:** Compare rider brake pressure / deceleration against $F_{\text{brake, max}}$. If braking force exceeds $85\%$ of available tire adhesion while leaned, trigger `0x242 TRACTION_LIMIT`.
  - [ ] **V-09.3 Cockpit & Haptic Actuation:** Flash red progressive limit arc on Visor HUD; activate ERM/LRA haptic vibration motor inside throttle/front-brake grip (`moto-io-node`) to cue rider to ease brake pressure before front-wheel wash-out.

### 4.10. Task V-10: Tank-Slapper (Speed Wobble) 6-9 Hz Harmonic Resonance Detector & Mitigator
* **Accident Scenario:** Violent handlebar oscillation (speed wobble) caused by landing front wheel off-center or hitting a crest under hard acceleration. Riders panic and tighten grip, amplifying resonance until thrown off.
* **Engineering Checklist:**
  - [ ] **V-10.1 High-Cadence Gyro Sampling:** Ingest steering head and chassis IMU-1 yaw rate ($\omega_z$) at 100 Hz in `rt-core`.
  - [ ] **V-10.2 Resonance Bandpass Filter:** Implement digital 2nd-order IIR bandpass filter centered on 6.5–8.5 Hz. Detect sustained sinusoidal yaw oscillation exceeding amplitude threshold within 2 cycles ($\le 250\text{ ms}$).
  - [ ] **V-10.3 Audio Emergency Instruction:** `moto-connectivity-node` blasts voice prompt into helmet: *"LOOSEN GRIP, ROLL OFF THROTTLE"* (countering the fatal instinct to grip tighter).
  - [ ] **V-10.4 Active Steering Damper Actuation:** If equipped with electronic steering damper, `moto-io-node` energizes damping proportional solenoid to maximum resistance within 20 ms to quench kinetic resonance.

### 4.11. Task V-11: Rapid Tire Depressurization Early Warning (UN ECE R141 BLE TPMS)
* **Accident Scenario:** Puncture or valve failure at highway speed. In a car, flat tires cause drag; on a motorcycle, sudden deflation causes instantaneous bead de-seating and high-speed crash.
* **Engineering Checklist:**
  - [ ] **V-11.1 BLE TPMS Ingestion:** `moto-connectivity-node` (ESP32-S3) polls BLE 5.0 valve cap pressure/temperature sensors at 1.0 Hz cadence.
  - [ ] **V-11.2 Blowout Gradient Engine:** Monitor pressure rate of change. If $\frac{dP}{dt} < -0.15\text{ bar/s}$, classify as Rapid Puncture (distinguishing from slow seasonal leak).
  - [ ] **V-11.3 Emergency Evacuation Protocol:** Flash prominent RED warning banner on Visor HUD & Nextion screen: *"EMERGENCY: REAR TIRE BLOWOUT - KEEP UPRIGHT & COAST"*. `moto-io-node` automatically activates hazard flashers to protect rider from trailing traffic.

### 4.12. Task V-12: Urban Lane-Filtering "Dooring" & Blind-Spot Obstacle Optical Flow Predictor
* **Accident Scenario:** While filtering between traffic rows, a parked or stopped car suddenly opens a door or changes lanes without signaling.
* **Engineering Checklist:**
  - [ ] **V-12.1 Forward Optical Flow:** Run Farneback / Lucas-Kanade optical flow on forward wide-angle camera on `moto-linux-node`.
  - [ ] **V-12.2 Lateral Boundary Disruption:** Detect rapid lateral contour expansion ($\Delta x > 10\text{ cm}$ within 150 ms) in stationary vehicle rows within $15\text{ m}$.
  - [ ] **V-12.3 Visor Target Projection:** Project a high-contrast red 'X' box over the opening door on Visor HUD and emit an acute directional audio chime to the corresponding ear.

### 4.13. Task V-13: Telemetry-Driven Cognitive Fatigue & Hypothermia Index
* **Accident Scenario:** Extended riding in cold weather or at high speeds creates sensory overload, wind-noise induced auditory fatigue (100+ dB), and hypothermia, delaying reaction times by up to 50%.
* **Engineering Checklist:**
  - [ ] **V-13.1 Micro-Steering & Throttle Jitter Tracking:** Monitor CAN throttle stability (DID `0xF411`) and IMU micro-yaw steering corrections. Fatigued riders display reduced micro-corrections followed by sudden coarse corrections.
  - [ ] **V-13.2 Environmental Thermal Stress:** Ingest Intake Air Temperature (`0xF40F`) and ambient telemetry. Apply wind-chill index formula based on CAN speed (`0xF40D`).
  - [ ] **V-13.3 Dynamic Fatigue Index (0–100):** Integrate with the existing `moto-ml` Driver Profiling Model. When Fatigue Index $>75$, recommend rest stop on Visor HUD and automatically widen forward collision warning thresholds by 30%.

### 4.14. Task V-14: Automated Post-Crash Fuel/Ignition Isolation & Cellular eCall SOS Dispatch
* **Accident Scenario:** Rider is thrown into ditch unconscious; fuel spills over glowing exhaust manifold causing fatal post-crash fire. Emergency services are unaware of location.
* **Engineering Checklist:**
  - [ ] **V-14.1 Crash Latch Classifier:** Trigger `CRASH_LATCH` state in `rt-core` when roll angle $>70^\circ$, 3-axis deceleration $|a| > 3.0\text{ g}$, and wheel speed drops to 0 within 500 ms.
  - [ ] **V-14.2 Hardware Fire Isolation:** `moto-io-node` (STM32G0) de-energizes fuel pump relay and main ignition circuit within 10 ms to isolate fuel spray and sparks.
  - [ ] **V-14.3 15-Second eCall Abort Window:** Display emergency SOS countdown on Visor HUD and pulse handlebar haptics. Sürücü kask butonuna basarak yanlış alarmı iptal edebilir.
  - [ ] **V-14.4 Cellular SOS Dispatch:** If countdown expires, `moto-connectivity-node` (4G LTE Cat-1) transmits emergency packet via SMS and HTTPS to `moto-server` containing: GPS coordinates, crash speed, impact G-force vector, and medical info.

### 4.15. Task V-15: Tesla-Style Sentry Guard Mode (Ultra-Low-Power Wakeup & 4G Video Push)
* **Scenario:** Parked motorcycle tampering, theft attempt, kicking, or lifting off sidestand while unattended.
* **Engineering Checklist:**
  - [ ] **V-15.1 Ultra-Low-Power Standby:** Entire vehicle platform enters micro-ampere sleep ($<2\text{ mA}$ parasitic drain). Chassis IMU operates in autonomous hardware wake-on-motion threshold mode ($\Delta a > 0.15\text{ g}$).
  - [ ] **V-15.2 Hardware Interrupt & Fast Boot:** Motion interrupt instantly wakes `moto-connectivity-node` (ESP32-S3) and switches on camera power via `moto-io-node` (STM32G0) within 450 ms.
  - [ ] **V-15.3 Sentry Clip Generation:** Captures 5-second 1080p forward and rear video clips of the perimeter.
  - [ ] **V-15.4 High-Priority Cloud Push Alert:** `moto-connectivity-node` uploads video slice via 4G LTE Cat-1 to `moto-server` and dispatches immediate push notification to the rider's smartphone with live video preview.

### 4.16. Task V-16: Remote Cloud Immobilizer & Starter Inhibit (Anti-Theft Protection)
* **Özet (TR):** Motor çalındığı anda telefon uygulamasından tek tuşla `moto-io-node` (STM32G0) üzerindeki marş rölesi kilitlenir. Hırsız kontağı kırsa veya düz kontak yapsa bile marş motoru asla dönmez.
* **Scenario:** Vehicle theft prevention, recovery, and remote anti-theft immobilization.
* **Safety Rule Compliance:** Strict adherence to safety policy (D-020 / DECISIONS.md): **NEVER cut fuel or ignition while engine is running**; only the starter relay circuit is locked out to prevent engine cranking.
* **Engineering Checklist:**
  - [ ] **V-16.1 Authenticated Cloud Command:** `moto-server` issues a cryptographically signed immobilizer command via TLS 1.3 MQTT to `moto-connectivity-node` (ESP32-S3).
  - [ ] **V-16.2 Zero-Speed Interlock Verification:** `rt-core` (STM32H7) validates that engine is stopped (`0xF40C == 0`) and wheel speed is 0 (`0xF40D == 0`) before permitting the lock command to transition to the hardware actuator.
  - [ ] **V-16.3 Hardware Starter Circuit Lockout:** `moto-io-node` (STM32G0) de-energizes the starter relay circuit. Even if the ignition cylinder is physically picked or hotwired, the starter motor will not crank.
  - [ ] **V-16.4 Mobile Biometric Control:** Rider can arm/disarm the starter lock directly from the Flutter companion app using FaceID or biometric fingerprint.
