# Özellik Havuzu, Donanım Mimarisi ve Açık Kaynak Referansı

**Proje:** Motosiklet gömülü teşhis, telemetri ve sürücü destek platformu
**Amaç:** Uzun vadeli geliştirme havuzu (aday kalemler + önceliklendirme), donanım mimarisi analizi ve açık kaynak/donanım referansı — tek dosyada
**Sürüm:** 2.0 — Eylül 2026

**İçindekiler:** Bölüm 1-13 fonksiyon/teknoloji kategorileri · 14 öne çıkanlar · 15 havuz dışı · 16 önceliklendirme çerçevesi · 17 donanım mimarisi analizi · 18 açık kaynak ekosistemi ve donanım maliyetleri

---

## Nasıl Kullanılır

Bu doküman bir taahhüt listesi değil, **aday havuzudur**. Her kalem için:

- **Efor:** kaba saat tahmini (önceliklendirme girdisi)
- **Bağımlılık:** önce hangi kalemin bitmiş olması gerektiği
- **Değer:** K = kariyer/mülakat değeri, T = tez/akademik değer, U = kullanım değeri
- **Açık kaynak:** ilgili proje veya standart

Önceliklendirme önerisi: yüksek değer + düşük efor + az bağımlılık olanlar önce.

---

## 1. Temel Protokol Katmanı

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| P1 | CAN sürücü + hata durum makinesi | 25-35 | — | K,T | ESP-IDF TWAI, SocketCAN |
| P2 | ISO-TP taşıma katmanı | 40-60 | P1 | K,T | ISO 15765-2, `isotp-c`, `can-isotp` |
| P3 | UDS teşhis sunucusu | 60-90 | P2 | K,T | ISO 14229, `udsoncan` (referans) |
| P4 | UDS teşhis istemcisi (tarayıcı) | 25-40 | P2 | K,U | `python-OBD`, `udsoncan` |
| P5 | OBD2 tam mod desteği (01-0A) | 15-25 | P1 | U | SAE J1979 |
| P6 | CAN FD desteği | 20-30 | P1 | K | ISO 11898-1 |
| P7 | DoIP (Diagnostics over IP) | 40-60 | P3 | K | ISO 13400 |
| P8 | CANopen desteği | 30-50 | P1 | — | CiA 301, `CANopenNode` |
| P9 | J1939 desteği (ticari araç) | 30-50 | P1 | K | SAE J1939, `python-j1939` |

**Not P7:** DoIP, yeni nesil araçlarda CAN teşhisinin yerini alıyor. Ethernet tabanlı. Sektörel görünürlüğü yüksek.

---

## 2. Yazılım Mimarisi ve Platform

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| A1 | Katmanlı modüler mimari (HAL/servis/fonksiyon) | 40-60 | — | K,T | AUTOSAR SWC/RTE mantığı |
| A2 | **COVESA VSS sinyal modeli** | 25-40 | A1 | K,T | Vehicle Signal Specification |
| A3 | Zephyr RTOS'a geçiş/port | 60-100 | A1 | K | Zephyr Project |
| A4 | SOME/IP servis haberleşmesi | 50-80 | A1 | K | `vsomeip` (COVESA) |
| A5 | DDS / Zenoh pub-sub katmanı | 40-70 | A1 | K | Cyclone DDS, Eclipse Zenoh |
| A6 | micro-ROS entegrasyonu | 40-60 | A1 | — | micro-ROS, ROS 2 |
| A7 | Eclipse Kuksa veri aracısı | 30-50 | A2 | K,T | Eclipse Kuksa (SDV) |
| A8 | Eclipse Velocitas uygulama çerçevesi | 40-60 | A7 | K | Eclipse Velocitas |
| A9 | Rust ile gömülü modül (bir modül örnek) | 40-70 | A1 | K | `embassy`, `embedded-hal` |
| A10 | Konteynerleştirilmiş araç uygulamaları | 50-80 | Linux birimi | K | Docker, Eclipse Leda |
| A11 | Hipervizör / sanallaştırma denemesi | 60-100 | Linux birimi | K | Xen, Jailhouse |

**A2 özellikle önerilir:** VSS, araç sinyallerinin standart tanım modeli. "Araç bağımsız sinyal tanım dosyası" fikrinin sektörel karşılığı tam olarak bu. Kendi şemanı uydurmak yerine VSS kullanmak, hem tezde hem mülakatta ağır basar. Efor düşük, değer yüksek.

**A7/A8:** Eclipse SDV çalışma grubunun projeleri. Bosch, Microsoft, Red Hat destekli. Yazılım tanımlı araç mimarisinin açık kaynak referans uygulaması.

---

## 3. Güvenlik (Functional Safety)

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| S1 | HARA (tehlike analizi ve risk değerlendirme) | 25-40 | — | K,T | ISO 26262-3 |
| S2 | FMEA / FTA (hata ağacı analizi) | 20-35 | S1 | K,T | ISO 26262, IEC 61025 |
| S3 | Gereksinim–test izlenebilirlik matrisi | 20-30 | S1 | K,T | ASPICE |
| S4 | Watchdog ve güvenli duruma geçiş | 15-25 | A1 | K,T | ISO 26262-5 |
| S5 | Girişimden bağımsızlık (freedom from interference) | 25-40 | A1 | K,T | ISO 26262-6 |
| S6 | MISRA C uyum ve statik analiz | 20-35 | — | K | MISRA C:2012, `cppcheck`, `clang-tidy` |
| S7 | SOTIF analizi (beklenen işlev güvenliği) | 25-40 | S1 | T | ISO 21448 |
| S8 | Güvenlik durumu makinesi ve arıza yönetimi | 30-50 | S4 | K,T | — |

---

