# Faz 0 Uygulama Planı — Veri Toplama Altyapısı ve ML Hazırlığı

**Proje:** Motosiklet gömülü teşhis, telemetri ve sürücü destek platformu
**Bu planın kapsamı:** İlk öncelik — ML araştırması, açık kaynak inceleme ve çalışan bir veri toplama sistemi
**Sürüm:** 1.0 — Eylül 2026

---

## 0. Bu Planın Mantığı

Diğer her şeyden önce **veri toplama sistemi** kurulmalı. Gerekçe:

- Geçmiş sürüşler sonradan toplanamaz — kayıt ne kadar erken başlarsa o kadar zengin veri birikir
- ML modellerinin hepsi (arıza tespiti, bağlam sınıflandırma, sesli komut) bu veriye dayanıyor
- Veri formatı ve meta veri şeması baştan yanlış kurulursa, toplanan veri sonradan işe yaramaz

Bu yüzden ML modelini **kurmak** değil, ML için **zemini hazırlamak** ilk iş. Model Faz 2'de kurulur; veri ve altyapı şimdi.

**Sıra:** araştırma → format kararı → kayıt sistemi → doğrulama → sürekli toplama başlar.

---

## 1. İş Paketi Sıralaması

| Sıra | İş paketi | Çıktı |
|---|---|---|
| İP-1 | ML ve açık kaynak araştırması | Referans notları, format/yöntem kararları |
| İP-2 | Veri şeması tasarımı | Sinyal listesi + meta veri şeması + kayıt formatı |
| İP-3 | Fiziksel bağlantı (jumper → perfboard) | Titreşime dayanıklı bağlantı |
| İP-4 | Kayıt sistemi (microSD + binary) | Araçta çalışan kayıt yazılımı |
| İP-5 | Güç ve güvenli kapanma | Süper kapasitör tamponu, veri kaybı koruması |
| İP-6 | Doğrulama ve kalibrasyon | IMU hizalama, hız doğrulama, format testi |
| İP-7 | Sürekli toplama + sunucu senkronu | Her sürüş otomatik kayıt, sunucuya aktarım |

---

## 2. İP-1: ML ve Açık Kaynak Araştırması

### 2.1 İncelenecek Açık Kaynak Projeler

| Proje | Ne için bakılacak |
|---|---|
| **Freematics** | ESP32 + OBD telemetri donanım/yazılım referansı — senin platformuna en yakın |
| **WICAN** | ESP32 OBD-WiFi/BLE dongle, açık devre şeması ve kayıt mimarisi |
| **RaceCapture (AutosportLabs)** | Yarış telemetri kayıt formatı, kanal yapısı, senkronizasyon |
| **openpilot / panda** | Araç CAN'ına güvenli erişim, veri kayıt mimarisi, kod kalitesi |
| **can-utils (candump/canplayer)** | Kayıt/oynatma formatı mantığı |
| **asammdf** | MDF4 formatı — arşiv/paylaşım hedefi |
| **Edge Impulse örnek projeleri** | IMU tabanlı sınıflandırma, veri toplama akışı |

### 2.2 Veri Setleri (arıza tespiti ön araştırması için)

| Veri seti | İçerik | Not |
|---|---|---|
| CWRU Bearing | Rulman arızası, titreşim | Alan uyumsuz ama transfer öğrenme için ön eğitim |
| MaFaulDa | 6 durum, çok sensörlü makine arızası | Metodoloji referansı |
| MIMII | Endüstriyel makine sesi anomali | Ses tabanlı yaklaşım için |
| (CAN arıza veri seti) | Yok — literatürde eksik | Senin katkı alanın burası |

### 2.3 Araştırma Çıktıları (karar verilecekler)

- Anomali tespiti yaklaşımı: tek sınıflı öğrenme mi, transfer öğrenme mi
- Özellik çıkarımı: ham sinyal mi, frekans domeni mi, istatistiksel öznitelik mi
- Örnekleme frekansları (her sinyal için)
- Etiketleme stratejisi (arıza durumları nasıl işaretlenecek)
- Kayıt formatı kararı (binary şema)

**Efor:** 20-40 saat (okuma, deneme, not)

---

## 3. İP-2: Veri Şeması Tasarımı

### 3.1 Kaydedilecek Sinyaller

