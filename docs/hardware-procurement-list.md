# Hardware Procurement List — moto-platform

> Where this list conflicts with `ARCHITECTURE.md` or `DECISIONS.md`, those take precedence.

**Version:** 2.0 — 2026-10-17. Rewritten for D-072 (one dual-core STM32H755 instead of the H7 + G4 + G0 set, io-node retired) and D-073 (helmet unit: ESP32-S3 HUD + voice).
**How to use:** buy wave by wave, top to bottom; update the Status column (On hand / Ordered / Arrived / Installed).
**Prices:** Turkish store prices as shown on 2026-10-17 (TL, VAT as the store shows it). "n/v" = link seen but price or stock not verified (the marketplace blocked automated reading). Prices and stock change; check before ordering. Single-store cart: Motorobit covers most small parts; Direnc is cheaper for some; marketplaces (Hepsiburada, Trendyol, n11) are the only source for TPMS, high-endurance microSD, Deutsch DT and some cables.

## On hand

| Item | Use |
|---|---|
| ESP32-S3 DevKitC-1 (N16R8, FT232R) | bike ESP32 (conn): Phase 0 tester today, platform-bus ↔ BLE bridge later (D-073) |
| SN65HVD230 CAN transceiver ×1 | bike ESP32 vehicle bus (check the on-board 120 Ω, hardware-integration §2) |
| MPU-6500 IMU | chassis IMU (D-032); moves to rt-core (M7) later |
| NEO-M8N GPS + antenna | GPS (D-060); moves to rt-core (M7) later |
| Nextion display | deferred (D-073 item 7) |
| Raspberry Pi 5 8 GB, Raspberry Pi 3B+ | linux-node; 3B+ home server (Phase 2) |
| STM32F103 | HIL fault/power node (Q-003 resolved by D-072) |
| i7 desktop | HIL host / CI runner |

## Wave 1 — now: the domain-controller board and the on-bike build

