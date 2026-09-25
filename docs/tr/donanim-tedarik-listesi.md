# Donanım Tedarik Listesi — Moto Platform

**Amaç:** Tüm alt sistemlerden derlenmiş, tek seferde görülebilir tam parça listesi. Kurulum sırasına göre gruplu — üstten alta doğru satın al.
**Sürüm:** 1.0 — Eylül 2026

**Kullanım:** Durum sütununu güncelle (Elde / Sipariş Edildi / Geldi / Monte Edildi). Fiyatlar Eylül 2026 Türkiye tahmini, sipariş öncesi teyit et.

---

## Grup 1 — Şimdi (moto-vehicle-defs + moto-hil-bench + connectivity-node için)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| STM32F4 Nucleo/Discovery | 1 | HIL simülatör beyni | 300-600 | |
| CAN transceiver (SN65HVD230) | 2 | HIL simülatör + DUT tarafı | 160-300 | |
| STM32F103 | — | Arıza/besleme kontrolü | **Elde** | ✓ |
| Programlanabilir besleme (buck+DAC/dijital pot) | 1 | HIL voltaj senaryoları | 200-400 | |
| OBD2 dişi konnektör + kablo | 1 (HIL için) | DUT'u tezgaha bağlama | 150-300 | |
| ESP32-S3 kartı | — | Connectivity node | **Muhtemelen elde** | |
| i7 5. nesil masaüstü | — | HIL host, Linux+SocketCAN | **Elde** | ✓ |
| **Ara toplam** | | | **~810-1600** | |

## Grup 2 — moto-rt-core (STM32H7) donanımı gelince

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| STM32H7 Nucleo/Discovery (H743/H723) | 1 | Ana domain MCU | 600-1200 | |
| CAN transceiver | 1 | Ana ünite CAN | 80-150 | |
| IMU (6/9 eksen, MPU9250/LSM6DSO) | 1 | Yatış açısı/EKF | 150-300 | |
| GPS modülü (NEO-M8N) + anten | 1 | Konum, hız doğrulama | 250-450 | |
| microSD modül + endüstriyel kart | 1 | Kayıt | 150-300 | |
| **Ara toplam** | | | **~1230-2400** | |

## Grup 3 — Güç Kartı (MCU hattı)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Geniş girişli buck (6-40V→5V, 2-3A) | 1 | MCU besleme | 150-250 | |
| Süper kapasitör + dengeleme + akım sınırlayıcı | 1 set | Güvenli kapanma | 150-300 | |
| INA226 | 1 | Güç izleme (MCU hattı) | 100-300 | |
| TVS diyot, ters polarite MOSFET, sigorta | 1 set | Koruma | 100-250 | |
| **Ara toplam** | | | **~500-1100** | |

## Grup 4 — Anomali Tespiti (Ek Sensörler)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Ayrı ivmeölçer (motor bloğuna) | 1 | Titreşim imzası (mevcut IMU'dan bağımsız) | 150-250 | |
| EGT termokupl + MAX31855 | 1 | Egzoz sıcaklığı | 300-600 | |
| Yağ basıncı/sıcaklık sensörü (opsiyonel) | 1 | Yağlama teşhisi | 300-600 | |
| Mikrofon (I2S, akustik anomali + ses komutu ortak) | 1 | Motor sesi + sesli komut | 250-450 | |
| **Ara toplam** | | | **~1000-1900** | |

## Grup 5 — Kör Nokta (moto-io-node parçası)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| STM32 G0/F0 | 1 | I/O node beyni | 100-250 | |
| 24 GHz radar modülü | 2 | Sol+sağ yan tespit | 600-1600 | |
| Yüksek parlaklık LED (ayna içi) | 2 | Kör nokta göstergesi | 80-200 | |
| CAN transceiver | 1 | I/O node CAN | 80-150 | |
| **Ara toplam** | | | **~860-2200** | |