## 4. Siber Güvenlik

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| C1 | TARA (tehdit analizi ve risk değerlendirme) | 25-40 | — | K,T | ISO/SAE 21434 |
| C2 | Güvenli önyükleme (secure boot) | 40-60 | B1 | K | ESP32 Secure Boot, TF-M |
| C3 | Flash şifreleme | 15-25 | C2 | K | ESP32 Flash Encryption |
| C4 | CAN saldırı tespiti (IDS) | 50-80 | P1 | K,T | `CaringCaribou`, ROAD dataset |
| C5 | Mesaj kimlik doğrulama (SecOC benzeri) | 40-60 | P1 | K | AUTOSAR SecOC |
| C6 | Güvenli OTA (imza doğrulama, rollback koruması) | 40-70 | B1 | K,T | **Uptane** standardı |
| C7 | SBOM üretimi ve bağımlılık takibi | 10-20 | — | K | CycloneDX, SPDX |
| C8 | Sızma testi senaryoları (kendi sistemine) | 30-50 | C4 | T | `CaringCaribou`, `SavvyCAN` |
| C9 | UN R155/R156 uyum dokümantasyonu | 20-30 | C1 | K,T | UNECE regülasyonları |

**C6 (Uptane):** Otomotiv OTA güvenliğinin fiili standardı. Otomotiv siber güvenliğinde bilinmesi beklenen bir konu.

---

## 5. Bootloader ve Güncelleme

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| B1 | UDS üzerinden bootloader (0x34/36/37) | 80-120 | P3 | K,T | ISO 14229 |
| B2 | A/B bank + atomik geçiş | 30-50 | B1 | K | MCUboot mantığı |
| B3 | Güç kesintisinde geri alma (rollback) | 25-40 | B2 | K,T | — |
| B4 | Delta güncelleme (fark bazlı) | 30-50 | B1 | K | `bsdiff`, `detools` |
| B5 | Kampanya yönetimi (sunucu tarafı) | 40-70 | B1 | K | Eclipse hawkBit |
| B6 | Linux tarafı OTA (ikinci birim varsa) | 40-60 | Linux birimi | K | RAUC, SWUpdate, Mender |

---

## 6. Test, Doğrulama ve HIL

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| H1 | HIL tezgahı donanımı | 40-60 | — | K,T | — |
| H2 | Senaryo motoru + otomatik değerlendirme | 50-70 | H1 | K,T | — |
| H3 | Araç bağımsız tanım katmanı | 25-40 | H2, A2 | K,T | VSS, DBC (`cantools`) |
| H4 | Ölçüm katmanı (zaman damgası, gecikme, bus yükü) | 30-50 | H2 | K,T | — |
| H5 | Arıza enjeksiyonu (elektriksel + protokol) | 30-50 | H1 | K,T | ISO 7637-2 (kısmi) |
| H6 | Kayıt / tekrar oynatma modu | 20-30 | H1 | K,U | `candump`/`canplayer` mantığı |
| H7 | Donanımda CI/CD (self-hosted runner) | 30-50 | H2 | K,T | GitHub Actions, Jenkins |
| H8 | Birim test altyapısı (gömülü C) | 25-40 | A1 | K | Unity, Ceedling, CMock |
| H9 | Kod kapsama ölçümü | 10-20 | H8 | K | gcov, lcov |
| H10 | **Renode ile sanal donanım simülasyonu** | 30-50 | — | K,T | Renode (Antmicro) |
| H11 | ASAM XIL API uyumlu arayüz | 40-60 | H2 | K | ASAM XIL |
| H12 | Simulink plant modeli + MIL/SIL/PIL zinciri | 80-120 | H2 | K,T | MATLAB/Simulink |
| H13 | OpenSCENARIO ile senaryo tanımı | 30-50 | H2 | K | ASAM OpenSCENARIO |

**H10 (Renode):** Donanım olmadan MCU'yu simüle eden açık kaynak araç. CI'da donanımsız test koşturmanı sağlar — fiziksel tezgahın tamamlayıcısı. Az bilinen ama etkileyici bir kalem.

---

## 7. Veri, Kayıt ve Platform

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| D1 | Telemetri toplama ve kayıt altyapısı | 50-80 | P1, A1 | T,U | — |
| D2 | **MDF4 formatında kayıt** | 25-40 | D1 | K,T | ASAM MDF, `asammdf` |
| D3 | **MCAP formatı desteği** | 20-30 | D1 | K | MCAP (Foxglove) |
| D4 | Zaman senkronizasyonu (GPS/PTP) | 25-40 | D1 | K,T | IEEE 1588 PTP |
| D5 | İstemci-sunucu senkronizasyon | 50-80 | D1 | U | MQTT, Mosquitto |
| D6 | Zaman serisi veritabanı + gösterge paneli | 30-50 | D5 | U | InfluxDB/TimescaleDB + Grafana |
| D7 | **Foxglove Studio ile veri görselleştirme** | 15-25 | D3 | K,U | Foxglove |
| D8 | PlotJuggler entegrasyonu | 10-20 | D1 | U | PlotJuggler |
| D9 | Hugging Face veri seti yayını | 20-35 | D1 | T | HF Datasets, veri kartı |
| D10 | Veri anonimleştirme (GPS kırpma, kimlik) | 10-20 | D9 | T | — |
| D11 | Sürüş sonu rapor üretimi | 25-40 | D1 | U | — |
| D12 | Harita üstü görselleştirme (hız/yatış/fren katmanı) | 30-50 | D11 | U | Leaflet, MapLibre |

**D2 (MDF4):** Otomotiv ölçüm verisinin standart formatı. Kendi ikili formatını uydurmak yerine MDF4 kullanmak, veriyi CANape/CANoe gibi araçlarla açılabilir kılar. Mülakatta somut bir ayrıntı.

**D7 (Foxglove):** Robotik ve otomotivde yaygınlaşan açık kaynak veri görselleştirme aracı. Kendi arayüzünü yazmadan profesyonel görünümlü analiz.

---

