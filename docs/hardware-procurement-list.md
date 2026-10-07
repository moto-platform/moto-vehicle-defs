# Hardware Procurement List — Moto Platform

> Translated from the Turkish original (`archive/tr/donanim-tedarik-listesi.md`). Where this document conflicts with `ARCHITECTURE.md` or `DECISIONS.md`, those take precedence.

**Purpose:** Complete parts list compiled from all subsystems, viewable in one place. Grouped by installation order — buy top to bottom.
**Version:** 1.0 — September 2026

**Usage:** Update the Status column (On hand / Ordered / Arrived / Installed). Prices are September 2026 Turkey estimates — confirm before ordering.

---

## Group 0 — Faz 0 ESP32 Anomali Veri Toplama Donanımı & Vizör HUD PoC

| Part / Entegre | Qty | Detailed Product Description (Ürün Açıklaması & Teknik Detay) | Estimate (TL) | Status |
|---|---|---|---|---|
| **ESP32 DevKit V1 (WROOM-32 30-Pin)** | 2 | Ana Veri Toplama MCU'su & Kask Vizör MCU'su. Çift çekirdek 240MHz, 512KB SRAM, Dahili TWAI (CAN Controller), I2S, I2C, SPI, Wi-Fi 4 ve Bluetooth 4.2/BLE desteği. | 180 - 300 | |
| **SN65HVD230 CAN Transceiver** | 2 | 3.3V Logic Seviyeli CAN Alıcı-Verici Entegresi. OBD2 CAN otobüsünü (500 kbps) ESP32 TWAI (GPIO4/5) pinlerine dönüştürür. | 120 - 220 | |
| **OBD2 Erkek Soket + Kablo (SAE J1962 / EURO5)** | 1 | Motosikletin sele altı DLC teşhis portuna doğrudan takılan 16-pin erkek konnektör ve dayanıklı kablo demeti (Pin 4/5: GND, Pin 6: CAN-H, Pin 14: CAN-L, Pin 16: +12V). | 150 - 300 | |
| **MPU-6050 / BMI270 6-DOF IMU** | 1 | Şasi Dinamikleri Sensörü. 3-Eksen İvmeölçer + 3-Eksen Jiroskop (I2C: GPIO21/22). Yatma açısı, ivmelenme, kasis/çukur ve şasi hareketi (0-50 Hz) için şasiye sabitlenir. | 100 - 220 | |
| **ADXL345 / LIS3DH Yüksek Frekans İvmeölçer** | 1 | Motor Rezonansı & Titreşim Sensörü. 13-bit çözünürlük, 3.2 kHz sampling rate. Doğrudan motor bloğuna cıvatalanarak krank, yanma ve rulman titreşim frekansı (FFT) ölçer. | 120 - 250 | |
| **INMP441 Dijital MEMS I2S Mikrofon** | 2 | 24-bit Dijital I2S Ses Sensörü. 1x Motor Bloğu ses analizi (subap, zincir, yanma sesi), 1x Ön Çevre/Rüzgar Gürültüsü Filtreleme (Noise cancellation reference). EMI parazitizdir. | 180 - 350 | |
| **NEO-6M / NEO-M8N GPS Modülü + Aktif Anten** | 1 | Seri UART (RX2/TX2) GPS Alıcısı. Coğrafi konum, irtifa ve tekerlek kayması/patinaj tespiti için gerçek GPS hızı doğrulama. | 250 - 450 | |
| **MicroSD SPI Modülü + 32GB Industrial Card** | 1 | Offline Veri Kaydedici. İnternet kesintilerinde verileri kayıpsız `.csv` / `.bin` formatında 50 Hz hızında SD karta yazar. | 200 - 380 | |
| **Mini DC-DC Step-Down (MP1584 / LM2596)** | 1 | Wide-Input (7-28V ➔ 5V 3A) Güç Düşürücü. OBD2 Pin 16'daki 12V akü voltajını ESP32 VIN girişi için kararlı 5V seviyesine düşürür. | 70 - 150 | |
| **Koruma Entegreleri Paketi** | 1 set | 1A Cam Sigorta + 1N4007 Ters Polarite Diyodu + 470uF 16V Filtre Kondansatörü + 120Ω CAN Sonlandırma Direnci. | 50 - 100 | |
| **0.39" Micro-OLED / 0.96" OLED + Optik Prizma** | 1 | Kask Vizör HUD Ekranı. High-brightness (>3000 nits) Micro-OLED veya PoC OLED + Combiner prizma mercek ile vizörde 2-3 metre sonsuz odağa telemetri yansıtma. | 400 - 1200 | |
| **BLE TPMS Lastik Basınç/Sıcaklık Sensörü** | 2 | Sibop tipi Bluetooth LE Kablosuz Lastik Basınç/Sıcaklık Sensörü. Anomali modeline basnç düşüşü ve lastik aşırı ısınma verisi sağlar. | 350 - 700 | |
| **Subframe Kutu & Titreşim Sönümleme** | 1 set | IP65 Su Geçirmez / PETG 3D Kutu + Kauçuk Titreşim Takozları (Vibration Damper Rubber Mounts) + Cable Gland Rekorları. | 150 - 400 | |
| **Subtotal (Group 0 - Data Logger + HUD PoC)** | | | **~2,320 - 5,020** | |

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

## Grand Total (Groups 0-10, Core Platform + Data Logger + HUD PoC)

**~11,220 - 21,920 TL** (Tüm Çekirdek Sistem + ESP32 Veri Toplama + Vizör HUD PoC Toplam Maliyeti)

* **Grup 0 (Veri Loglayıcı & Vizör HUD):** ~2,320 - 5,020 TL
* **Grup 1-10 (Tüm Çekirdek Donanım Mimarisi):** ~8,900 - 16,900 TL
* **Grup 11 (Opsiyonel Deneysel Doğrulama - Süspansiyon/Fren Sensörleri):** ~950 - 2,100 TL
* **Grup 12 (İleri Seviye / Faz 2 Eklentileri):** ~5,350 - 11,350 TL

*(Not: Elindeki mevcut parçalar — Raspi 5 8GB, Nextion Ekran, i7 Masaüstü HIL, STM32F103, ESP32 — bu bütçeden düşülmüştür, sıfırdan almaya gerek yoktur).*

## Already On Hand (summary)

- STM32F103 (fault/power control)
- ESP32-S3 board (probably)
- i7 5th gen desktop (HIL host)
- Nextion display
- Raspi 5 8GB
- Raspi 3B+ (role: home server — ECU behavior analysis, offline, within Phase 2 scope)