## Grup 6 — İmmobilizer + Park Modu + Güç (moto-io-node parçası, Grup 5 ile aynı çip)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Bistable röle | 1 | Marş devresi kilitleme | 80-200 | |
| NFC okuyucu (PN532) | 1 | Yetkilendirme | 100-250 | |
| Basit NFC etiketi (NTAG213/215) | 2-3 | Anahtar etiketi | 10-50 | |
| Gizli mekanik bypass anahtarı | 1 | Fail-safe | 50-100 | |
| GSM modül + hat | 1 | Park modu/hırsızlık takibi bağlantısı (WiFi'a ek, taşınabilir bildirim) | 400-900 | |
| **Ara toplam** | | | **~640-1500** | |

**Park modu bildirim kanalı:** GSM üzerinden bağlantı (WiFi'a ek/yedek); hareket algılandığında WhatsApp Business API (Meta Cloud API veya Twilio) üzerinden bildirim gönderilir — bu donanım değil yazılım/servis entegrasyonu, düşük hacimde ek maliyeti yok.

**NFC kriptografik yükseltme (Faz 2):** Basit UID okuyan NTAG yerine kriptografik doğrulamalı MIFARE DESFire etiketine geçiş — klonlanmaya dayanıklılık için. Etiket maliyeti ~50-150 TL/adet; PN532 donanımsal olarak destekler ama gerçek DESFire kimlik doğrulaması ek kütüphane (libfreefare vb.) entegrasyonu gerektirir — yazılım işi, donanım değişmez.

## Grup 7 — Safety Node

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| STM32 G4/F3 | 1 | Viraj güvenlik, izole | 150-400 | |
| CAN transceiver | 1 | Safety node CAN | 80-150 | |
| **Ara toplam** | | | **~230-550** | |

## Grup 8 — Ekran/Gösterge

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Nextion | — | Ana bilgi ekranı | **Elde** | ✓ |
| WS2812 LED şerit/halka | 3+ | Yatış göstergesi (x2) + shift-light | 200-400 | |
| Ortam ışık sensörü (opsiyonel) | 1 | Gündüz/gece | 50-100 | |
| **Ara toplam** | | | **~250-500** | |

## Grup 9 — Linux Node (Raspi 5)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Raspi 5 8GB | — | Linux node | **Elde** | ✓ |
| MCP2515+transceiver veya CAN HAT | 1 | Raspi CAN erişimi | 200-400 | |
| Raspi kamera modülü | 1 | Şerit takip | 500-1500 | |
| Geniş girişli buck (izole hat) | 1 | Raspi ayrı güç | 200-350 | |
| INA226 | 1 | Güç izleme (Raspi hattı) | 100-300 | |
| Pasif soğutucu + nefes alan membran | 1 set | Isı yönetimi (IP67 kutu) | 150-350 | |
| **Ara toplam** | | | **~1150-2900** | |

## Grup 10 — Mekanik/Montaj (genel)

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| IP54/IP67 muhafaza | 3-4 | Ana ünite, güç kartı, Raspi kutusu | 450-1200 | |
| Deutsch DT konnektör seti | 1 set | Araç bağlantıları | 300-600 | |
| PG7 kablo rakoru + O-ring | 4-6 | Sızdırmazlık | 200-400 | |
| Titreşim takozu, kablo, spiral sargı, sigorta | — | Genel montaj | 250-450 | |
| **Ara toplam** | | | **~1200-2650** | |

## Grup 11 — Deneysel Doğrulama

| Parça | Miktar | Amaç | Tahmini (TL) | Durum |
|---|---|---|---|---|
| Dişli (11-13T, deney için) | 1 | Ölçüm sistemi duyarlılık doğrulaması | 300-600 | |
| Süspansiyon potansiyometreleri | 2 | Yol yüzeyi, ayar etkisi | 300-600 | |
| Fren hattı basınç sensörü (transduser + T-parça + sinyal şartlandırma) | 1 | Fren kuvveti analizi, sanal dinamometre girdisi | 350-900 | |
| **Ara toplam** | | | **~950-2100** | |

**Ayrıca alınacak (bütçe/erişime bağlı):** Harici dinamometre referans ölçümü — ticari seans (3000-6000 TL) veya üniversite laboratuvar imkânı (araştırılacak, bulunabilirse maliyetsiz).

## Grup 12 — İleri/Faz 2 (opsiyonel, şimdi alma)

| Parça | Amaç | Tahmini (TL) |
|---|---|---|
| Geniş bant lambda sensörü | AFR/yanma kalitesi | 2000-4000 |
| RTK GPS modülü | Çizgi analizi (yarış telemetrisi) | 2000-4500 |
| TPMS sensörleri | Yarış basınç takibi | 800-1500 |
| Fren kolu yük hücresi | Fren kuvveti analizi (kol tarafı — hattı ölçen sensörden ayrı) | 500-1200 |
| MIFARE DESFire kriptografik NFC etiketi | İmmobilizer klonlanmaya dayanıklılık yükseltmesi | 50-150/adet |

---

## Genel Toplam (Grup 1-10, zorunlu/çekirdek)

**~8.900-16.900 TL** (Grup 6'ya eklenen GSM+NFC etiket kalemleriyle güncellenmiş yaklaşık aralık)

Grup 11-12 hariç. Kademeli al — Grup 1 bu hafta, Grup 2-3 önümüzdeki birkaç hafta, gerisi ilgili alt sistem geliştirilmeye başlanınca.

## Zaten Elde Olanlar (özet)

- STM32F103 (arıza/besleme kontrolü)
- ESP32-S3 kartı (muhtemelen)
- i7 5. nesil masaüstü (HIL host)
- Nextion ekran
- Raspi 5 8GB
- Raspi 3B+ (rol: ev sunucusu — ECU davranış analizi, offline, Faz 2 kapsamında)