## 8. Edge AI / TinyML

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| M1 | Sesli komut tanıma (keyword spotting) | 60-90 | A1 | K,T | TFLite Micro, ESP-NN |
| M2 | Sürüş bağlamı sınıflandırma (IMU) | 40-60 | D1 | T | TFLite Micro, Edge Impulse |
| M3 | Yol yüzeyi sınıflandırma | 40-60 | M2 | T | — |
| M4 | Anomali tespiti (tek sınıflı öğrenme) | 60-100 | D1 | T | scikit-learn, TFLite |
| M5 | Arıza tahmin modeli (kontrollü arıza verisiyle) | 100-200 | D1, D9 | T | — |
| M6 | Sürücü kimliği tanıma (sürüş imzası) | 30-50 | M2 | T | — |
| M7 | Model regresyon testi (boyut/gecikme/doğruluk) | 20-35 | H7, M1 | K,T | — |
| M8 | Nicemleme ve budama optimizasyonu | 25-40 | M1 | K | TFLite, ONNX Runtime |
| M9 | Ses tabanlı motor sağlık analizi | 60-100 | M4 | T | MIMII/MaFaulDa ön eğitim |

---

## 9. Araç Fonksiyonları

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak |
|---|---|---|---|---|---|
| F1 | Viraj güvenlik uyarısı (fizik + EKF + ML) | 60-100 | D1 | T,U | — |
| F2 | EKF ile durum/parametre kestirimi | 50-80 | D1 | K,T | `Eigen`, `kalman` |
| F3 | Sanal dinamometre | 60-90 | F2 | T,U | — |
| F4 | Vites tespiti ve vites koçluğu | 10-20 | D1 | U | — |
| F5 | Tüketim ve menzil tahmini | 10-20 | D1 | U | — |
| F6 | Akü sağlık göstergesi | 15-25 | D1 | T,U | — |
| F7 | Düşme / kaza tespiti | 15-25 | D1 | U | — |
| F8 | Bakım takibi (yük bazlı) | 10-20 | D1 | U | — |
| F9 | Sürüş agresiflik skoru | 10-15 | D1 | U | — |
| F10 | Fren performans analizi | 10-20 | D1 | U | — |
| F11 | Segment / tur karşılaştırma | 25-40 | D12 | U | — |
| F12 | Asistan profilleri (şehir/tur/sportif/eko) | 30-50 | A1 | U | — |
| F13 | Park modu + uyanık kalma + hareket alarmı | 45-70 | D1 | K,U | — |
| F14 | GPS takip + GSM bildirim | 50-70 | F13 | U | — |
| F15 | Immobilizer (NFC + PIN, marş devresi) | 20-35 | A1 | T,U | — |
| F16 | Dijital anahtar (BLE yakınlık) | 30-50 | F15 | K | CCC Digital Key (referans) |
| F17 | Aktüatör kontrolü (ışık, ısıtma, kamera tetik) | 25-40 | P3 | U | UDS 0x31 |
| F18 | XCP kalibrasyon arayüzü + A2L | 40-60 | P2 | K,T | ASAM XCP, `pyXCP` |
| F19 | Kalibrasyon paneli (canlı parametre) | 30-50 | F18 | U | — |

---

## 9b. Yarış / Motorsporları Telemetrisi

Çoğu mevcut donanımla (IMU + GPS + CAN) yapılabilir; "sportif profil"in içeriğini doldurur.

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / not |
|---|---|---|---|---|---|
| R1 | Tur tespiti (GPS geofence / beacon) | 15-25 | D1 | U | Otomatik tur başı/sonu |
| R2 | Delta zaman göstergesi | 20-30 | R1 | T,U | Referans tura göre anlık fark |
| R3 | Segment (sektör) analizi | 20-35 | R1 | T,U | Turu parçalayıp kayıp yeri bulma |
| R4 | Fren noktası tutarlılık analizi | 15-25 | D1 | T,U | Fren başlangıç noktası dağılımı |
| R5 | Yatış hızı ve yatış histogramı | 15-25 | F2 | T,U | Yatırma agresifliği, kullanılmayan yatış payı |
| R6 | Gaz–fren geçiş süresi analizi | 10-20 | D1 | T,U | Sürüş tekniği metriği |
| R7 | Sürüş tutarlılık skoru | 10-15 | R1 | U | Tur sürelerinin standart sapması |
| R8 | Kayma oranı (slip ratio) kestirimi | 20-35 | D1 | K,T | Tekerlek hızı CAN'da varsa |
| R9 | Süspansiyon strok histogramı + dibe vurma | 25-40 | Potansiyometre | T,U | Ayar için temel veri |
| R10 | Lastik/fren yüzey sıcaklığı takibi | 20-35 | IR sensör | U | Isınma turu göstergesi |
| R11 | Şasi titreşim imzası (rezonans/gevşeklik) | 25-40 | Mevcut IMU | T | Mekanik anomali |
| R12 | Çizgi (racing line) analizi | 30-50 | D12, D4 | T,U | Yüksek çözünürlüklü GPS/füzyon gerekir |
| R13 | Yol eğimi kestirimi | 15-25 | F2 | K,T | Sanal dinamometre girdisi de |
| R14 | Fren balata aşınma tahmini | 15-25 | D1 | U | Fren enerjisi entegrasyonu |
| R15 | Motor yük faktörü / bakım aralığı | 10-20 | D1 | U | Devir-tork ağırlıklı kullanım |

---

## 9c. Konfor, Enerji ve Sürücü Fonksiyonları

Daha önce havuza girmemiş fonksiyon önerileri. Çoğu mevcut donanımla veya küçük eklemeyle yapılabilir.

