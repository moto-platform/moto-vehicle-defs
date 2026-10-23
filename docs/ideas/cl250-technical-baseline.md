# Honda CL250 (8BK-MC57) — Technical Baseline & Service Specifications

> Idea note (Antigravity, 2026-10-20), not a decision; values without a cited source are CONFIRM.

> [!NOTE]
> **Status:** GREEN zone (`docs/ideas/*`). Idea and technical baseline reference note. No source is cited for the part numbers and figures below, so every one of them is **CONFIRM** against the service manual or a datasheet before use.
> **Scope:** Compiles factory service, diagnostic, and electrical baseline specifications for the Honda CL250 (Type: 8BK-MC57, 249cc DOHC single-cylinder) and shared platform sister models (Rebel 250 / CMX250 MC49, CB250R MC52, CRF250L MD44/MD47).
> **Rule Alignment:** Invariant 2 (Never invent signals; factual cross-references only).

---

## 1. Vehicle Platform Identification

- **Commercial Designation:** Honda CL250 / CL250 Scrambler
- **Vehicle Type Code:** 8BK-MC57
- **Engine Architecture:** 249 cm³, 4-stroke, liquid-cooled, DOHC 4-valve single-cylinder
- **Bore × Stroke:** 76.0 mm × 55.0 mm
- **Compression Ratio:** 10.7 : 1
- **Fuel System:** PGM-FI (Programmed Fuel Injection), 38 mm throttle body
- **Diagnostic Interface:** ISO 19689 4-pin Euro 5 DLC (under-seat, red connector): **CONFIRM** the standard, pin count, colour and position on the bike (hardware-integration §10 item 1)

---

## 2. Electrical, Charging & Starting System Baseline

### 2.1 Battery Specification
- **OEM Model:** GS Yuasa **YTZ8V** (Alternative: Furukawa FTZ8V / Skyrich STZ8V)
- **Type:** VRLA (Valve Regulated Lead-Acid) / AGM (Absorbent Glass Mat), sealed maintenance-free
- **Nominal Voltage:** 12 V
- **Rated Capacity:** **7.0 Ah (10-HR)** / ~7.4 Ah (20-HR)
- **Cold Cranking Amps (CCA):** 120 A (SAE rating @ -18 °C)
- **Open Circuit Voltage (OCV @ 25 °C):**
  - Fully charged: **13.0 V – 13.2 V**
  - Undercharged (needs charge): **< 12.3 V**
  - Severely discharged: < 11.8 V
- **Charging Current Standard:** 0.7 A (Standard, 5–10 h) / 3.5 A (Quick charge, max 1 h)
- **Internal Resistance (R0, typical fresh):** **16 – 22 mΩ** @ 25 °C (**CONFIRM**)

### 2.2 Alternator / AC Generator (Stator)
- **Type:** 3-Phase AC Synchronous Generator with Permanent Magnet Rotor
- **Rated Power Output:** **0.34 kW (340 W) @ 5,000 RPM**
- **Maximum Rectified Output Current:** **~24.3 A @ 14.0 V**
- **Stator Coil Resistance:** ~0.2 – 0.6 Ω (phase-to-phase between yellow leads @ 20 °C)
- **Unloaded AC Voltage (disconnected):** > 45 – 55 VAC @ 5,000 RPM
- **Pole Configuration:** 18 stator teeth / 12 rotor magnets (6 pole pairs)
- **Electrical Frequency:** f_elec = RPM / 60 x 6 pole pairs (**CONFIRM** the pole count). At 1,400 RPM idle: ~140 Hz. At 5,000 RPM: ~500 Hz.
- **Rectified Ripple Fundamental (6 x f_elec):** At 1,400 RPM: ~840 Hz. At 5,000 RPM: ~3,000 Hz. At 9,000 RPM: ~5,400 Hz. A 1 kHz ADC cannot resolve this ripple (Nyquist limit 500 Hz); ripple analysis needs a high-rate burst, which is open (Q-036, D-082 item 4).

### 2.3 Regulator / Rectifier (R/R)
- **Type:** Shunt / Solid-State Regulator with 3-Phase Full-Wave Bridge
- **Regulated Output Voltage:** **14.0 V – 15.0 V** (standard plateau)
- **Factory Diagnostic Pass Limit:** 13.5 V – 15.5 V @ 5,000 RPM
- **Thermal Limit:** Max case operating temperature < 85 °C

### 2.4 Starter Motor & Cranking Profile
- **OEM Part Number:** `31200-KZZ-901` (Mitsuba PMDD series)
- **Rated Output:** **~400 W (0.4 kW)**
- **Rotation:** Counter-Clockwise (CCW), 9-tooth drive pinion
- **Inrush Peak Current (I_peak):** **60 – 90 A** (initial stall current for first 5–20 ms)
- **Steady Cranking Current:** **35 – 50 A** (compression stroke peak-to-valley oscillation)
- **Cranking Speed:** ~350 – 550 RPM (healthy engine and warm oil)
- **Cranking Duration:** Typically 400 – 900 ms from starter push to self-sustained idle

### 2.5 Base Vehicle Quiescent & Key-On Loads
- **Parked Sleep / Quiescent Current:** < 0.5 mA (factory specification)
- **Key-On Engine-Off Base Current:** **~2.8 – 3.4 A** (LED headlight, DRL, taillight, instrument cluster, ECM)
- **Fuel Pump Prime Current:** **2.0 – 3.2 A** for ~2.0 seconds upon key-on

---

## 3. Sensor Selection Cross-Reference for Anomaly Models

| Measurement | Selected Sensor | Range & Rating | Why Selected |
|---|---|---|---|
| **Total Battery & Starter Current** | **Allegro ACS758LCB-200B** (D-082 item 3) | ±200 A bidirectional (10 mV/A, **CONFIRM**) | The 50 A model saturates on the 60-90 A starter inrush; the 200B covers starting and charging without clipping. Series element in the battery/starter cable: own mounting and fuse/cable plan (**CONFIRM** on the bike). |
| **Kelvin Battery Sense** | Fused direct 22 AWG tap | 0 – 16 V DC | Isolates wiring harness voltage drop from battery internal resistance R0. |
| **R/R Surface Temperature** | 10k NTC Thermistor | -40 to +125 °C | Detects regulator thermal runaway and connector oxidation. |
| **Battery Terminal Temperature** | 10k NTC Thermistor | -40 to +85 °C | Electro-chemical temperature compensation for battery aging algorithms. |
| **Battery Voltage ADC** | ADC with DMA on STM32H755 (resolution **CONFIRM**) | 0 – 16 V, 1 kHz sampling (D-079) | Cranking V_min and dV/dt. A high-rate burst for charging-ripple analysis and raw SD logging is open (Q-036). |