| Kaynak | Sinyal | Frekans (Hz) |
|---|---|---|
| CAN | Motor devri | 10-20 |
| CAN | Araç hızı | 10 |
| CAN | Gaz kelebeği pozisyonu | 10-20 |
| CAN | Motor sıcaklığı | 1 |
| CAN | Emme basıncı / hava akışı | 10 |
| CAN | Yakıt trim (varsa) | 1 |
| CAN | Akü gerilimi | 1 |
| CAN | Tekerlek hızları (ABS'ten, varsa) | 20-50 |
| CAN | Arıza kodları | Olay bazlı |
| IMU | 3 eksen ivme | 100-200 |
| IMU | 3 eksen açısal hız | 100-200 |
| Türetilmiş | Yatış açısı | 100 |
| GPS | Konum, yer hızı, yön | 5-10 |
| Ünite | Besleme gerilimi, akım | 10 |
| Ünite | İç sıcaklık | 0.1 |
| Ünite | Yığın/görev durumu | 1 |

### 3.2 Meta Veri Şeması (her seans başında)

- Seans kimliği, tarih, saat
- Ortam sıcaklığı, hava (kuru/ıslak)
- Lastik basıncı (ön/arka)
- Yakıt seviyesi
- Sürücü ağırlığı, ek yük
- Araç konfigürasyonu (dişli, egzoz, filtre — modifikasyon deneyleri için)
- **Durum etiketi: sağlıklı / arıza tipi** (arıza seansları için kritik)
- Güzergâh türü (şehir/kırsal/otoyol/kapalı alan)
- Serbest not

### 3.3 Kayıt Formatı Kararı

| Katman | Format | Gerekçe |
|---|---|---|
| Araçta yazma | Basit binary | Hızlı, kompakt, ESP32 dostu |
| Arşiv/paylaşım | MDF4 (sonradan çevir) | Sektörel uyum, Hugging Face |
| Model eğitimi | Parquet / NumPy | Kütüphaneler bunu okur |

**Binary şema tasarımı:** sabit boyutlu kayıt bloğu, zaman damgası + sinyal alanları + CRC. Blok başına CRC, ani kesintide kısmi kurtarma.

**Efor:** 10-15 saat

---

## 4. İP-3: Fiziksel Bağlantı

Jumper kablolar titreşimde güvenilmez. Ara adım: **perfboard'a lehim** (PCB'yi beklemeden).

| İş | Detay |
|---|---|
| Perfboard montaj | Modüller (ESP32-S3, IMU, GPS, SD, güç) lehimli |
| Konnektörler | Ayrılabilir noktalarda kilitli konnektör (JST/Molex), jumper yok |
| CAN bağlantısı | Y kablo, DLC'ye paralel, kesme yok |
| Muhafaza | IP54 kutu, konnektör ağzı aşağı |
| Titreşim | Kart silikon takozda; IMU rijit (takozsuz) |

**Efor:** 15-25 saat
**Not:** PCB tasarımı bu fazda değil — tasarım oturduktan sonra (Faz 1).

---

## 5. İP-4: Kayıt Sistemi

| Bileşen | İş |
|---|---|
| microSD sürücüsü | SPI veya SDMMC, yüksek yazma hızı |
| Binary yazıcı | Şemaya göre blok yazma, tamponlu |
| Zaman tabanı | Monoton sayaç + GPS senkronizasyonu |
| Dosya yönetimi | Seans başına dosya, 100 MB'ta böl |
| Bütünlük | Blok CRC, kısmi kurtarma |
| Meta veri | Seans başında JSON yaz |

**Efor:** 30-50 saat

---

## 6. İP-5: Güç ve Güvenli Kapanma

| Bileşen | İş |
|---|---|
| Giriş koruması | Sigorta, ters polarite, TVS, LC filtre |
| Regülasyon | Geniş girişli buck (6-40V → 5V) |
| Süper kapasitör tamponu | Kontak kesilince dosyayı güvenli kapatacak enerji |
| Kapanış tespiti | Kontak hattı GPIO ile izlenir, düşüşte kapanma başlar |
| Güç izleme | INA226 (gerilim, akım) |

**Efor:** 20-35 saat
**Not:** Ayrı güç kartı olarak tasarlanabilir; subframe/tail yerleşimi.

---

## 7. İP-6: Doğrulama ve Kalibrasyon

| Test | Amaç |
|---|---|
| IMU hizalama | Statik referans + bilinen açıda doğrulama |
| Hız doğrulama | CAN hızı vs GPS vs hesap (vites oranından) |
| CAN sinyal haritası | Hangi ID/byte hangi sinyal — tanım dosyası |
| Kayıt bütünlüğü | Kontak kesme testi, dosya kurtarılabilirliği |
| Gürültü testi | Motor açık/kapalı sinyal karşılaştırması |
| Uyku akımı | < 1 mA doğrulaması |

**Efor:** 20-30 saat

---

## 8. İP-7: Sürekli Toplama ve Sunucu Senkronu