| # | Kalem | Efor | Bağımlılık | Değer | Not |
|---|---|---|---|---|---|
| K1 | Adaptif gösterge parlaklığı | 5-10 | Ortam ışık sensörü | U | Gündüz/gece otomatik |
| K2 | Isıtmalı el kumandası kontrolü | 15-25 | F17 | U | Sıcaklığa göre otomatik ayar |
| K3 | Otomatik sinyal iptali | 10-20 | D1 | U | Dönüş tamamlanınca IMU'dan iptal |
| K4 | Acil fren sinyali (hızlı yanıp sönme) | 10-15 | D1, F17 | U | Sert frende stop lambası flaşör |
| K5 | Yokuş kalkış desteği bildirimi | 15-25 | F2 | U | Eğim + duruş tespiti |
| K6 | Rüzgar/hava durumu uyarısı | 10-20 | N1 | U | Bağlantı varsa yol koşulu bilgisi |
| K7 | Yorgunluk/dikkat tespiti | 30-50 | M2 | T | Sürüş düzensizliği paterninden |
| K8 | Sürüş günlüğü ve istatistik | 15-25 | D1 | U | Km, süre, ortalama, rota geçmişi |
| K9 | Sosyal/grup sürüş takibi | 40-70 | N1 | U | Birden fazla aracın konumu |
| K10 | Sesli navigasyon entegrasyonu | 40-70 | M1, N4 | U | Telefon navigasyonu + sesli yönlendirme |
| E1 | Enerji akış izleme (üretim/tüketim) | 15-25 | D1 | T | Alternatör çıkışı vs yük |
| E2 | Akü şarj durumu ve sağlık kestirimi | 20-35 | F6 | T,U | SoC/SoH tahmini |
| E3 | Düşük gerilim koruma ve yük atma | 15-25 | Güç kartı | K,U | Kritik olmayan yükleri kesme |
| E4 | Rejeneratif fren analizi (ileride EV için) | 20-30 | D1 | T | Kavramsal, gelecek araç için |
| E5 | Uyku/uyanıklık güç bütçesi yönetimi | 20-35 | F13 | K,T | Modlara göre tüketim optimizasyonu |
| DR1 | Sürücü kimliği ve kişisel profil | 30-50 | M6 | K | Kim sürüyorsa ayarları yükle |
| DR2 | Sürüş becerisi gelişim takibi | 25-40 | R7 | U | Zaman içinde tutarlılık/hız trendi |
| DR3 | Kaza sonrası otomatik bildirim (eCall benzeri) | 30-50 | F7, N2 | K,U | Düşme + konum + acil bildirim |
| DR4 | Geofence / bölge uyarıları | 15-25 | D1 | U | Belirli bölgeye giriş/çıkış |
| DR5 | Hız limiti uyarısı (harita bazlı) | 25-40 | N1 | U | Konuma göre limit bilgisi |

**DR3 (eCall benzeri):** Gerçek araçlarda AB'de zorunlu olan otomatik acil çağrı sisteminin motosiklet versiyonu. Düşme tespiti (F7) + konum + GSM ile "kaza oldu, şuradayım" bildirimi. Motosiklet güvenliğinde gerçek bir ihtiyaç, tezde güçlü bir sosyal etki argümanı.

---

## 10. Görüntü İşleme ve İleri Algı

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak |
|---|---|---|---|---|---|
| V1 | Kamera entegrasyonu ve kayıt | 40-70 | Linux birimi | U | OpenCV, GStreamer |
| V2 | Şerit tespiti | 60-100 | V1 | T | OpenCV, LaneNet |
| V3 | Araç/engel tespiti | 80-150 | V1 | T | YOLO, OpenVINO |
| V4 | Kör nokta / arka yaklaşma uyarısı | 60-100 | V3 | U | — |
| V5 | Sürüş kaydı (dashcam + olay tetikli) | 30-50 | V1 | U | — |
| V6 | Veri toplama ve etiketleme hattı | 60-120 | V1 | T | CVAT, Label Studio |
| V7 | Kamera–IMU–CAN senkronizasyonu | 30-50 | V1, D4 | K,T | — |
| V8 | Trafik işareti tanıma | 60-100 | V3 | T | GTSRB dataset |

---

## 11. Linux / Yüksek Seviye Birim

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak |
|---|---|---|---|---|---|
| L1 | Linux birimi entegrasyonu (güç, ısı, titreşim, muhafaza) | 40-60 | Güç kartı | U | — |
| L2 | Yocto/Buildroot ile özel imaj | 50-80 | L1 | K | Yocto Project, Buildroot |
| L3 | Automotive Grade Linux denemesi | 60-100 | L2 | K | AGL |
| L4 | Android Automotive OS denemesi | 80-150 | L1 | K | AAOS |
| L5 | Salt okunur kök dosya sistemi + güç kesintisi dayanıklılığı | 25-40 | L2 | K | overlayfs |
| L6 | MCU–Linux haberleşme köprüsü | 30-50 | L1, A4 | K | SOME/IP, UART/SPI |
| L7 | Gösterge/HMI uygulaması | 50-90 | L1 | U | Qt, Flutter, LVGL |

---

## 12. Haberleşme ve Bağlantı

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak / standart |
|---|---|---|---|---|---|
| N1 | MQTT ile bulut bağlantısı | 25-40 | D5 | U | Mosquitto, `paho-mqtt` |
| N2 | GSM/LTE modülü entegrasyonu | 40-60 | — | U | — |
| N3 | BLE ile telefon bağlantısı | 30-50 | A1 | U | NimBLE |
| N4 | Mobil uygulama (basit gösterge) | 60-100 | N3 | U | Flutter, React Native |
| N5 | LoRa ile uzun menzil telemetri | 30-50 | — | U | LoRaWAN |
| N6 | Automotive Ethernet denemesi | 50-80 | — | K | 100BASE-T1 |
| N7 | TSN (zaman duyarlı ağ) denemesi | 60-100 | N6 | K | IEEE 802.1 TSN |
| N8 | V2X denemesi (araçlar arası) | 80-150 | N6 | K | C-V2X, `OpenC2X` |

---

## 13. Süreç ve Geliştirme Altyapısı

| # | Kalem | Efor | Bağımlılık | Değer | Açık kaynak |
|---|---|---|---|---|---|
| G1 | Gereksinim yönetimi | 20-35 | — | K,T | Doorstop, StrictDoc |
| G2 | V-modeli süreç dokümantasyonu | 25-40 | G1 | K,T | ASPICE |
| G3 | Sürüm yönetimi ve dallanma stratejisi | 10-20 | — | K | Git Flow, semantic versioning |
| G4 | Otomatik dokümantasyon üretimi | 15-25 | — | U | Doxygen, Sphinx |
| G5 | Yapı sistemi ve bağımlılık yönetimi | 15-30 | — | K | CMake, PlatformIO, west |
| G6 | Kod inceleme ve kalite kapıları | 10-20 | H7 | K | SonarQube |
| G7 | Açık kaynak yayını (lisans, katkı rehberi) | 15-30 | — | T,U | — |

