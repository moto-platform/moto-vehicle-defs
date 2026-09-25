# Hardware Procurement List — Moto Platform

> Translated from the Turkish original (`tr/donanim-tedarik-listesi.md`). Where this document conflicts with `ARCHITECTURE.md` or `DECISIONS.md`, those take precedence.

**Purpose:** Complete parts list compiled from all subsystems, viewable in one place. Grouped by installation order — buy top to bottom.
**Version:** 1.0 — September 2026

**Usage:** Update the Status column (On hand / Ordered / Arrived / Installed). Prices are September 2026 Turkey estimates — confirm before ordering.

---

## Group 1 — Now (for moto-vehicle-defs + moto-hil-bench + connectivity-node)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| STM32F4 Nucleo/Discovery | 1 | HIL simulator brain | 300-600 | |
| CAN transceiver (SN65HVD230) | 2 | HIL simulator + DUT side | 160-300 | |
| STM32F103 | — | Fault/power control | **On hand** | ✓ |
| Programmable power supply (buck+DAC/digital pot) | 1 | HIL voltage scenarios | 200-400 | |
| OBD2 female connector + cable | 1 (for HIL) | Connecting DUT to bench | 150-300 | |
| ESP32-S3 board | — | Connectivity node | **Probably on hand** | |
| i7 5th gen desktop | — | HIL host, Linux+SocketCAN | **On hand** | ✓ |
| **Subtotal** | | | **~810-1600** | |

## Group 2 — Once moto-rt-core (STM32H7) hardware arrives

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| STM32H7 Nucleo/Discovery (H743/H723) | 1 | Main domain MCU | 600-1200 | |
| CAN transceiver | 1 | Main unit CAN | 80-150 | |
| IMU (6/9 axis, MPU9250/LSM6DSO) | 1 | Lean angle/EKF | 150-300 | |
| GPS module (NEO-M8N) + antenna | 1 | Position, speed verification | 250-450 | |
| microSD module + industrial card | 1 | Logging | 150-300 | |
| **Subtotal** | | | **~1230-2400** | |

## Group 3 — Power Board (MCU line)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Wide-input buck (6-40V→5V, 2-3A) | 1 | MCU supply | 150-250 | |
| Supercapacitor + balancing + current limiter | 1 set | Safe shutdown | 150-300 | |
| INA226 | 1 | Power monitoring (MCU line) | 100-300 | |
| TVS diode, reverse-polarity MOSFET, fuse | 1 set | Protection | 100-250 | |
| **Subtotal** | | | **~500-1100** | |

## Group 4 — Anomaly Detection (Additional Sensors)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Separate accelerometer (on engine block) | 1 | Vibration signature (independent of existing IMU) | 150-250 | |
| EGT thermocouple + MAX31855 | 1 | Exhaust temperature | 300-600 | |
| Oil pressure/temperature sensor (optional) | 1 | Lubrication diagnostics | 300-600 | |
| Microphone (I2S, shared for acoustic anomaly + voice command) | 1 | Engine sound + voice command | 250-450 | |
| **Subtotal** | | | **~1000-1900** | |

## Group 5 — Blind Spot (part of moto-io-node)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| STM32 G0/F0 | 1 | I/O node brain | 100-250 | |
| 24 GHz radar module | 2 | Left+right side detection | 600-1600 | |
| High-brightness LED (in-mirror) | 2 | Blind spot indicator | 80-200 | |
| CAN transceiver | 1 | I/O node CAN | 80-150 | |
| **Subtotal** | | | **~860-2200** | |

## Group 6 — Immobilizer + Park Mode + Power (part of moto-io-node, same chip as Group 5)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Bistable relay | 1 | Starter circuit lockout | 80-200 | |
| NFC reader (PN532) | 1 | Authorization | 100-250 | |
| Simple NFC tag (NTAG213/215) | 2-3 | Key tag | 10-50 | |
| Hidden mechanical bypass switch | 1 | Fail-safe | 50-100 | |
| GSM module + line | 1 | Park mode/theft tracking connectivity (in addition to WiFi, portable notification) | 400-900 | |
| **Subtotal** | | | **~640-1500** | |

