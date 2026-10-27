# Vehicle Signal Taxonomy Beyond the CL250 (Groups G and I, Scale Tiers)

> **Idea notes, not decisions** (drafted with Antigravity/Gemini on 2026-10-18, session log `vehicle-workspace/external-ai/log/2026-10-18-antigravity-anomaly-sensor-analysis.md`; reviewed by Claude the same day; kept here by D-078 item 3). Nothing here overrides `DECISIONS.md`. Signal names are illustrative, **not** defs names: a signal enters a node only through `/signal-change` with a vehicle profile and a source (invariant 2).
>
> **Review (2026-10-18).** What is already decided elsewhere: the catalog / per-vehicle poll-list split (D-078 item 2), the health windows (D-079), the DTC freeze frames (D-080), position (D-076), two servers (D-077). What stays out of defs: groups G and I below (no vehicle, no source, no test, and MCU table cost). Counts in the original log (612 signals, ~3,500 features) are not repeated: on the CL250 only 5 DIDs are verified, 40 are polled, and Q-001 (passive broadcasts) is open.
>
> | Item | Verdict | Basis |
> |---|---|---|
> | G3 fuel-line T, G9 oil-pressure Y, G10 injector tap, G11 brake reservoir | DECIDE (safety) | They open or load fuel, oil, ECU-output or brake circuits. Not on the CL250 without a safety decision; a tap never drives or loads the bike's circuit |
> | G5 helmet biometrics | DECIDE | Personal health data: never committed (D-033); its own decision with the helmet unit (D-073) |
> | Group I (other vehicle types) | Taxonomy only | Enters defs with a vehicle profile that has the source (D-078 item 3) |
> | Scale-tier rules 3 and 4 | Already true | VSS/DBC contract between modules (ARCHITECTURE §7); nullable server columns |
> | Scale-tier rule 2 (one expansion connector) | DECIDE | Part of the Q-034 enclosure design |

## 1. Group G — external "master mechanic" sensors (any motorcycle)

| ID | Sensor (example part) | What it adds | CL250 note |
|---|---|---|---|
| G1 | Suspension travel (VL53L1X ToF or linear pot ×2) | fork/shock travel, compression/rebound velocity, bottoming count, dynamic sag | Q-010 (suspension pots) |
| G2 | Crankcase blow-by differential pressure (MPXV7002DP on the breather line) | crankcase pulse amplitude, ring-leak index | breather line only, no case modification |
| G3 | Fuel-line pressure transducer (0–5 bar, injector-hose T) | fuel pressure, drop on injection, regulator leak-down | safety decision first |
| G4 | Radiator outlet hose NTC | radiator ΔT, thermostat opening check, clog index | clamp-on preferred |
| G5 | Helmet biometrics (MAX30102, SCD40) | heart rate/HRV, helmet CO2, interior temperature | personal data, see review |
| G6 | Chain slack/whip (VL53L0X) | slack, whip amplitude, stretch | — |
| G7 | Magnetic drain plug with chip detector | ferrous debris index | drain-plug thread to confirm |
| G8 | Oil level and dielectric quality | level, contamination index | — |
| G9 | Oil pressure transducer (0–10 bar, Y on the switch port) | oil pressure per RPM, hot-idle pressure | safety decision first |
| G10 | Injector low-side tap | pulse width, duty, pintle delay | safety decision first (ECU output) |
| G11 | Brake-fluid moisture and level | water %, boiling-point estimate | safety decision first (brake circuit) |
| G12 | Steering head angle (AS5600) | steering angle/rate, front slip angle | — |
| G13 | Clutch lever position (AS5600) | lever %, bite point | Q-031 |
| G14 | Battery terminal NTC | temperature-compensated internal resistance | complements D-079 W2 |
| G15 | Rectifier heatsink NTC, stator ripple | rectifier temperature, 3-phase imbalance | — |
| G16 | Wheel bearing / brake disc envelopes (accelerometer) | BPFO/BPFI energy, warped-disc 1× wheel order | swing-arm ADXL345 of Wave 2 |
| G17 | Exhaust backpressure | backpressure, catalyst clog index | — |
| G18 | Shift rod force | shift force/duration, false neutrals | — |