---

## 14. Öne Çıkan On Kalem

Havuz büyük olduğu için, değer/efor oranı en yüksek on kalemi ayrıca işaretliyorum:

| Kalem | Neden |
|---|---|
| **A2 — COVESA VSS** | Düşük efor, yüksek sektörel görünürlük, mimarinin temelini standartlaştırır |
| **D2 — MDF4 kayıt formatı** | Verini sektörel araçlarla uyumlu kılar, efor düşük |
| **D7 — Foxglove** | Profesyonel görselleştirme, neredeyse bedava |
| **H10 — Renode** | Donanımsız CI testi, az bilinen ama etkileyici |
| **C6 — Uptane** | OTA güvenliğinin standardı, bootloader yapılıyorsa doğal devam |
| **S6 — MISRA C + statik analiz** | Efor düşük, "sektör standardı" iddiasını somutlaştırır |
| **H8/H9 — Birim test + kapsama** | Yazılım mühendisliği ciddiyetinin kanıtı |
| **F6 — Akü sağlık göstergesi** | Küçük iş, gerçek teşhis tekniği, HIL'de test edilebilir |
| **A7 — Eclipse Kuksa** | SDV mimarisinin açık kaynak referansı |
| **F18 — XCP + A2L** | Kalibrasyon dünyasının dili, ayırt edici |
| **R2/R3 — Delta zaman + segment** | Yarış telemetrisinin kalbi, mevcut donanımla, ölçülebilir çıktı |

---

## 15. Kasıtlı Olarak Havuz Dışı

| Kalem | Gerekçe |
|---|---|
| ECU flash yazma / stage haritalama | Yasal (ruhsat dışı tadilat), garanti, güvenlik; kazanç %3-5 |
| Piggyback / yakıt haritası müdahalesi | Geniş bant lambda ve EGT olmadan motor hasarı riski |
| Motor çalışırken kesme (yakıt/ateşleme) | Sürüş güvenliği — yalnızca marş devresine müdahale edilir |
| Gidona/şasiye gerilim uygulama | Üçüncü kişilere zarar, hukuki sorumluluk, etkisiz |
| Otonom sürüş yığını (Autoware/Apollo) | Ölçek olarak bu platformun kat kat üstünde |
| Gerçek load dump testi (ISO 7637-2 pals 5) | Özel ekipman gerektirir, DUT'u tahrip eder |

---

## 16. Önceliklendirme İçin Öneri Çerçevesi

Kalemleri şu dört kovaya ayırmanı öneririm:

**Kova 1 — Omurga.** Üstüne her şeyin bindiği altyapı. Bunlar olmadan diğerleri yapılamaz: P1, P2, A1, D1, F2, H1, H2.

**Kova 2 — Bitirme teslimi.** Jüriye gösterilecek kesit. Omurga + birkaç görünür fonksiyon + süreç dokümantasyonu.

**Kova 3 — Kariyer vitrini.** Mülakatta anlatılacaklar. P3, B1, C6, F18, H7, A2, S6 gibi sektörel karşılığı net olanlar.

**Kova 4 — Uzun vadeli.** Görüntü işleme, Linux birimi, V2X, otonom fonksiyonlar. Zaman kısıtı olmadan, sırayla.

Her yeni fikir havuza eklenir, kovaya değil. Kovaya girmesi için bir şeyin çıkması gerekir — bu kural, havuzun işe yaramasını sağlayan tek şeydir.

---

## 17. Donanım Mimarisi Analizi ve Standartlaşma

Mevcut sistem tek düğümlü (ESP32-S3 + OBD2/CAN + Nextion). Platform büyüdükçe bu yapı sınır verir. Sorun ESP32-S3 değil, her işin tek çipe yıkılması. Standart otomotiv mimarisi dağıtıktır: her düğüm bir işe bakar, aralarında CAN konuşur.

### 17.1 Üç Kademeli Evrim

**Kademe 1 — mevcut yapının rasyonelleştirilmesi (bitirme için önerilen).**
ESP32-S3 ana düğüm kalır, görev ayrımı netleşir (füzyon/fonksiyon/kayıt katmanları). HIL simülatörü ayrı çip. Donanım aynı, değişen sadece yazılım mimarisi (katmanlı yapı).

**Kademe 2 — standart otomotiv MCU'su (genişletilmiş).**
Ana üniteyi ESP32-S3'te bırak (Wi-Fi/BLE değerli), ikinci düğüm olarak STM32 ekle. Deterministik işler (CAN zamanlama, güvenlik kritik döngü, kontrol) STM32'ye taşınır. CV'ye "STM32 + otomotiv MCU" satırı girer.

**Kademe 3 — domain controller (Faz 2).**
Gerçek zamanlı domain (STM32/S32K) + yüksek seviye domain (Raspi/Linux), arada SOME/IP köprü. Modern SDV mimarisinin ta kendisi.

### 17.2 Otomotiv MCU Aileleri

| Çip ailesi | Konum | Not |
|---|---|---|
| STM32 F/G/H | Genel gömülü | En yaygın öğrenme yolu |
| STM32H7 | Yüksek performans + DSP | ML + kontrol birlikte |
| NXP S32K | AUTOSAR uyumlu, ASIL-B/D | Sektörde yaygın, Faz 2 için ideal |
| Infineon AURIX (TriCore) | Güvenlik kritik ECU | Pahalı, öğrenmesi zor |
| Renesas RH850 | Otomotiv ECU | Japon OEM'lerde yaygın |

### 17.3 Ara Modül Standartlaşması

| Alan | Şu an | Standart yaklaşım |
|---|---|---|
| CAN transceiver | Genel modül | TJA1051/TJA1441 (otomotiv), SN65HVD230 (3.3V) |
| Güç regülasyonu | Buck modül | Otomotiv sınıfı DC-DC (load dump dayanımlı) |
| Konnektör | Çeşitli | Deutsch DT serisi (su geçirmez, otomotiv standardı) |
| Koruma | Dağınık | TVS + ters polarite + PTC standart giriş katmanı |
| Zaman | MCU dahili | Harici RTC veya GPS disiplinli saat |
| Depolama | microSD | Endüstriyel SD veya eMMC |