| Bileşen | İş |
|---|---|
| Otomatik kayıt | Her kontak açılışında seans başlar |
| Wi-Fi senkron | Ev menzilinde otomatik sunucuya yükleme |
| Sunucu tarafı | Dosya deposu + zaman serisi DB (InfluxDB/TimescaleDB) veya basit dosya + Python |
| MDF4 dönüşümü | Sunucuda `asammdf` ile arşiv formatı |
| Yedekleme | İki kopya (yerel + bulut) |

**Not:** Öğrenme **offline ve sürümlü** — sunucuda periyodik yeniden eğitim, insan onayı, OTA ile model yükleme. Sürekli/online öğrenme değil.

**Efor:** 40-60 saat (temel senkron + basit DB)

---

## 9. Donanım Gereksinimleri

### 9.1 Zaten Elde Olanlar

- ESP32-S3 (ana ünite)
- OBD2/CAN bağlantısı
- Nextion ekran

### 9.2 Bu Faz İçin Gerekli — Zorunlu

| Donanım | Amaç | Elde var mı? | Tahmini (TL) |
|---|---|---|---|
| CAN transceiver (SN65HVD230) | Fiziksel katman | Kontrol et | 80-150 |
| IMU (6/9 eksen, MPU6050/9250 veya LSM6DSO) | Hareket verisi | ? | 150-300 |
| microSD kart modülü + kart (endüstriyel/high-endurance) | Kayıt | Hayır | 150-300 |
| GPS modülü (NEO-M8N) + anten | Konum, hız | ? | 250-450 |
| Perfboard, kilitli konnektör, kablo | Montaj | Kısmen | 200-350 |
| Güç: buck + koruma + INA226 | Besleme, izleme | Kısmen | 300-500 |
| Süper kapasitör + dengeleme + akım sınırlayıcı | Güvenli kapanma | Hayır | 150-300 |
| Muhafaza (IP54) | Koruma | Hayır | 150-300 |
| **Ara toplam** | | | **1430-2650** |

### 9.3 Bu Faz İçin — Opsiyonel / Sonraki Faz

| Donanım | Amaç | Ne zaman |
|---|---|---|
| STM32 (Nucleo F303RE / F103) | HIL simülatör, ikinci düğüm | HIL fazında — satılık listeden alınabilir |
| Raspberry Pi 4/5 | Linux birimi, kamera, ML | Dağıtık mimari fazında |
| Pi kamera | Görüntü işleme | Kamera fazında |
| Mikrofon + buton | Sesli komut | Sesli komut fazında |
| LoRa modülü | Uzun menzil telemetri | İsteğe bağlı |

### 9.4 Satılık Listeden Alınması Önerilenler

Bu faz için doğrudan gerekli değil ama sonraki fazlar için değerli ve fiyatı iyiyse alınmalı:

- **STM32 Nucleo F303RE** — HIL simülatör ve ikinci düğüm
- **STM32F103C8T6 (2 adet)** — HIL simülatör (ECU taklidi) için ideal
- **Raspberry Pi 4 8GB** — dağıtık mimari (fiyatı iyiyse; Pi 5 alternatifi değerlendirilebilir)
- **Pi kamera** — görüntü işleme fazı
- **LoRa + anten** — uzun menzil telemetri denemesi

Alınması **gereksiz:** Arduino UNO (geriye adım), OV7670 (düşük kalite), motor/step sürücüler (projede aktüatör sürme yok).

---

## 10. Faz 0 Toplam Efor

| İş paketi | Efor (saat) |
|---|---|
| İP-1 ML/açık kaynak araştırması | 20-40 |
| İP-2 Veri şeması | 10-15 |
| İP-3 Fiziksel bağlantı | 15-25 |
| İP-4 Kayıt sistemi | 30-50 |
| İP-5 Güç ve güvenli kapanma | 20-35 |
| İP-6 Doğrulama | 20-30 |
| İP-7 Sürekli toplama + senkron | 40-60 |
| **Toplam** | **155-255** |

Faz 0 bittiğinde elinde: titreşime dayanıklı, kesintiye dayanıklı, her sürüşte otomatik veri toplayan, sunucuya senkronize olan bir sistem — ve üstüne her ML modelinin oturacağı temiz, etiketli, sürekli büyüyen bir veri kümesi.

---

## 11. Bu Fazdan Sonra

Faz 0 tamamlanınca sıra:
- Veri birikmeye devam ederken protokol yığını (CAN/ISO-TP/UDS) ve HIL tezgahı
- Yeterli veri birikince ilk ML modeli (bağlam sınıflandırma — en kolay etiketlenen)
- Arıza enjeksiyon seansları (veri zenginleştirme)
- Model eğitimi ve doğrulama

Öncelik havuzundaki (ayrı doküman) kovalara göre ilerlenir.