| Item | Qty | Why | Link | Price | Status |
|---|---|---|---|---|---|
| **NUCLEO-H755ZI-Q** | 1 | M7 = rt-core, M4 = safety partition (D-072) | [SAMM (STM Nucleo category)](https://market.samm.com/en/stm-nucleo) · [Farnell TR](https://tr.farnell.com/stmicroelectronics/nucleo-h755zi-q/development-board-32bit-arm-cortex/dp/4225702) | 2,904.30 TL (SAMM, stock n/v) · Farnell n/v | |
| SN65HVD230 module | 3 | M7 FDCAN1 (vehicle), FDCAN2 (platform), 1 spare | [F1Depo](https://www.f1depo.com/urun/sn65hvd230-can-modulu) · [Hepsiburada](https://www.hepsiburada.com/alkatronik-sn65hvd230-can-modulu-pm-HBC00000FDLXH) | ~112 TL (F1Depo out of stock) · n/v | |
| MPU-6500 module (SPI) | 1 | the M4's own fallback IMU (D-042), same driver family as the chassis IMU | [Motorobit GY-6500](https://www.motorobit.com/mpu6500-6-axis-acceleration-and-gyro-sensor-gy-6500) · [Trendyol CJMCU-116](https://www.trendyol.com/robolink-teknoloji/cjmcu-116-mpu-6500-6-eksen-ivme-ve-gyro-sensoru-spi-i2c-p-49850291) | n/v | |
| USB-CAN adapter (gs_usb / CANable) | 1 | platform-bus sniffing, HIL; on the vehicle bus **listen-only only** (invariant 1) | [Motorobit CANable 2.0](https://www.motorobit.com/makerbase-canable-20-usb-can-analizor-donusturucu-modul) · [Hepsiburada CANable 2.1](https://www.hepsiburada.com/alkatronik-canable-v2-1-usb-can-fd-bus-analizor-monitor-izleyici-iletisim-cevirici-hata-ayiklayici-transceiver-pm-HBC0000702X2X) | 1,313 TL (out of stock) · n/v | |
| Honda DLC → OBD2 (J1962) adapter | 1 | DLC access without cutting the harness. **Check the connector on the bike first** (4- or 6-pin); the CL250 data path is CAN (D-019) | [Trendyol 6-pin → 16-pin](https://www.trendyol.com/streak/honda-iv-motosiklet-obd2-ariza-tespit-cevirici-kablo-6-pin-to-16-p-113958099) · [Hepsiburada 3/4/6-pin set](https://www.hepsiburada.com/passing-motosiklet-yamaha-3pin-4pin-ve-honda-6pin-obd2-teshis-baglanti-kablosu-yamaha-motosiklet-obd-uzatma-kablosu-yurt-disindan-pm-HBC00005P3SQQ) | n/v | |
| microSD module + 32 GB high-endurance card | 1 + 1 | rt-core logging (D-045); the phone stays the Phase 0 path | [Direnc module](https://www.direnc.net/arduino-micro-sd-kart-modulu) · [SanDisk High Endurance](https://www.hepsiburada.com/sandisk-high-endurance-micro-sd-kart-32-gb-uhs-i-class-10-100-mb-s-okuma-hizi-ile-pm-HB000017A8SV) · [Kingston High Endurance](https://www.hepsiburada.com/kingston-high-endurance-32gb-micro-sd-95mb-s-uhs-i-sdce-32gb-pm-HB00000LAXY0) | 29 TL · ~900-2,000 TL (n/v) | |

**Power chain (ignition-switched line, hardware-integration §3):**

| Item | Qty | Why | Link | Price | Status |
|---|---|---|---|---|---|
| Buck 5 V, **input ≥ 53 V** | 1 | MCU/ESP supply; survives load-dump peaks behind the TVS. Not the MP1584 (28 V max) | [Direnc LM2596HVS 4.5-53 V, 3 A](https://www.direnc.net/lm2596hvs-dc-kademeli-ayarlanabilir-modul-3a-45v~53v) · [Motorobit HW-788 6-100 V, 2 A](https://www.motorobit.com/hw-788-dc-6-100v-to-5v-2a-voltaj-dusurucu-modulu) | 137 TL (out of stock) · 126 TL | |
| TVS, bidirectional | 2 | input clamp | [Direnc SMBJ30CA](https://www.direnc.net/smbj30ca-ht-smd-30v-600w-transil-diyot) (SMBJ24CA out of stock at [Özdisan](https://www.ozdisan.com/en/p/tvs-diodes-386/stm-smbj24ca-tr-419047)) | 3.47 TL | |
| Schottky 1N5822 (reverse polarity) | 2 | | [Motorobit](https://www.motorobit.com/1n5822-3a-40v-diyot) | 4 TL | |
| Waterproof blade-fuse holder + 2 A fuses | 1 + 5 | | [holder](https://www.motorobit.com/su-gecirmez-minimicro-bicak-sigorta-yuvasi-18awg) · [fuse](https://www.motorobit.com/2a-mikro-oto-sigorta-bicak-sigorta) (match the size) | 25 + 6 TL | |
| INA226 module | 1 | supply current, sleep current < 1 mA | [Direnc](https://www.direnc.net/ina226-iki-yonlu-akim-guc-izleme-sensor-modulu) | 105 TL | |
| Electrolytic 470 µF/35 V + ceramic 100 nF | few | input filter | local / any store | — | |

**Mechanical, wiring, tools:**

| Item | Qty | Link | Price | Status |
|---|---|---|---|---|
| IP65/IP67 ABS box (~100×70×40 for the ESP32 unit, ~160×90×60 for the H755 Nucleo-144) | 2 | [Robolink boxes](https://www.robolinkmarket.com/arama?q=kutu) (170×120×55 IP67 seen); Direnc "Plastik Kutu" category | 442.50 TL (170×120×55) | |
| PG7 cable glands | 6 | [Motorobit](https://www.motorobit.com/pg-7-3-7-mm-polyamid-rakoru) | 2.78 TL each | |
| Deutsch DT connector kit (2-6 pin) | 1 | [Hepsiburada Deutsch](https://www.hepsiburada.com/deutsch) | n/v | |
| Deutsch DT crimp tool | 1 | [Hepsiburada Jr Ready](https://www.hepsiburada.com/jrready) · [n11](https://www.n11.com/urun/jrready-act-ly-terminal-sikma-pensesi-crimp-tools-46231372) (confirm the DT model) | n/v | |
| JST-XH 560-piece set | 1 | [Motorobit](https://www.motorobit.com/jst-xhxhp-254mm-tunic-connector-set-560-pieces) | 454.50 TL | |
| JST crimp tool (SN-28B class) | 1 | [Hepsiburada Iwiss SN-2549](https://www.hepsiburada.com/guangdong-spirit-iwiss-crimper-sn-2549-sn28b-sn01bm-dupont-xh2-54-fis-yayli-terminal-sikma-aletleri-2-8-3-0-3-96-4-8-sikma-pensesi-pm-HBC00001PCDHA) | n/v | |
| Double-sided perfboard 7×9 and 9×15 cm | 2 + 2 | [Motorobit 7×9](https://www.motorobit.com/7x9cm-epoxy-cift-tarafli-delikli-plaket) · [Robolink 9×15](https://www.robolinkmarket.com/9x15-cift-yuzlu-delikli-pertinaks) | 37.88 TL · 100.50 TL (sold out) | |
| Shielded 2-core cable (CAN, LiYCY 2×0.22/0.5) | 3 m | [Direnc shielded 2-core](https://www.direnc.net/arama?q=blendajlı+kablo) · [n11 Erse 2×0.50 LiYCY](https://m.n11.com/urun/erse-2x050-liycy-blendajli-100-bakir-kablo-1-m-13177603) | 47.08 TL/m · n/v | |
| 22 AWG silicone wire (red/black) | 3 m each | [Motorobit](https://www.motorobit.com/22-awg-silikon-kablo-kirmizi-1-metre) | 17.67 TL/m | |
| Spiral wrap 6-8 mm | 5 m | [n11 8 mm](https://www.n11.com/urun/5-metre-kablo-toplama-spirali-siyah8mm-14731594) · [Hepsiburada 6 mm](https://www.hepsiburada.com/unelsis-6mm-10-metre-helezon-sprial-pm-HBC0000909IHE) | n/v | |
| Heat-shrink (several sizes) | — | [Motorobit](https://www.motorobit.com/isi-ile-daralan-makaron-48mm-1-metre) | 10.10 TL/m | |
| 120 Ω resistors | 10 | platform-bus ends only, never on the vehicle bus | [Motorobit](https://www.motorobit.com/120r-14w-direnc-10-adet) | 2.53 TL | |
| Vibration damping (silicone mounts/tape); rigid IMU bracket | — | local | — | |
| Logic analyzer 24 MHz 8-ch | 1 | [Robotistan](https://www.robotistan.com/usb-lojik-analizor-24-mhz-8-kanal) | 467.95 TL | |
| Multimeter | 1 | [Motorobit DT-830D](https://www.motorobit.com/dijital-avometre-multimetre-olcu-aleti-dt-830d) | 176.75 TL | |

Wave 1 with verified prices: about 7,500-8,500 TL, plus the n/v items.

## Wave 2 — anomaly sensors (D-044, hardware-architecture §5b.9)

New sensors need their signals defined through `/signal-change` (and Q-025) before code; all are QM inputs, never safety-partition inputs.

| Item | Qty | Why | Link | Price | Status |
|---|---|---|---|---|---|
| ADXL345 (SPI) | 2 | engine-block vibration (documented, high priority) + swing-arm/chain vibration (new). Mount where the part stays below 85 °C | [Motorobit](https://www.motorobit.com/adxl345-3-eksen-ivme-olcer-gy-291) · [Robotistan](https://www.robotistan.com/adxl345-3-eksen-ivme-olcer-triple-axis-accelerometer-breakout-adxl345) | 126.25 · 155.38 TL | |
| MAX31856 thermocouple module (MAX31855 alt.) | 1 | EGT | [Motorobit MAX31856](https://www.motorobit.com/max31856-yuksek-hassasiyetli-a/d-donusturucu-termokupl-modulu) · [SAMM MAX31855](https://market.samm.com/max31855-thermocouple-amplifier) | 555.50 TL · 1,010 TL (out of stock) | |
| K-type probe, M6, 0-800 °C | 1 | EGT probe | [Motorobit 50 cm](https://www.motorobit.com/k-tip-0-800c-m6-termokupl-50cm) | 126.25 TL | |
| EGT weld-in bung | 1 | the probe needs a bung welded into the header: a local exhaust/welding shop (no TR store found) | local | — | |
| INMP441 I2S microphone | 1 | engine-facing microphone on the Raspi (D-044) | [Direnc](https://www.direnc.net/inmp441-mems-i2s-cok-yonlu-mikrofon-modulu) | 145.29 TL | |
| ACS758 50 A hall current sensor | 1 | battery current: charging system, regulator faults, cranking profile (new) | [Motorobit](https://www.motorobit.com/acs758lcb-50a-linear-hall-current-sensor-module) | 353.50 TL | |
| BME280 | 1 | ambient temperature, pressure, humidity as context (new) | [Robolink](https://www.robolinkmarket.com/bme-280-barometrik-basinc-nem-ve-sicaklik-sensor-karti) | 309 TL | |
| LJ12A3-4-Z/BX inductive sensor | 2 | wheel speed from the brake-disc bolts, independent of the ECU (new; helps Q-031, wheel_slip, final drive). Output needs level shifting to 3.3 V | [Direnc](https://www.direnc.net/enduktif-npn-proximity-sensor-lj12a3-4-zbx) | 116.24 TL | |
| BLE TPMS (motorcycle, 2 external sensors) | 1 set | tyre pressure/temperature. Many sets are 433 MHz with their own display: buy only a Bluetooth one | [Trendyol Powermaster](https://www.trendyol.com/powermaster/pm-28656-motosiklet-kablosuz-lastik-basinc-ve-sicaklik-izleme-sistemi-tpms-p-1042126095) · [n11](https://m.n11.com/lasonstiges-2-harici-sensorlu-motosiklet-tpms-moto-lastik-basinci-izleme-sistemi-P675123074) | n/v | |
| Oil pressure/temperature sensor (optional) | 1 | lubrication faults | not searched | 300-600 TL (estimate) | |
| Inductive spark-lead pickup (optional) | 1 | ECU-independent RPM and misfire (new) | not searched | — | |

## Wave 3 — helmet unit (D-073, hardware-architecture §5b.4a)

| Item | Qty | Stage | Link | Price | Status |
|---|---|---|---|---|---|
| ESP32-S3 N16R8 | 1 | H0 | [Direnc](https://www.direnc.net/esp32-s3-n16r8-wifi-bluetooth-board) · [Robolink](https://www.robolinkmarket.com/esp32-s3-n16r8-wifi-ve-bluetooth-gelistirme-karti) | 610.23 · 696 TL | |
| 0.96" SSD1306 OLED | 1 | H0 desk display | [Direnc](https://www.direnc.net/128x64-096-4-pin-oled-grafik-lcd-ekran-ssd1306-i2c-mavi) | 162.73 TL | |
| INMP441 I2S microphone | 1 | H0 helmet mic | [Direnc](https://www.direnc.net/inmp441-mems-i2s-cok-yonlu-mikrofon-modulu) | 145.29 TL | |
| Push button (PTT) | 1 | H0 | local | — | |
| 0.42"/0.49" micro-OLED | 1 | H1. Not daylight-bright; a brighter micro-OLED may be needed after H1 | [F1Depo 0.49" 64×32 I2C](https://www.f1depo.com/urun/0-40-inc-64x32-oled-ekran-i2c-iic) · [F1Depo 0.42" I2C/SPI](https://www.f1depo.com/urun/0-42-inc72x40-oled-lcd-ekran-i2c-spi-ssd1306-4-pin) | 240 TL | |
| Beam-splitter cube 20-25 mm (50:50) | 1 | H1 combiner | [AliExpress 25 mm](https://www.aliexpress.com/item/1005001280015931.html) · [AliExpress 20 mm](https://www.aliexpress.com/item/1005007594739464.html) | n/v (import) | |
| MAX98357A I2S amplifier | 1 | H1 voice prompts | [n11](https://www.n11.com/urun/max98357-i2s-5v-3w-ses-yukseltici-amfi-class-d-dijital-ses-muzik-27456041) · [SAMM Adafruit](https://market.samm.com/en/adafruit-i2s-3w-class-d-amplifier-breakout-max98357a-en) | n/v · 545.63 TL (out of stock) | |
| Thin 8 Ω 1-2 W speaker (20-40 mm) | 1 | H1 | [Direnc search](https://www.direnc.net/arama?q=hoparlör) (8 Ω 2 W 20×40 mm, sold out) | 159.53 TL | |
| 3.7 V LiPo 1000-1500 mAh **with protection PCB** | 1 | H1 | [Robolink PX663538 1000 mAh](https://www.robolinkmarket.com/power-xtra-px663538-37v-1000mah-li-po-pil-soketli-devreli) · [Hepsiburada 803450 1500 mAh](https://www.hepsiburada.com/803450-3-7v-1500mah-li-polymer-pil-devreli-1-5a-pm-HBC0000I98EE1) | 274.50 TL (out of stock) · n/v | |
| TP4056 Type-C charger, protected (DW01) | 1 | H1 | [Motorobit protected](https://www.motorobit.com/tp4056-37v-charging-circuit-protected-mode-type-c) · [Robotistan](https://www.robotistan.com/tp4056-type-c-1s-37v-lipo-li-ion-pil-sarj-devresi) | n/v · 21.68 TL | |
| Slide switch | 1 | H1 | [Robotistan search](https://www.robotistan.com/arama?q=slide) | — | |
| Clip-on housing | 1 | H1 | 3D print (PETG/ASA); never drill or glue the helmet (D-073 item 2) | — | |

## Wave 4 — safety outputs, blind spot, immobilizer (M4 safety partition, D-072)

| Item | Qty | Why | Link | Price | Status |
|---|---|---|---|---|---|
| HLK-LD2451 24 GHz vehicle-detection radar | 2 | blind spot (hardware-architecture §5b.1). HLK-LD2410/2450 are people sensors: not suitable | [openelab](https://openelab.io/de/products/hlk-ld2451-motorcycle-tricycle-blind-spot-auxiliary-radar-module) · [uelectronics](https://uelectronics.com/producto/hlk-ld2451-radar-de-ondas-milimetricas-24ghz-para-deteccion-de-vehiculos/) | n/v (import) | |
| WS2812B ring, 12 LED | 2 | cornering LED ring (D-041) | [Robotistan 12](https://www.robotistan.com/neopixel-12li-halka) · [Robotistan 16](https://www.robotistan.com/16li-neopixel-halka) | 71.67 · 374 TL | |
| High-brightness LEDs for the mirrors | 2 | blind-spot indicator, readable in sunlight | local | — | |
| Dead-man parts: 74HC123 (retriggerable monostable) + logic-level P-MOSFET | 2 sets | one option for the D-072 item 5 rule (a dead M4 must not leave a frozen GREEN); the other is a moving alive pixel in software | local | — | |
| Bistable (latching) relay | 1 | starter-relay coil (invariant 6) | local | 80-200 TL (estimate) | |
| PN532 NFC reader + NTAG213/215 tags | 1 + 3 | immobilizer authorization | not searched | 110-300 TL (estimate) | |
| Hidden bypass switch | 1 | invariant 6 | local | — | |
| WS2812B strip 60 LED/m (shift-light, optional) | 1 m | M7 | [Robotistan 5 m roll](https://www.robotistan.com/ws2812b-addressable-rgb-led-strip-60-led-ip20-5m-300-led) | 1,038.89 TL (5 m) | |

## Wave 5 — Raspberry Pi 5 on the bike

| Item | Qty | Link | Price | Status |
|---|---|---|---|---|
| CAN HAT (2-channel, isolated) or MCP2515 module | 1 | [SAMM Waveshare 2-CH isolated](https://market.samm.com/en/raspberry-pi-2-kanalli-izole-genisletme-karti) · [Robolink MCP2515](https://www.robolinkmarket.com/mcp2515-canbus-spi-modulu) | 1,338.81 TL (out of stock) · 127.50 TL | |
| 12 V → 5 V **5 A** buck (the Pi 5 needs 5 V 5 A; the Wave 1 buck cannot feed it) | 1 | [Motorobit HCW-P715 9-36 V → 5 V 5 A](https://www.motorobit.com/hcw-p715-9-36v-to-5v-5a-voltage-reducer-regulator-board) | n/v | |
| INA226 (Pi line) | 1 | [Direnc](https://www.direnc.net/ina226-iki-yonlu-akim-guc-izleme-sensor-modulu) | 104.61 TL | |
| Camera module (lane tracking) | 1 | not searched | 500-1,500 TL (estimate) | |
| Passive heatsink + breathable membrane, IP67 box | 1 set | not searched | 150-350 TL (estimate) | |

## Wave 6 — HIL bench (after Q-009)

| Item | Qty | Link | Price | Status |
|---|---|---|---|---|
| NUCLEO-F446RE (HIL simulator) | 1 | [SAMM](https://market.samm.com/en/stm-nucleo) · [Direnc](https://www.direnc.net/arama?q=nucleo) | 1,288.58 · 1,685.87 TL | |
| SN65HVD230 module | 2 | see Wave 1 | ~112 TL | |
| Programmable supply (buck + DAC/digital pot) | 1 | not searched | 200-400 TL (estimate) | |
| OBD2 female connector + cable | 1 | not searched | 150-300 TL (estimate) | |

## Later — park mode, validation, Phase 2

| Item | Purpose | Estimate (TL) |
|---|---|---|
| GSM module + line | park-mode notification (rt-core, QM) | 400-900 |
| Sprocket 11-13T | measurement sensitivity check | 300-600 |
| Suspension potentiometers ×2 (Q-010) | road surface, setup effect | 300-600 |
| Brake line pressure sensor | brake force, virtual dyno | 350-900 |
| Wideband lambda, RTK GPS, brake-lever load cell, MIFARE DESFire tags | Phase 2, do not buy now | 2,000-4,500 each class |

## Removed from v1.0

- STM32G4 and STM32G0 boards and their transceivers (D-072); NUCLEO-H743ZI2 (obsolete at distributors) and the H743/H723 choice (Q-019 resolved).
- ESP32 DevKit V1 (WROOM-32): both ESP32 units are ESP32-S3 (D-073).
- MP1584 buck (28 V input limit), MPU9250 (discontinued), the "9-axis LSM6DSO" line (it is a 6-axis part).
- The separate on-bike microSD/ESP logging of the old Group 0 (D-045: logging is rt-core's).