**Deutsch DT konnektör** özellikle: ucuz (birkaç yüz TL) ama sistemi "prototip"ten "saha donanımı" görünümüne taşır. Jüri ve mülakatta fark yaratır.

### 17.4 Öneri

Bitirme için Kademe 1'de kal. Kademe 2'yi (STM32 ikinci düğüm) genişletilmiş kapsama al. Kademe 3'ü Faz 2'ye bırak. Ana üniteyi ESP32-S3'ten taşıma — Wi-Fi/BLE'yi kaybetmek için iyi sebep yok.

---

## 18. Açık Kaynak Ekosistemi ve Donanım Maliyetleri

> **Yasal ve etik çerçeve:** Aşağıdaki güvenlik/tersine mühendislik araçları **kendi aracın üzerinde, kendi ağında** öğrenme ve savunma amaçlı kullanım içindir. Başkasının aracına veya ağına izinsiz müdahale hem yasa dışıdır hem projenin meşruiyetini yok eder. Bu araçlar tezde "kendi sistemime saldırı senaryoları uygulayıp savunma geliştirdim" bağlamında değerlidir — saldırı aracı olarak değil, güvenlik doğrulama aracı olarak.

### 18.1 CAN / Otomotiv Ağ Araçları (Genel)

| Proje | Ne işe yarar | Lisans | Not |
|---|---|---|---|
| **SocketCAN** | Linux çekirdeğinin CAN altyapısı | GPL | Tüm Linux CAN işinin temeli |
| **can-utils** | candump, cansend, canplayer, cangen | GPL | Kayıt/oynatma, trafik üretimi — HIL için birebir |
| **python-can** | Python'da CAN erişimi | LGPL | Senaryo motorun için ideal |
| **cantools** | DBC/ARXML ayrıştırma, sinyal kodlama | MIT | Araç bağımsız sinyal katmanının çekirdeği |
| **SavvyCAN** | Grafik CAN analiz/tersine mühendislik | MIT | Bilinmeyen mesajları çözmek için görsel araç |
| **Wireshark + CAN** | Protokol analizi | GPL | Trafik inceleme |
| **udsoncan** | Python UDS istemci implementasyonu | MIT | Kendi UDS'ini doğrulamak için referans |
| **isotp (Python/C)** | ISO-TP taşıma katmanı | MIT | Kendi ISO-TP'ni karşılaştırmak için |
| **CANopenNode** | CANopen protokol yığını | Apache 2.0 | Endüstriyel/robotik CAN |

---

### 18.2 Güvenlik Araştırma ve Tersine Mühendislik Araçları

Bu bölüm senin "hacking tarafı" isteğinin karşılığı. Otomotiv güvenlik araştırması ciddi ve büyüyen bir alan; bu araçlar akademik ve savunma amaçlı geliştirilmiş.

| Proje | Ne işe yarar | Köken / topluluk | Not |
|---|---|---|---|
| **CaringCaribou** | "Araçlar için nmap" — CAN keşif, UDS tarama, fuzzing | İsveç (HEAVENS projesi) | Otomotiv sızma testinin en bilinen açık aracı |
| **CANToolz** | CAN analiz, MITM, fuzzing çerçevesi | **Rus güvenlik topluluğu** (Alexey Sintsov) | Modüler, saldırı senaryosu kurma |
| **c0f** | CAN parmak izi (fingerprinting) | Güvenlik topluluğu | ECU'ları trafikten tanımlama |
| **Metasploit HWBridge** | Donanım köprüsü üzerinden CAN saldırı modülleri | Rapid7 | Sızma testi çerçevesine CAN eklentisi |
| **UDS fuzzer'ları** | UDS servislerine anormal girdi | Çeşitli | Kendi UDS sunucunun sağlamlığını test etmek |
| **gallia** | Otomotiv teşhis fuzzing/tarama çerçevesi | Almanya (Fraunhofer) | UDS/DoIP odaklı, modern |
| **scapy-automotive** | Scapy'nin CAN/ISO-TP/UDS/DoIP katmanı | Fransa/topluluk | Paket üretimi ve analizi, çok güçlü |
| **OpenGarages / UDSim** | ECU simülatörü, öğrenme ortamı | OpenGarages | "Car Hacker's Handbook" ekosistemi |

**Rus/eski Sovyet sahnesi hakkında:** Bu bölgede güçlü bir tersine mühendislik ve düşük seviye sistem programlama geleneği var — CANToolz bunun en görünür açık kaynak örneği. Ayrıca immobilizer/anahtar sistemleri, ECU okuma-yazma (chiptuning) ve alarm sistemleri tersine mühendisliği üzerine geniş forum ve topluluk bilgisi mevcut (drive2, çeşitli РФ forumları). Bu bilginin bir kısmı gri alanda (araç hırsızlığıyla iç içe geçebiliyor), o yüzden kaynak seçerken savunma/araştırma tarafında kal — chiptuning ve araç çalma tekniklerine kayan içerikten uzak dur. Akademik ve CTF (capture-the-flag) tarafı temiz ve öğretici.

**Nasıl kullanırsın (meşru çerçeve):** CaringCaribou veya gallia ile kendi motosikletinin CAN hattını tararsın → hangi servisler açık, hangi ID'ler var öğrenirsin → bu bilgiyle hem sinyal haritanı çıkarırsın (P haritası) hem de kendi UDS sunucunun/istemcinin sağlamlığını fuzzing ile test edersin (havuzdaki C4, C8). Tezde bu, "kendi sistemime saldırı yüzeyi analizi yaptım" bölümü olur.

---

### 18.3 Yazılım Tanımlı Araç (SDV) — Açık Kaynak