## 2. Group I — other vehicle types (dormant on the CL250)

| ID | Vehicle type | Signal families |
|---|---|---|
| I1 | Inspection / NDT kit | coolant pressure (head gasket), ultrasonic acoustic emission (20–100 kHz), wideband lambda (LSU 4.9 + CJ125), stator stray flux, fuel quality, 4-gas exhaust |
| I2 | Variable valve timing (VVT, VTEC, ShiftCam, VANOS) | cam target vs actual angle and phase error, OCV duty/current, cam lift state, cylinder deactivation |
| I3 | Multi-cylinder, turbo, diesel, GDI | per-cylinder balance, crank acceleration, knock retard, misfire counters; boost, wastegate/VGT, intercooler, DPF, multi-point EGT, NOx, SCR, glow plugs |
| I4 | Automatic / DCT / DSG / CVT | TCM oil temperature, line pressure, clutch K1/K2 pressure and slip, shift drum, solenoid currents, belt slip |
| I5 | EV / hybrid | HV pack V/I/SOC/SOH, cell spread, isolation resistance, inverter and motor temperatures, phase balance, resolver error |
| I6 | ABS / cornering ABS / electronic suspension / EPS | wheel speeds, ABS valve activity, TCS/wheelie intervention, damper valve currents, steering torque |
| I7 | Smart alternator, electric pump, accessories | alternator target voltage and load, battery sensor, pump speed/current, accessory currents, parasitic sleep current |

## 3. Scale tiers (product direction, D-078)

- **Scale 1A — single plug + onboard sensors.** What the unit sees with no external harness: the ECU through the DLC (the D-068 poll list, whatever V0/V1 shows the CL250 serves), passive broadcasts if Q-001 finds any, the unit's own supply voltage sampled fast (cranking and charging ripple, D-079 W2), and the sensors inside the enclosure (IMUs, frame accelerometer, microphone, BME280, GPS, BLE TPMS), plus the derived signals of D-070.
- **Scale 1B — CL250 with external sensors.** Scale 1A plus the Wave 2 sensors wired to the bike (engine and swing-arm accelerometers, battery current, sump NTC, spark pickup, EGT, opto taps), the Wave 4 safety outputs and the helmet unit.
- **Scale 2 — other vehicles and inspection rigs.** Group I and the catalog PIDs no CL250 serves; defined only with a vehicle profile, silenced at runtime by the D-068 stop rule where they are polled at all.
- **Decoupling rules:** (1) each anomaly sub-model is exported per tier, so a missing external sensor is a masked input, never a NaN failure (vehicle-ml); (2) one expansion connector between 1A and 1B (Q-034); (3) modules talk only over the platform DBC and VSS; (4) every server column and vehicle-mcp field is nullable.

## 4. Anomaly-model direction (vehicle-ml / vehicle-server, not defs)

- **Sub-models instead of one model** (matches D-068 "there is not one model"): eight domains (combustion and fuel; cooling and lubrication; electrical and charging; valvetrain acoustics; crank, clutch and transmission; chain, bearings and drivetrain; suspension, chassis and tyres; brakes), each on its 10–15 core features. Reason: covariance rank and fault dilution in one large model.
- **Feature store for drill-down:** multi-horizon statistics, envelope and cepstrum spectra, coherence between inputs, degradation slopes and CAN-health counters, computed per window from raw data (D-069 item 6) on the server, served by vehicle-mcp tools (the LLM does no math, invariant 7).
- **Cross-vehicle cold start:** (1) physics and OBD rules that hold on any engine (cranking dip, internal resistance, charging ripple, trims in %, cold-soak spread); (2) order-domain and shape features (frequency / (RPM/60), kurtosis, crest factor) parameterised by cylinders, stroke, final drive; (3) a self-supervised baseline over the first D-079 windows of a new vehicle; (4) a fleet baseline per make/model on the server. Caveats from the review: day 1 holds for layer 1 only; mounting and transfer path shift the vibration domain; layer 3 can learn an already-faulty baseline, so gate it with layer 1; layer 4 needs other users' consent and is outside the thesis.