**Park mode notification channel:** Connectivity via GSM (in addition to/as backup for WiFi); when motion is detected, a notification is sent via the WhatsApp Business API (Meta Cloud API or Twilio) — this is a software/service integration, not hardware, and adds no extra cost at low volume.

**NFC cryptographic upgrade (Phase 2):** Move from simple UID-reading NTAG to a cryptographically authenticated MIFARE DESFire tag — for clone resistance. Tag cost ~50-150 TL/unit; the PN532 supports this in hardware, but true DESFire authentication requires integrating an additional library (libfreefare, etc.) — a software task, hardware unchanged.

## Group 7 — Safety Node

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| STM32 G4/F3 | 1 | Cornering safety, isolated | 150-400 | |
| CAN transceiver | 1 | Safety node CAN | 80-150 | |
| **Subtotal** | | | **~230-550** | |

## Group 8 — Display/Instrument Cluster

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Nextion | — | Main information display | **On hand** | ✓ |
| WS2812 LED strip/ring | 3+ | Lean angle indicator (x2) + shift-light | 200-400 | |
| Ambient light sensor (optional) | 1 | Day/night | 50-100 | |
| **Subtotal** | | | **~250-500** | |

## Group 9 — Linux Node (Raspi 5)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Raspi 5 8GB | — | Linux node | **On hand** | ✓ |
| MCP2515+transceiver or CAN HAT | 1 | Raspi CAN access | 200-400 | |
| Raspi camera module | 1 | Lane tracking | 500-1500 | |
| Wide-input buck (isolated line) | 1 | Separate Raspi supply | 200-350 | |
| INA226 | 1 | Power monitoring (Raspi line) | 100-300 | |
| Passive heatsink + breathable membrane | 1 set | Thermal management (IP67 enclosure) | 150-350 | |
| **Subtotal** | | | **~1150-2900** | |

## Group 10 — Mechanical/Mounting (general)

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| IP54/IP67 enclosure | 3-4 | Main unit, power board, Raspi box | 450-1200 | |
| Deutsch DT connector kit | 1 set | Vehicle connections | 300-600 | |
| PG7 cable gland + O-ring | 4-6 | Sealing | 200-400 | |
| Vibration mount, cable, spiral wrap, fuse | — | General mounting | 250-450 | |
| **Subtotal** | | | **~1200-2650** | |

## Group 11 — Experimental Validation

| Part | Qty | Purpose | Estimate (TL) | Status |
|---|---|---|---|---|
| Sprocket (11-13T, for experiment) | 1 | Measurement system sensitivity verification | 300-600 | |
| Suspension potentiometers | 2 | Road surface, setup effect | 300-600 | |
| Brake line pressure sensor (transducer + T-fitting + signal conditioning) | 1 | Brake force analysis, virtual dyno input | 350-900 | |
| **Subtotal** | | | **~950-2100** | |

**Also to acquire (budget/access dependent):** External dynamometer reference measurement — commercial session (3000-6000 TL) or university lab access (to be investigated, may be cost-free if available).

## Group 12 — Advanced/Phase 2 (optional, do not buy now)

| Part | Purpose | Estimate (TL) |
|---|---|---|
| Wideband lambda sensor | AFR/combustion quality | 2000-4000 |
| RTK GPS module | Line analysis (race telemetry) | 2000-4500 |
| TPMS sensors | Race pressure tracking | 800-1500 |
| Brake lever load cell | Brake force analysis (lever side — separate from the sensor measuring the line) | 500-1200 |
| MIFARE DESFire cryptographic NFC tag | Immobilizer clone-resistance upgrade | 50-150/unit |

---

## Grand Total (Groups 1-10, mandatory/core)

**~8,900-16,900 TL** (approximate range updated with the GSM+NFC tag line items added to Group 6)

Excludes Groups 11-12. Buy in stages — Group 1 this week, Groups 2-3 over the next few weeks, the rest once the relevant subsystem development begins.

## Already On Hand (summary)

- STM32F103 (fault/power control)
- ESP32-S3 board (probably)
- i7 5th gen desktop (HIL host)
- Nextion display
- Raspi 5 8GB
- Raspi 3B+ (role: home server — ECU behavior analysis, offline, within Phase 2 scope)