| Proje | Ne | Destekleyen | Havuz karşılığı |
|---|---|---|---|
| **COVESA VSS** | Araç sinyal veri modeli standardı | COVESA (BMW, Bosch, Ford...) | A2 |
| **Eclipse Kuksa** | VSS tabanlı veri aracısı (databroker) | Eclipse SDV | A7 |
| **Eclipse Velocitas** | Araç uygulaması geliştirme çerçevesi | Eclipse SDV | A8 |
| **Eclipse Leda / Chariott** | SDV runtime ortamı | Eclipse SDV | A10 |
| **Eclipse hawkBit** | OTA kampanya yönetimi | Eclipse | B5 |
| **vsomeip** | SOME/IP implementasyonu | COVESA | A4 |
| **Eclipse Cyclone DDS** | DDS pub-sub | Eclipse | A5 |
| **Eclipse Zenoh** | Hafif pub-sub/veri akışı | Eclipse | A5 |
| **Eclipse ThreadX** | Gerçek zamanlı işletim sistemi (eski Azure RTOS) | Eclipse | A3 alternatifi |

Bu ekosistem, "yeni nesil otomotiv felsefesi" derken kastettiğin şeyin somut açık kaynak hali. Bosch, Microsoft, Red Hat, BMW gibi oyuncular bu projelere kod katıyor.

---

### 18.4 İşletim Sistemi ve Runtime

| Proje | Ne | Havuz karşılığı |
|---|---|---|
| **Zephyr RTOS** | Modern gömülü RTOS, geniş donanım desteği | A3 |
| **FreeRTOS** | Yaygın hafif RTOS (ESP-IDF zaten kullanıyor) | Mevcut |
| **Automotive Grade Linux (AGL)** | Otomotiv için Linux dağıtımı | L3 |
| **Android Automotive OS** | Google'ın araç içi OS'u | L4 |
| **Yocto Project** | Özel gömülü Linux imajı üretimi | L2 |
| **RAUC / SWUpdate / Mender** | Linux OTA çözümleri | B6 |
| **MCUboot** | Güvenli bootloader (A/B, imza) | B1/B2 referansı |
| **TF-M (Trusted Firmware-M)** | Güvenli dünya / secure boot | C2 |

---

### 18.5 Test, Simülasyon, Doğrulama

| Proje | Ne | Havuz karşılığı |
|---|---|---|
| **Renode** | MCU/SoC yazılım simülasyonu (donanımsız test) | H10 |
| **QEMU** | Genel sistem emülasyonu | H10 alternatifi |
| **Unity / CMock / Ceedling** | Gömülü C birim testi | H8 |
| **gcov / lcov** | Kod kapsama | H9 |
| **cppcheck / clang-tidy** | Statik analiz | S6 |
| **PlotJuggler** | Zaman serisi veri görselleştirme | D8 |
| **Foxglove Studio** | Robotik/otomotiv veri görselleştirme | D7 |
| **CARLA** | Otonom sürüş simülatörü (ağır) | V-serisi için |
| **esmini** | OpenSCENARIO senaryo oynatıcı | H13 |

---

### 18.6 Veri ve ML

| Proje | Ne | Havuz karşılığı |
|---|---|---|
| **asammdf** | MDF4 okuma/yazma (Python) | D2 |
| **MCAP** | Çok kanallı kayıt formatı (Foxglove) | D3 |
| **TensorFlow Lite Micro** | MCU'da ML çıkarımı | M-serisi |
| **Edge Impulse** | TinyML geliştirme platformu (kısmen açık) | M1/M2 |
| **ESP-DL / ESP-NN** | ESP32 için ML hızlandırma | M1 |
| **ONNX Runtime** | Model çalıştırma/dönüştürme | M8 |
| **scikit-learn** | Klasik ML (anomali tespiti) | M4 |
| **Hugging Face Datasets** | Veri seti yayınlama | D9 |

---

### 18.7 Referans / İlham Alınacak Custom Projeler

Bireylerin veya küçük ekiplerin yaptığı, senin projene yakın açık kaynak işler:

| Proje | Ne | Neden ilgili |
|---|---|---|
| **comma.ai / openpilot** | Açık kaynak ADAS (şerit takip, adaptif hız) | Custom donanım + araç CAN entegrasyonunun en iyi örneği; kod kalitesi ve mimari referans |
| **openpilot panda** | Araç CAN'ına güvenli erişim donanımı | Güvenlik kilitli CAN arayüzü tasarımı |
| **RetroPilot** | openpilot'un topluluk çatalları | Küçük ekip sürdürülebilirliği |
| **Freematics** | Arduino/ESP tabanlı OBD telemetri donanımı+yazılımı | Senin platformuna en yakın açık donanım |
| **ESP32-OBD2 projeleri** | Çeşitli bireysel OBD tarayıcılar | ESP32 + CAN referans kodları |
| **WICAN** | ESP32 tabanlı açık kaynak OBD-WiFi/BLE dongle | Ticari-açık hibrit, devre şeması açık |
| **O-Panel / TinyCAN gösterge projeleri** | Motosiklet/araç dijital gösterge | Nextion/LVGL gösterge referansı |
| **Speeduino** | Açık kaynak ECU (megasquirt tarzı) | ECU'nun nasıl çalıştığını öğrenmek için — kendi motorunda kullanmak için değil |
| **rusEFI** | Açık kaynak ECU firmware | Speeduino alternatifi, güçlü topluluk |
| **DIY yarış telemetri (RaceCapture)** | Açık kaynak yarış veri kaydedici | AutosportLabs — R-serisi için birebir referans |

**Speeduino/rusEFI notu:** Bunlar açık kaynak ECU projeleri. Kendi CL250'ne kurmak için DEĞİL (havuz dışı — yasal/garanti). Ama motor kontrolünün nasıl çalıştığını öğrenmek, HIL plant modelini kurarken referans almak ve "ECU tarafını da anlıyorum" diyebilmek için okumaya değer.

**RaceCapture (AutosportLabs):** Açık kaynak yarış telemetri donanımı ve yazılımı. R-serisi (yarış telemetrisi) için doğrudan ilham kaynağı — delta zaman, tur analizi, gösterge nasıl yapılır görürsün.

---

### 18.8 Öğrenme Kaynakları

| Kaynak | Ne |
|---|---|
| **The Car Hacker's Handbook** (Craig Smith) | Otomotiv güvenliğinin temel kitabı, ücretsiz PDF açık |
| **OpenGarages topluluğu** | Araç güvenliği öğrenme ekosistemi |
| **CAN bus üzerine ISO standartları** | 11898 (CAN), 15765 (ISO-TP/OBD), 14229 (UDS), 13400 (DoIP) |
| **AUTOSAR spesifikasyonları** | Herkese açık, mimari referans |
| **CTF (capture-the-flag) araç güvenliği** | Pratik, yasal öğrenme ortamı |

---

### 18.9 Ek Donanım Maliyet Listesi

Havuzdaki kalemlerin gerektirdiği, mevcut sistemde OLMAYAN donanımlar. Fiyatlar Eylül 2026 Türkiye tahmini; sipariş öncesi teyit et.

### 9.1 Sensörler

| Donanım | Hangi kalem için | Tahmini (TL) |
|---|---|---|
| Lineer potansiyometre / çekme telli enkoder ×2 | R9 süspansiyon | 300-600 |
| IR sıcaklık sensörü (MLX90614 vb.) | R10 lastik/fren sıcaklığı | 150-350 |
| Termokupl + MAX31855 (EGT) | Motor sağlığı, arıza tespiti | 300-600 |
| Geniş bant lambda sensörü + kontrolcü | AFR / yanma kalitesi | 2000-4000 |
| TPMS sensörleri (lastik basıncı) | Yarış basınç takibi | 800-1500 |
| Ek IMU (yüksek kaliteli, düşük drift) | F2/R serisi hassasiyet | 400-1000 |
| RTK GPS modülü + anten | R12 çizgi analizi | 2000-4500 |
| Fren kolu yük hücresi + amplifikatör | Fren kuvveti analizi | 500-1200 |

### 9.2 İşlem ve Haberleşme

| Donanım | Hangi kalem için | Tahmini (TL) |
|---|---|---|
| Raspberry Pi 5 (veya CM5) | Linux birimi, kamera, ağır ML | 2500-4500 |
| Raspi güç HAT / UPS modülü | L1 güç kesintisi dayanıklılığı | 400-900 |
| STM32 geliştirme kartı | HIL simülatör alternatif platform | 150-400 |
| CAN FD transceiver | P6 CAN FD | 100-250 |
| GSM/LTE modülü (A7670/SIM7600) | F14, N2 | 400-900 |
| LoRa modülü (SX1276/1262) | N5 uzun menzil | 200-450 |
| Automotive Ethernet PHY (100BASE-T1) | N6, DoIP | 500-1200 |
| BLE zaten ESP32-S3'te var | N3, F16 | 0 |

### 9.3 Kamera ve Görüntü

| Donanım | Hangi kalem için | Tahmini (TL) |
|---|---|---|
| Raspi kamera modülü (v3 / HQ) | V1 | 500-1500 |
| Global shutter kamera | V3 hareket bulanıklığı azaltma | 1000-2500 |
| Su geçirmez kamera muhafazası | V1 dış montaj | 200-500 |
| Coral USB TPU / hızlandırıcı (opsiyonel) | V3 ağır model | 1500-3000 |

### 9.4 Güç ve Koruma

| Donanım | Hangi kalem için | Tahmini (TL) |
|---|---|---|
| Süper kapasitör seti + dengeleme | Denetimli kapanma | 150-300 |
| Geniş girişli buck (2-3 A) | Ayrı güç kartı | 100-250 |
| INA226/228 güç izleme | Güç ölçümü, HIL | 100-300 |
| Koruma (TVS, ters polarite, sigorta) | Güç kartı | 100-250 |
| Küçük LiPo + şarj devresi | Bataryalı gizli takip modülü | 200-450 |
| Bistable röle | F15 immobilizer | 80-200 |
| NFC okuyucu (PN532) | F15 yetkilendirme | 100-250 |

### 9.5 HIL Tezgahı (ayrı sistem)

| Donanım | Hangi kalem için | Tahmini (TL) |
|---|---|---|
| İkinci ESP32/STM32 (simülatör) | H1 | 150-450 |
| CAN transceiver ×1 | H1 | 80-150 |
| DAC kontrollü ayarlanabilir besleme | H5 elektriksel arıza | 150-300 |
| Röle/analog anahtar (arıza enjeksiyonu) | H5 | 80-200 |
| OBD2 dişi konnektör + kablo | H1 | 100-250 |

### 9.6 Kaba Toplamlar

| Paket | Aralık (TL) |
|---|---|
| Sadece mevcut sistem + temel eklemeler (güç kartı, immobilizer, park modu) | +600-1400 |
| Yarış telemetrisi ek sensörleri (süspansiyon, IR, EGT) | +750-1550 |
| HIL tezgahı | +560-1350 |
| Linux + kamera katmanı | +4000-9000 |
| İleri sensörler (lambda, RTK, TPMS, yük hücresi) | +5300-11200 |

**Not:** Alt bandı Türkiye yerel tedarikle, üst bandı ithal/premium parçalarla oluşur. Öncelik sırasına göre parça parça alınmalı — hepsini baştan almak ne gerekli ne mantıklı. AliExpress fiyatları yaklaşık yarısı ama 3-5 hafta kargo ve gümrük riski var; zaman kritikse yerelden al.

---

### 18.10 Önceliklendirme İçin Not

Bu dokümandaki açık kaynak araçların çoğu **bedava** ve donanım gerektirmiyor — yani havuzun yazılım kalemlerinin marjinal maliyeti çoğu zaman sıfır. Asıl maliyet donanımda ve o da kademeli. Bölüm 14'teki (özellik havuzu) "öne çıkan on kalem"in neredeyse hepsi bu dokümandaki bedava açık kaynak araçlarla yapılabilir: VSS, MDF4, Foxglove, Renode, MISRA araçları, birim test — hiçbiri ek donanım istemiyor.

Yani bir sonraki adımda önceliklendirme yaparken kuralı şöyle koy: **önce sıfır-donanım, yüksek-değer kalemleri** süpür (bunlar açık kaynakla geliyor), donanım gerektirenleri ise gerçekten o fonksiyona geldiğinde parça parça al.
