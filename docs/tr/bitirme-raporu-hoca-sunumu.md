# Motosiklet Gömülü Teşhis, Telemetri ve Sürücü Destek Platformu
## Bitirme Projesi Teknik Raporu

**Öğrenci:** Bilgisayar Mühendisliği, Manisa Celal Bayar Üniversitesi
**Araç:** Honda CL250 (ilk uygulama, mimari araç bağımsız tasarlandı)
**Sürüm:** 2.0 — Eylül 2026

---

# İçindekiler

1. Proje Amacı ve Kapsamı
2. Fonksiyon Envanteri (Sistemde Yer Alan Tüm Modüller)
3. Donanım Listesi
4. Repo Yapısı: Neden Çoklu-Repo, Her Reponun Amacı
5. Fonksiyonların Çalışma Yöntemleri (Metodoloji)
6. MCU Mimari Şeması ve Gerekçesi
7. MCU'lar ve Teknik Yeterlilik Değerlendirmesi
8. HIL Test Tezgahı — Amaç, Mimari, MCU
9. Sürdürülebilirlik ve Ölçeklenebilirlik Analizi
10. Sektörel Karşılaştırma: ADAS / SDV Standartlarına Uygunluk
11. Sistem İş Akışı
12. Senaryo Bazlı İş Akışı Örnekleri
13. Faz 2 / Sonraki Aşama (Konsolide Liste)

---

# 1. Proje Amacı ve Kapsamı

## 1.1 Problem Tanımı

Motosiklet, otomobile kıyasla çok daha az elektronik güvenlik desteğine sahip bir araç sınıfıdır — sürücü, çevresel tehditlere (kör nokta, viraj kaybı, şerit ihlali) ve mekanik arızalara karşı büyük ölçüde kendi refleksleriyle baş başadır. Bu proje, otomotiv sektörünün kullandığı mimari desenleri (yazılım tanımlı araç / SDV, katmanlı domain controller yapısı, UDS teşhis protokolü, HIL doğrulama) motosiklet ölçeğine uyarlayarak bu boşluğu kapatan bir gömülü sistem geliştirmeyi amaçlar.

## 1.2 Proje İkili Amacı

1. **Sürücü güvenliği ve teşhis:** Kör nokta uyarısı, viraj güvenlik sistemi, şerit takip, arıza/anomali tespiti, immobilizer — motosikletçinin karşılaştığı somut riskleri azaltan fonksiyonlar.
2. **Mühendislik metodolojisi:** Bu fonksiyonları, gerçek otomotiv sektöründe kullanılan yöntemlerle (ISO 14229 UDS, ISO 15765-2 ISO-TP, VSS sinyal standardı, HIL restbus simülasyonu, ISO 26262 girişimden bağımsızlık ilkesi) inşa etmek — yani "çalışan bir prototip" değil, "sektörün nasıl çalıştığını gösteren bir prototip" üretmek.

## 1.3 Sürdürülebilir Kalkınma Amaçları (SDG) ile İlişki

| SDG | Alt hedef | Projedeki karşılığı |
|---|---|---|
| SDG 3 — Sağlık ve Kaliteli Yaşam | 3.6 — Karayolu trafik kazalarından ölüm/yaralanmaları azaltmak | Kör nokta, viraj uyarısı, şerit takip, kaza tespit+bildirim |
| SDG 11 — Sürdürülebilir Şehirler | 11.2 — Güvenli, sürdürülebilir ulaşım sistemleri | Aynı güvenlik fonksiyonları, ulaşım sistemi güvenliği çerçevesinde |
| SDG 9 — Sanayi, Yenilikçilik, Altyapı | 9.5 — Ar-Ge/teknolojik kapasite; 9.b — yerli teknoloji geliştirme | HIL metodolojisi, açık kaynak protokol implementasyonu, açık veri seti yayını |
| SDG 12 — Sorumlu Tüketim (tamamlayıcı) | 12.5 — Atık azaltma | Yük-bazlı bakım takibi — gereksiz parça değişimini azaltır |

Birincil gerekçe SDG 3/11 (sistemin çıktısı — güvenlik), ikincil gerekçe SDG 9 (sistemin nasıl inşa edildiği — açık kaynak Ar-Ge metodolojisi).

## 1.4 Kapsam Sınırları (bilinçli olarak dışarıda bırakılanlar)

| Konu | Neden dışarıda |
|---|---|
| ECU yazılımına müdahale (stage/chiptuning) | Yasal (tadilat), garanti, güvenlik riski; doğal emişli motorda kazanç düşük (~%3-5) |
| Piggyback/yakıt haritası müdahalesi | Geniş bant lambda/EGT olmadan motor hasarı riski |
| Cruise control | Gaz teline fiziksel aktüasyon — projenin "pasif izleme + uyarı" felsefesiyle uyuşmuyor, güvenlik riski kategorik olarak farklı |
| Otonom sürüş fonksiyonları | Ölçek olarak bu platformun kapsamı dışında |
| Tam ISO 21434 siber güvenlik sertifikasyonu (TARA) | Backlog'da (özellik havuzu), çekirdek kapsamda değil — bkz. bölüm 10 |

---

# 2. Fonksiyon Envanteri

Sistemde yer alan tüm fonksiyonel modüller, hangi fiziksel birimde koştuğu ile birlikte:

| # | Fonksiyon | Koştuğu birim | Kritiklik | Bölüm |
|---|---|---|---|---|
| 1 | CAN sürücü + hata durum makinesi | STM32H7 | Yüksek | §5.1 |
| 2 | ISO-TP taşıma katmanı | STM32H7 | Yüksek | §5.1 |
| 3 | UDS teşhis sunucusu + istemcisi | STM32H7 | Yüksek | §5.1 |
| 4 | Bootloader (OTA, A/B bank, rollback) | STM32H7 | Yüksek | §5.1 |
| 5 | XCP kalibrasyon arayüzü | STM32H7 | Orta | §5.1 |
| 6 | Bağlam sınıflandırma (yol tipi, yüzey, sürüş olayı) | STM32H7 (ESP32-S3'te hafif varyant) | Yüksek (temel katman) | §5.2 |
| 7 | Bağlam veri yolu | STM32H7 | Yüksek (altyapı) | §5.2 |
| 8 | Kör nokta uyarı sistemi (BSM) | STM32 G0/F0 (I/O node) | Güvenlik kritik | §5.3 |
| 9 | Viraj güvenlik uyarı sistemi | STM32 G4/F3 (safety node, karar) + STM32H7 (EKF) | Güvenlik kritik | §5.4 |
| 10 | İmmobilizer | STM32 G0/F0 (I/O node) | Güvenlik ilişkili | §5.5 |
| 11 | Park modu / hırsızlık takibi | STM32 G0/F0 (I/O node) | Orta | §5.5 |
| 12 | Güç kartı (besleme, güvenli kapanma) | STM32 G0/F0 hattı + Raspi ayrı hat | Yüksek (altyapı) | §5.5 |
| 13 | Ekran/gösterge mimarisi (Nextion + LED halka + shift-light) | STM32H7 + I/O node | Orta | §5.6 |
| 14 | Şerit takip / şerit ihlali uyarı (LDW) | Raspi 5 | Orta-yüksek | §5.7 |
| 15 | Sesli komut sistemi (offline) | ESP32-S3 | Orta | §5.8 |
| 16 | Moto-MCP + sürüş içi LLM asistanı | Raspi 5 (+ bulut) | Düşük (konfor) | §5.9 |
| 17 | Linux node / SDV katmanı (Kuksa Databroker, VSS köprüsü) | Raspi 5 | Yüksek (altyapı) | §5.10 |
| 18 | Anomali/arıza tespit modeli | Raspi 5 (birleşik model) + STM32H7 (güvenlik ağı) | Orta | §5.11 |
| 19 | Veri toplama ve kayıt altyapısı | STM32H7 (yazma) + Raspi/sunucu (senkron) | Yüksek (altyapı) | §5.12 |
| 20 | Sanal dinamometre | STM32H7 | Düşük (analiz) | §5.13 |
| 21 | Konfor/enerji/sürücü destek fonksiyonları (15 alt fonksiyon) | Dağıtık — çoğunlukla STM32H7/I/O node | Düşük-orta | §5.14 |
| 22 | HIL test tezgahı | STM32F4 (simülatör) + host bilgisayar | Yüksek (doğrulama) | §8 |

**Not:** Tablo, çekirdek kapsamda tamamlanması hedeflenen fonksiyonları kapsar. Genişletilmiş/Faz 2 kapsamındaki ek fonksiyonlar (sanal dinamometre, sürücü kimliği modeli, kamera tabanlı ek analitik, GSM takip vb.) ayrı bir özellik havuzu dokümanında (backlog) tutulmaktadır ve bu raporun ana kapsamı dışındadır.

---

# 3. Donanım Listesi

Fiyat bilgisi olmadan, kategori ve amaç bazlı tam liste:

## 3.1 İşlem Birimleri

| Birim | Çip | Rol |
|---|---|---|
| Ana domain MCU | STM32H7 (H743/H723 ailesi) | CAN, telemetri, kayıt, füzyon, UDS/ISO-TP/bootloader, XCP, bağlam, EKF |
| Bağlantı+ses MCU | ESP32-S3 | Wi-Fi/BLE, sesli komut (ESP-SR) |
| Güvenlik MCU | STM32 G4/F3 ailesi | Viraj güvenlik kararı — izole |
| I/O MCU | STM32 G0/F0 ailesi | Kör nokta, immobilizer, güç yönetimi (birleşik zone controller) |
| Linux/HPC birimi | Raspberry Pi 5 (8GB) | Kamera, görüntü işleme, ağır ML çıkarımı, HMI, harita, LLM köprüsü |
| HIL simülatör MCU | STM32F4 ailesi | Restbus simülasyonu, araç dinamik modeli (araçta değil, ayrı test donanımı) |
| HIL yardımcı MCU | STM32F103 (mevcut) | Arıza enjeksiyonu, programlanabilir besleme kontrolü |
| HIL host | Masaüstü bilgisayar (Linux) | Senaryo motoru, kontrol paneli, rapor üretimi |

## 3.2 Haberleşme Donanımı

- CAN transceiver (her MCU için bir adet + HIL simülatör/DUT tarafı için ayrı)
- CAN köprüsü modülü (Raspi için — SPI tabanlı denetleyici + transceiver veya hazır CAN arayüz kartı)
- OBD2 dişi konnektör ve kablo (araç bağlantısı + HIL bağlantısı için ayrı ayrı)

## 3.3 Sensörler

| Sensör | Amaç |
|---|---|
| IMU (6/9 eksen) | Yatış açısı, EKF girdisi, ana ünite |
| Ayrı ivmeölçer (motor bloğuna monte) | Titreşim imzası — anomali tespiti için, ana IMU'dan bağımsız |
| GPS modülü + anten | Konum, hız doğrulama, viraj yarıçapı |
| IR sıcaklık sensörü | Lastik/fren yüzey sıcaklığı |
| Egzoz gaz sıcaklığı (EGT) sensörü + arayüz kartı | Motor sağlığı, yanma kalitesi |
| Yağ basıncı/sıcaklık sensörü (opsiyonel) | Yağlama teşhisi |
| I2S mikrofon | Sesli komut + akustik anomali tespiti (ortak) |
| 24 GHz mmWave radar (×2) | Kör nokta tespiti, sol+sağ |
| NFC okuyucu | İmmobilizer yetkilendirme |
| Ortam ışık sensörü (opsiyonel) | Gündüz/gece ayrımı |
| Kamera modülü | Şerit takip görüntü işleme |

## 3.4 Güç Donanımı

- Geniş girişli DC-DC dönüştürücü — MCU hattı için
- Geniş girişli DC-DC dönüştürücü — Raspi için, izole ayrı hat
- Süper kapasitör bankası + dengeleme devresi + akım sınırlayıcı — güvenli kapanma
- Güç izleme entegre devresi (gerilim/akım/güç) — her hat için bir adet
- Bistable röle — immobilizer marş devresi kilitleme
- Koruma bileşenleri (TVS diyot, ters polarite koruma MOSFET'i, sigorta) — her güç hattı için

## 3.5 Gösterge/Işık

- Mevcut Nextion ekran (ana bilgi ekranı)
- Adreslenebilir RGB LED şerit/halka — yatış açısı göstergesi (×2) ve shift-light
- Yüksek parlaklık LED — ayna içi kör nokta göstergesi (×2)

## 3.6 Depolama

- microSD modül + endüstriyel sınıf kart (araç üstü kayıt)

## 3.7 Mekanik/Montaj

- Su geçirmez muhafazalar (ana ünite, güç kartı, Raspi kutusu)
- Otomotiv sınıfı sızdırmaz konnektör seti
- Kablo rakoru ve O-ring contalar
- Titreşim izolasyon takozları, kablo koruma malzemesi, sigortalar
- Pasif soğutucu + basınç dengeleme membranı (Raspi muhafazası için)

## 3.8 Deneysel Doğrulama (opsiyonel/ileri aşama)

- Alternatif dişli seti (ölçüm sistemi duyarlılık doğrulaması için)
- Süspansiyon strok potansiyometreleri
- Harici dinamometre referans ölçümü (veya üniversite laboratuvar imkânı)

---

# 4. Repo Yapısı: Neden Çoklu-Repo, Her Reponun Amacı

## 4.1 Temel İlke

Repo sınırı, kod organizasyonu tercihi değil, çalışma zamanı sınırıdır: farklı fiziksel çipte, farklı dilde veya farklı ortamda çalışan her bileşen ayrı bir repo olarak tutulur. Aynı çipte/binary'de derlenen kod ise tek repo içinde klasör (modül) olarak organize edilir. Bu ayrım iki riski önler:

- **Aşırı bölme:** Aynı binary'de derlenen kodu ayrı repolara bölmek, sahte bir izolasyon görüntüsü verir ama gerçek bir fayda sağlamaz — sadece geliştirme sürtünmesi ekler.
- **Yetersiz bölme:** Farklı çip/dil/ortamdaki kodu tek repoda tutmak, birbirinden bağımsız sürümlenebilir, bağımsız test edilebilir parçaları yapay olarak birbirine kenetler.

## 4.2 Repo Listesi ve Amaçları

| # | Repo | Çalışma zamanı | Dil | Amaç |
|---|---|---|---|---|
| 1 | `moto-vehicle-defs` | — (paylaşılan tanım) | DBC/YAML/VSS | CAN mesaj haritası, VSS semantik model, UDS servis tanımları — tek gerçek kaynak |
| 2 | `moto-rt-core` | STM32H7 | C/C++ | Ana domain firmware: CAN, UDS/ISO-TP/bootloader, XCP, EKF, bağlam sınıflandırma, kayıt |
| 3 | `moto-connectivity-node` | ESP32-S3 | C/C++ | Wi-Fi/BLE bağlantısı, sesli komut |
| 4 | `moto-safety-node` | STM32 G4/F3 | C/C++ | Viraj güvenlik kararı — izole, tek sorumluluk |
| 5 | `moto-io-node` | STM32 G0/F0 | C/C++ | Kör nokta, immobilizer, güç yönetimi — birleşik zone controller |
| 6 | `moto-linux-node` | Raspberry Pi 5 | Python/C++ | Şerit takip, Kuksa/VSS köprüsü, anomali modeli, HMI, kamera |
| 7 | `moto-hil-bench` | STM32F4 (simülatör) + host bilgisayar | C/C++ + Python | Araç bağımsız HIL test tezgahı |
| 8 | `moto-server` | Sunucu | Python/Go | Veri deposu, zaman serisi veritabanı, görselleştirme |
| 9 | `moto-ml` | Offline (sunucu/iş istasyonu) | Python | Model eğitimi (çıkarım değil) |
| 10 | `moto-mobile` | Telefon | Flutter/React Native | Companion uygulama — ayarlar, geçmiş, rapor |
| 11 | `moto-mcp` | Raspberry Pi 5 (bağımsız repo) | Python | MCP sunucusu — LLM asistanının araç erişim katmanı |

## 4.3 Neden 11 Repo — Gerekçe Tablosu

| Ayrım | Gerekçe |
|---|---|
| `moto-rt-core` vs `moto-connectivity-node` | Farklı fiziksel çip (STM32H7 vs ESP32-S3), farklı derlenen binary, farklı flaş |
| `moto-safety-node` ayrı | ISO 26262 "girişimden bağımsızlık" ilkesi — güvenlik kritik karar, diğer yazılımlardan fiziksel olarak izole |
| `moto-io-node` ayrı | Farklı çip; ama içinde birden fazla fonksiyon (kör nokta+immobilizer+güç) birleşik — SDV zone-controller deseni, "her fonksiyona ayrı çip" değil |
| `moto-linux-node` ayrı | Tamamen farklı işletim sistemi/çalışma zamanı (Linux vs bare-metal/RTOS) |
| `moto-hil-bench` ayrı | Test aracı, üründen ayrı yaşam döngüsü; farklı donanımda (STM32F4) çalışır |
| `moto-server`, `moto-ml`, `moto-mobile` ayrı | Sunucu/offline/mobil — üçü de farklı çalışma zamanı ve dağıtım modeli |
| `moto-mcp` ayrı (istisna) | Çalışma zamanı `moto-linux-node` ile aynı (Raspi 5) ama paylaşım sınırı geçerli gerekçe — bağımsız açık kaynak proje olarak yayınlanması hedefleniyor |

**`moto-vehicle-defs`'in merkezi rolü:** Diğer 10 repo, sinyal/mesaj/servis tanımlarını buradan okur (submodule/paket referansı ile). Bu, "iki birim aynı sinyali farklı biliyor" hatasını yapısal olarak imkânsız kılar. `moto-vehicle-defs` semantik olarak sürümlenir (v1.0, v1.1...); bağımlı repolar belirli bir sürüme sabitlenir, böylece hangi kombinasyonun birlikte test edildiği/çalıştığı her zaman bilinir.

## 4.4 Repo İçi Modül Organizasyonu

Her repo kendi içinde katmanlı organize edilir (örnek: `moto-rt-core`):

```
/src/hal/         → donanım soyutlama (CAN, IMU, GPS, sensörler)
/src/services/     → sinyal havuzu, kayıt yöneticisi, EKF füzyon, zaman tabanı
/src/features/      → bağımsız fonksiyon modülleri (uds/, bootloader/, xcp/, cornering/, context/, dyno/, anomaly-safety-net/)
```

`features/` altındaki modüller birbirini tanımaz, yalnızca `services/`'e bağımlıdır — bir modül devre dışı bırakılırsa diğerleri çalışmaya devam eder.

---

# 5. Fonksiyonların Çalışma Yöntemleri (Metodoloji)

## 5.1 Protokol Yığını (UDS / ISO-TP / Bootloader / XCP)

**Ne yapar:** Motosikletin CAN hattından veri okur/yazar, standart otomotiv teşhis protokolüyle (UDS — ISO 14229) hem sunucu (kendi arıza kodlarını sunar) hem istemci (motosikletin ECU'sunu sorgular) rolünde çalışır.

**Nasıl çalışır:**
- **ISO-TP (ISO 15765-2):** CAN'ın 8 byte'lık çerçeve sınırını aşan mesajları segmentlere böler/birleştirir (ilk çerçeve, akış kontrolü, ardışık çerçeveler).
- **UDS:** Oturum kontrolü, güvenlik erişimi (seed-key), arıza kodu okuma/silme, veri okuma/yazma servisleri — hem sunucu hem istemci tarafı implementasyonu.
- **Bootloader:** UDS'in aktarım servisleri (0x34/0x36/0x37) üzerinden yeni firmware indirilir; A/B bank yapısıyla atomik geçiş yapılır; güç kesintisinde geri alma (rollback) mekanizması vardır.
- **XCP:** Kalibrasyon parametrelerinin çalışma anında (canlı) okunup değiştirilmesini sağlayan ayrı bir protokol; A2L tanım dosyası ile hangi parametrenin nerede olduğu tarif edilir.

## 5.2 Bağlam Sınıflandırma ve Bağlam Veri Yolu

**Ne yapar:** Sistemin geri kalanını koşullandıran temel katman — "şu an hangi koşuldayız" sorusuna cevap üretir ve bu cevabı ortak bir veri yolunda diğer tüm modüllere sunar.

**Nasıl çalışır:** IMU+CAN+GPS ham verisinden üç alt problem çözülür: yol tipi (CAN istatistikleri + hafif ML), yol yüzeyi (IMU titreşimi + hafif 1D-CNN), sürüş olayı sınıflandırması. Bunlara ek olarak araç durumu (kütle, termal, lastik), sürücü durumu (kimlik, yorgunluk, tarz) ve çevre durumu (hava/µ, gündüz-gece, trafik) koşullandırıcıları da aynı veri yoluna toplanır. Anomali tespiti, viraj güvenliği, sesli asistan ve kayıt frekansı gibi modüller bu ortak veri yolundan okuma yapar — her biri kendi bağlam mantığını tekrar hesaplamaz.

## 5.3 Kör Nokta Uyarı Sistemi

**Ne yapar:** Motosikletin yan/arka kör noktasına giren aracı tespit edip sürücüye görsel uyarı verir.

**Nasıl çalışır:** İki adet 24 GHz mmWave radar (sol+sağ), aracın mesafe ve yaklaşma hızını doğrudan ölçer. I/O düğümü (STM32 G0/F0) bu veriyi işler, "gerçekten yaklaşan araç mı yoksa sabit nesne mi" ayrımını hız/yön analiziyle yapar, sonucu ayna içine gömülü LED'lere (yeşil/kırmızı sabit/kırmızı yanıp sönen) yansıtır. Karar tamamen I/O düğümünde verilir — ana MCU veya CAN hattı çökse bile LED çalışmaya devam eder. Sinyal koluna basıldığında (yön değiştirme niyeti) uyarı güçlendirilir. Sistem, yatış açısı bilgisini bağlam veri yolundan alarak mesafe eşiğini yatışa göre hafifçe ayarlar (motosikletlerde nadir uygulanan bir düzeltme).

## 5.4 Viraj Güvenlik Uyarı Sistemi

**Ne yapar:** Sürücüye, girilen virajın mevcut hızla güvenli şekilde alınıp alınamayacağı konusunda erken uyarı verir.

**Nasıl çalışır:** Üç katmanlı, fiziksel olarak izole bir mimari:
- **Katman 1 (deterministik karar):** Kapalı form fizik formülleriyle (v_max = √(µ·g·R)) hesaplanan güvenli hız sınırı, ayrı bir güvenlik MCU'sunda (STM32 G4/F3) değerlendirilir ve uyarı burada üretilir. Bu katman, sistemin geri kalanı çökse bile bağımsız çalışır.
- **Katman 2 (EKF kestirimi):** Sürtünme katsayısı, araç kütlesi, ağırlık merkezi yüksekliği gibi doğrudan ölçülemeyen parametreler, Genişletilmiş Kalman Filtresi ile IMU/CAN verisinden kestirilir; fiziksel olarak makul aralıklara kırpılır. Bu katman ana MCU'da (STM32H7) çalışır ve sonucunu CAN üzerinden güvenlik MCU'suna yayınlar.
- **Katman 3 (ML kişiselleştirme, isteğe bağlı):** Sürücü profili ve yol bağlamına göre uyarı eşiği hafifçe ayarlanır — ama güvenlik tavanını asla gevşetemez.

Sinir ağı tabanlı (örn. PINN) bir yaklaşım yerine kapalı form + EKF tercih edilmesinin gerekçesi, güvenlik kritik bir kararın açıklanabilir ve test edilebilir olması zorunluluğudur.

## 5.5 İmmobilizer ve Güç Yönetimi

**Ne yapar:** Motoru yetkisiz çalıştırmaya karşı korur; park halinde hareket tespiti yapıp bildirim gönderir; tüm sistemin güç kesintilerine dayanıklı çalışmasını sağlar.

**Nasıl çalışır:** Müdahale noktası bilinçli olarak marş rölesi bobin devresi ile sınırlıdır — düşük akımlı, motor çalışırken tamamen işlevsiz bir devre; ateşleme/yakıt pompası/ECU hattına asla dokunulmaz (bu, giden bir motoru elektroniğin asla durduramayacağı anlamına gelir — kasıtlı güvenlik sınırı). Bistable röle, enerji harcamadan kilitli kalır. Yetkilendirme NFC ile (eldivenle okunabilir) yapılır, PIN yedek olarak durur. Fail-safe tasarım: varsayılan konum açık, gizli mekanik bypass anahtarı, karar veremezse otomatik açığa dönme. Park modunda IMU "harekette uyanma" tekniğiyle düşük güç modunda beklenir; hareket algılanırsa Wi-Fi üzerinden bildirim gönderilir. Güç kartı, süper kapasitör tamponuyla ani kesintide kayıt dosyasını güvenli kapatacak süre kazandırır.

## 5.6 Ekran ve Görsel Uyarı Mimarisi

**Ne yapar:** Sürücüye bilgiyi doğru arayüzle, doğru yerde sunar.

**Nasıl çalışır:** Tek bilgi ekranı (mevcut Nextion) + profil bazlı sayfa sistemi (şehir/tur/sportif/eko/medya) — gerçek yarış göstergelerinin (MoTeC, AIM) kullandığı, fiziksel düğmeyle sayfa geçen deseni izler; dokunmatik gezinme sürüş konforunu bozacağı için kullanılmaz. Yatış açısı, ayrı bir grafik ekran yerine göstergenin iki yanına yerleştirilen LED halkalarla (renk geçişli) gösterilir — bu tercih, insan periferik görüşünün bir rengi bir grafikten çok daha hızlı algılamasına dayanır ve ticari/patentli örneklerle doğrulanmıştır. Orijinal Honda göstergesine dokunulmaz.

## 5.7 Şerit Takip / Şerit İhlali Uyarı Sistemi

**Ne yapar:** Sürücü şeritten çıkarken uyarı verir.

**Nasıl çalışır:** Klasik görüntü işleme yöntemi (OpenCV) kullanılır — derin öğrenme değil, çünkü (a) sıfır eğitim verisi gerektirir, (b) Raspi 5 CPU'sunda hızlandırıcısız çalışır, (c) hazır derin öğrenme modelleri otomobil kamerasıyla eğitildiği için motosikletin yatan kamerasına aktarılamaz (domain gap). Adımlar: lens distorsiyon düzeltme → renk/gradyan eşikleme → kuş bakışı perspektif dönüşümü → şerit piksel takibi ve eğri uydurma → araç/şerit merkez mesafesi hesabı. Motosiklete özgü kritik fark: yatış açısı kamera görüntüsünü döndürdüğü için, bağlam veri yolundan alınan EKF yatış açısıyla mesafe ölçümü düzeltilir (otomobil algoritmaları bunu yapmaz, doğrudan kopyalanamaz).

## 5.8 Sesli Komut Sistemi

**Ne yapar:** Sürüş sırasında, bağlantı gerektirmeden, kapalı bir komut kümesiyle sesli etkileşim sağlar.

**Nasıl çalışır:** Espressif'in resmi ESP-SR çerçevesi (WakeNet + MultiNet) kullanılır — kendi model eğitimi gerekmez, 300 kelimeye kadar hazır destekli. Tetikleme wake-word değil, gidon üzerinde bas-konuş butonuyla yapılır — bu, rüzgar gürültüsünde yanlış tetiklenme riskini baştan ortadan kaldırır. ESP32-S3'ün vektör hızlandırıcısı üzerinde ~100-200ms gecikmeyle, tamamen çevrimdışı çalışır.

## 5.9 Moto-MCP ve Sürüş İçi LLM Asistanı

**Ne yapar:** Bağlantı varsa, araç verisini bilen (genel amaçlı değil) bir LLM ile doğal dil etkileşimi sağlar.

**Nasıl çalışır:** Model Context Protocol (MCP) standardında bir sunucu, araç durumuna erişim sağlayan tipli "araçlar" (tool) sunar (anlık durum, son istatistikler, olay günlüğü, anomali durumu, bakım durumu, geçmiş sürüş sorgusu). LLM bu araçları çağırarak hazır hesaplanmış sonuçları doğal dile çevirir — kendi matematiğini yapmaz, çünkü büyük dil modellerinin sayısal zaman serisi üzerinde güvenilir hesap yapmadığı bilinen bir sınırlamadır. Bağlantı yoksa (kırsal), sistem otomatik olarak offline sesli komut sistemine (§5.8) düşer. Mahremiyet gereği ham GPS konumu genel bağlam paketine dahil edilmez, sadece yerel olarak özetlenmiş bilgi (bölge, mesafe) paylaşılır.

## 5.10 Linux Node / SDV Katmanı

**Ne yapar:** Raspi üzerindeki tüm uygulamaların CAN'a doğrudan değil, standart bir aracı üzerinden erişmesini sağlar.

**Nasıl çalışır:** Eclipse Kuksa Databroker, VSS (Vehicle Signal Specification) semantik modeliyle çalışan merkezi bir sinyal aracısıdır — hiçbir uygulama ham CAN mesajı ayrıştırmaz, hepsi isimlendirilmiş, tipli sinyaller (`Vehicle.Powertrain.CombustionEngine.Speed` gibi) okur. Bu, sektörün (Bosch/BMW/Microsoft destekli Eclipse SDV girişimi) kullandığı standart bir mimari desendir.

## 5.11 Anomali/Arıza Tespit Modeli

**Ne yapar:** Motorun mekanik/elektriksel durumunda normalden sapmaları tespit eder, mümkün olduğunda arıza türünü sınıflandırır.

**Nasıl çalışır:** Çok modaliteli veri (CAN, yüksek frekanslı titreşim, akustik, termal, bağlam) Raspi 5 üzerinde tek birleşik modelde değerlendirilir — bu, modaliteler arası korelasyonu (tek başına anlamsız ama birlikte anlamlı olan sinyal kombinasyonlarını) yakalayabilmek için bilinçli bir mimari tercihtir. Ana MCU'da ise ayrı, basit kural tabanlı bir güvenlik ağı (ML değil, sabit eşikler) bulunur — Raspi çökse/yeniden başlasa bile sistemin tamamen sessiz kalmamasını garanti eder.

## 5.12 Veri Toplama ve Kayıt Altyapısı

**Ne yapar:** Her sürüşü, bağlantıdan bağımsız, güvenilir şekilde kaydeder.

**Nasıl çalışır:** Ana MCU, sinyalleri ikili (binary) formatta microSD karta yazar — blok bazlı, her bloğa CRC eklenmiş, ani kesintide kısmi kurtarma mümkün. Süper kapasitör tamponu, kontak kesildiğinde dosyayı güvenli kapatacak süreyi sağlar. Araç Wi-Fi menziline (ev) girdiğinde veri otomatik olarak sunucuya senkronize edilir; arşivleme için MDF4 (otomotiv standart ölçüm formatı) formatına dönüştürülür.

## 5.13 Sanal Dinamometre

**Ne yapar:** Motorun tekerlek gücü ve torkunu, harici bir dinamometreye ihtiyaç duymadan, mevcut sensör verisinden hesaplar.

**Nasıl çalışır:** Boylamsal ivme (IMU), hız (CAN/GPS) ve bilinen araç parametrelerinden (kütle, aktarma oranları, tekerlek yarıçapı) yola çıkarak tekerlek kuvveti ve gücü hesaplanır; yuvarlanma ve aerodinamik direnç katsayıları, motor boşta bırakılıp yavaşlatılarak (coast-down testi) ayrıca kalibre edilir. Sabit vitesle tam gaz hızlanma koşuları, tork-devir ve güç-devir eğrilerini üretir. Doğrulama üç ayakta yapılır: tekrarlanabilirlik (aynı koşuda birden fazla ölçüm), duyarlılık (dişli oranı gibi bilinen bir değişikliğin beklenen etkiyle örtüşmesi) ve mümkünse harici dinamometreyle karşılaştırma.

## 5.14 Konfor, Enerji ve Sürücü Destek Fonksiyonları

Bağlam veri yolu ve mevcut sensör altyapısı üzerine kurulu, çoğunlukla düşük ek maliyetli tamamlayıcı fonksiyonlar:

**Konfor:**

| Fonksiyon | Açıklama |
|---|---|
| Adaptif gösterge parlaklığı | Ortam ışığına göre otomatik gündüz/gece ayarı |
| Isıtmalı el kumandası kontrolü | Sıcaklığa göre otomatik ayar |
| Otomatik sinyal iptali | Dönüş tamamlanınca IMU verisiyle sinyal otomatik kapanır |
| Acil fren sinyali | Sert frende stop lambası hızlı yanıp söner |
| Yokuş kalkış desteği bildirimi | Eğim ve duruş tespitiyle bilgilendirme |
| Rüzgar/hava durumu uyarısı | Bağlantı varsa yol koşulu bilgisi |
| Yorgunluk/dikkat tespiti | Sürüş düzensizliği paterninden çıkarım |
| Sürüş günlüğü ve istatistik | Km, süre, ortalama hız, rota geçmişi |
| Sosyal/grup sürüş takibi | Birden fazla aracın konum paylaşımı |
| Sesli navigasyon entegrasyonu | Telefon navigasyonu + sesli yönlendirme |

**Enerji Yönetimi:**

| Fonksiyon | Açıklama |
|---|---|
| Enerji akış izleme | Alternatör çıkışı ile yük dengesi |
| Akü şarj durumu ve sağlık kestirimi | SoC/SoH tahmini |
| Düşük gerilim koruma | Kritik olmayan yüklerin otomatik kesilmesi |
| Rejeneratif fren analizi | Kavramsal — gelecek elektrikli araç uyarlaması için |
| Uyku/uyanıklık güç bütçesi yönetimi | Sürüş moduna göre tüketim optimizasyonu |

**Sürücü Destek:**

| Fonksiyon | Açıklama |
|---|---|
| Sürücü kimliği ve kişisel profil | Kim sürüyorsa ona göre ayar yükleme |
| Sürüş becerisi gelişim takibi | Zaman içinde tutarlılık/hız trendi |
| Kaza sonrası otomatik bildirim (eCall benzeri) | Düşme tespiti + konum + acil bildirim — motosiklet güvenliğinde somut bir ihtiyaç, AB'de otomobiller için zorunlu olan sistemin motosiklet uyarlaması |
| Geofence / bölge uyarıları | Belirli bölgeye giriş/çıkış bildirimi |
| Hız limiti uyarısı | Harita tabanlı, konuma göre limit bilgisi |

---



## 6.1 Mimari Felsefe

Modern SDV (yazılım tanımlı araç) yaklaşımı, eski "her fonksiyona bir ECU" paradigmasından uzaklaşıp az sayıda güçlü işlem birimi + bir güvenlik izleyici + gerektiği kadar uç düğüm kullanır. Bu projede aynı felsefe izlenmiştir: yeni bir fonksiyon eklemek genellikle yeni donanım değil, mevcut bir düğüme yazılım modülü eklemek anlamına gelir.

**Temel ayrım ilkesi:** Gerçek zamanlı/güvenlik kritik iş ile zengin/hesaplama yoğun iş asla aynı çipte çalıştırılmaz.

## 6.2 Mimari Şeması

```
                        ARAÇ CAN HATTI
        ═════╤═════════════╤═════════════╤═══════
             │             │             │
        ┌────┴───┐   ┌─────┴─────┐  ┌────┴────┐
        │STM32H7 │   │  STM32    │  │  STM32  │
        │ ANA    │   │  G4/F3    │  │  G0/F0  │
        │DOMAIN  │   │  SAFETY   │  │  I/O    │
        └──┬──┬──┘   └───────────┘  └────┬────┘
           │  │SPI                       │
      ┌────┴┐ └──┐                  aktüatörler
      │ESP32│ ┌──┴───┐              (ışık, ısıtma,
      │ S3  │ │Raspi5│               immobilizer, güç)
      │BLE/ │ │LINUX │
      │ ML  │ │ HPC  │
      └─────┘ └──────┘
```

## 6.3 Birim Bazlı Görev Dağılımı

| Birim | Çip | SDV rolü | Görev |
|---|---|---|---|
| Ana MCU | STM32H7 | Domain controller | CAN, telemetri, kayıt, füzyon, UDS/ISO-TP/bootloader, XCP, bağlam sınıflandırma, EKF kestirimi (viraj için), sanal dinamometre, anomali güvenlik ağı |
| Bağlantı+ML | ESP32-S3 | Yardımcı düğüm | Wi-Fi/BLE, sesli komut (ESP-SR/TinyML) |
| Güvenlik | STM32 G4/F3 | Safety monitor | Viraj güvenlik kararı — fiziksel olarak izole |
| I/O | STM32 G0/F0 | Zone/edge controller | Kör nokta, immobilizer, güç yönetimi (birleşik) |
| Linux | Raspberry Pi 5 | HPC | Şerit takip, kamera, ağır ML çıkarımı (anomali), HMI, LLM köprüsü |

## 6.4 Neden Bu Kadar Az Birim (5), Neden Bu Kadar Çok Değil

Mimari kararı iki karşıt riski dengeler:

- **Az fazla bölme (ör. her fonksiyona ayrı çip):** Eski "dağıtık ECU" paradigmasına geri dönüş; her ek çip bağlantı gecikmesi, senkronizasyon, güç bütçesi ve bakım yükü ekler.
- **Az fazla birleştirme (ör. tek çipte her şey):** Güvenlik kritik fonksiyonun kritik olmayan bir modülün (örn. kayıt) hata/gecikmesinden etkilenmesi riski; ISO 26262'nin "girişimden bağımsızlık" ilkesini ihlal eder.

Bu projede yalnızca gerçek bir izolasyon veya çalışma zamanı gerekçesi olan yerlerde ayrı birim kullanılmıştır (güvenlik izolasyonu → safety MCU; RF/Wi-Fi özel donanımı → ESP32; Linux gerektiren ağır işlem → Raspi). Kör nokta, immobilizer ve güç yönetimi gibi birbirinden bağımsız ama benzer ağırlıkta işler tek bir I/O düğümünde birleştirilmiştir (zone-controller deseni) — her biri için ayrı çip açmak gereksiz donanım çoğalmasına yol açardı.

## 6.5 CAN Bağlantı Topolojisi

Her MCU, kendi CAN transceiver'ı ile doğrudan araç CAN hattına bağlıdır (bir aracı/köprü düğümü üzerinden değil) — bu, düğümler arası gecikmeyi ortadan kaldırır. CAN'ın yayın (broadcast) doğası gereği her düğüm her mesajı eşzamanlı alır; yalnızca bir düğüm (ana MCU) hatta yazar, diğerleri dinler — hat çakışması bu şekilde önlenir.

---

# 7. MCU'lar ve Teknik Yeterlilik Değerlendirmesi

Bu bölüm, seçilen her çipin genel donanım özelliklerinin, kendisine atanan iş yükünü karşılayıp karşılamadığının dürüst bir değerlendirmesidir.

## 7.1 STM32H7 (Ana Domain MCU)

| Özellik | Yaklaşık değer |
|---|---|
| Çekirdek | ARM Cortex-M7, ~480 MHz |
| FPU | Çift hassasiyetli, DSP talimat seti |
| Bellek | ~1-2 MB flash, ~1 MB SRAM (aile/varyanta göre değişir) |
| CAN | Birden fazla FDCAN çevre birimi |

**İş yükü:** CAN/ISO-TP/UDS protokol yığını, telemetri tamponlama+kayıt, EKF sensör füzyonu, bağlam sınıflandırma (hafif ML), sanal dinamometre hesabı, anomali güvenlik ağı (kural tabanlı), XCP sunucusu, bootloader.

**Değerlendirme:** Bu, gerçek zamanlı iş yükleri arasında en yoğun olanıdır, ancak Cortex-M7 sınıfı çipler endüstride tam olarak bu tür birleşik iş yükleri (protokol yığını + sensör füzyonu + hafif ML çıkarımı) için kullanılır. FPU ve DSP talimatları EKF matris işlemlerini ve filtre hesaplarını native hızda yapar. Sonuç: yeterli, konforlu marjla. Gelecekte eklenecek yeni `features/` modülleri için de işlemci gücünde rezerv bulunmaktadır.

## 7.2 ESP32-S3 (Bağlantı + Ses MCU)

| Özellik | Yaklaşık değer |
|---|---|
| Çekirdek | Çift çekirdekli Xtensa LX7, ~240 MHz |
| Özel donanım | Vektör/SIMD talimat uzantıları (AI/ML hızlandırma) |
| Bellek | ~512 KB SRAM + harici PSRAM (tipik 8 MB'a kadar) |
| Bağlantı | Wi-Fi 802.11, Bluetooth 5.0 (BLE) |
| CAN | Dahili TWAI denetleyicisi mevcut |

**İş yükü:** Wi-Fi/BLE yığını, ESP-SR (WakeNet+MultiNet) sesli komut çıkarımı.

**Değerlendirme:** Bu görev kombinasyonu (kablosuz bağlantı + gömülü ses tanıma), Espressif'in ESP-SR çerçevesini doğrudan bu çip için tasarlamış olması nedeniyle referans/tasarım amacına birebir uymaktadır. Sonuç: ideal eşleşme, çip bu iş için özel olarak seçilmiştir ve fazlasıyla yeterlidir.

## 7.3 STM32 G4/F3 (Güvenlik MCU)

| Özellik | Yaklaşık değer |
|---|---|
| Çekirdek | ARM Cortex-M4, ~170 MHz (G4 ailesi) |
| FPU | Tek hassasiyetli |
| Özel donanım | Donanımsal CORDIC/FMAC (trigonometrik/matematik hızlandırma, G4 ailesinde) |
| CAN | FDCAN destekli varyantlar mevcut |

**İş yükü:** Kapalı form fizik hesabı (v_max = √(µ·g·R)), eşik karşılaştırması, LED tetikleme, CAN alış/gönderme, watchdog.

**Değerlendirme:** Bu iş yükü, çipin kapasitesinin oldukça altındadır — hesaplama açısından "gereğinden güçlü" bir seçim gibi görünebilir. Ancak bu, güvenlik kritik bir düğümde bilinçli bir tercihtir: düşük kullanım oranı, gelecekte ek doğrulama mantığı (örn. yerel sensör okuma, çift hesaplama yolu) eklenmesi için pay bırakır ve deterministik zamanlama garantisini kolaylaştırır. Sonuç: fazlasıyla yeterli, kasıtlı marj.

## 7.4 STM32 G0/F0 (I/O MCU)

| Özellik | Yaklaşık değer |
|---|---|
| Çekirdek | ARM Cortex-M0/M0+, ~48-64 MHz |
| FPU | Yok (bazı G0 varyantlarında yok) |
| CAN | FDCAN destekli varyantlar mevcut (G0 ailesinin bir kısmında) |

**İş yükü:** İki radar sensörünün okunması, basit yaklaşma mantığı, LED/WS2812 sürme, immobilizer röle kontrolü, NFC okuma, güç izleme, CAN haberleşmesi.

**Değerlendirme:** Bu, giriş/çıkış ağırlıklı, düşük hesaplama yoğunluklu bir iştir — matris işlemi veya yoğun matematik gerekmez. Cortex-M0/M0+ sınıfı çipler, gerçek otomotivde tam olarak bu tür bölgesel gövde kontrol/I/O toplama görevlerinde kullanılır. Sonuç: doğru boyutlandırılmış — ne fazla güçlü (israf) ne yetersiz.

## 7.5 Raspberry Pi 5 8GB (Linux/HPC Birimi)

| Özellik | Yaklaşık değer |
|---|---|
| Çekirdek | Dört çekirdekli ARM Cortex-A76, ~2.4 GHz |
| Bellek | 8 GB LPDDR4X |
| Video | Donanımsal video kodlama/kod çözme bloğu |
| CAN | Dahili yok — harici denetleyici (SPI tabanlı) gerekir |

**İş yükü:** OpenCV şerit takip pipeline'ı, Kuksa Databroker + CAN köprüsü, birleşik anomali modeli çıkarımı, video kayıt/kodlama, HMI render, MCP sunucusu, çeşitli yardımcı servisler (NTP, yerel veritabanı, harita önbelleği).

**Değerlendirme:** Genel amaçlı hesaplama gücü bu iş yükleri için fazlasıyla yeterlidir, ancak bir koşulla: çok modaliteli anomali modelinin akustik (ses) katmanı sürekli tam hızda değil, periyodik pencere analiziyle çalıştırılmalıdır; aksi halde diğer sürekli görevlerle (şerit takip, HMI) birlikte kapasite sıkışabilir. Ayrıca konteyner tabanlı OTA yönetimi (Eclipse Kanto) bilinçli olarak MVP kapsamı dışında tutulmuş, basit Linux servisleriyle başlanması planlanmıştır. Sonuç: yeterli, koşullu (duty-cycling disiplinine bağlı) — bu proje genelinde "koşulsuz yeterli" denemeyen tek birim budur ve bu dürüstçe belirtilmelidir.

## 7.6 Özet Değerlendirme Tablosu

| Birim | Yeterlilik | Not |
|---|---|---|
| STM32H7 | Yeterli, konforlu marj | En yoğun iş yükü, doğru sınıf seçim |
| ESP32-S3 | İdeal eşleşme | Çip bu iş için tasarlanmış |
| STM32 G4/F3 | Fazlasıyla yeterli | Kasıtlı güvenlik marjı |
| STM32 G0/F0 | Doğru boyutlandırılmış | Ne israf ne yetersiz |
| Raspberry Pi 5 | Yeterli, koşullu | Duty-cycling disiplinine bağlı |

---

# 8. HIL Test Tezgahı — Amaç, Mimari, MCU

## 8.1 Amaç

Geliştirilen gömülü ünitenin (DUT), gerçek araca bağlanmadan, kontrollü ve tekrarlanabilir şekilde test edilmesi. HIL tezgahı, motosikletin elektriksel ortamını (CAN trafiği, besleme profili, arıza durumları) masada taklit eder.

## 8.2 Temel İlke — Neyin Aynı, Neyin Farklı Olması Gerektiği

- **DUT'un gördüğü arayüz aynı olmalı** (zorunluluk): CAN transceiver tipi, CAN hızı/protokolü, OBD2 konnektör, sinyal tanımları, besleme gerilim profili — bunlar gerçek araçla birebir eşleşmezse test geçersiz olur.
- **Simülatörün "beyni" farklı olmalı** (bağımsızlık ilkesi): Simülatör çipi, DUT'un ana çipiyle aynı olursa, ikisi aynı kütüphane hatasını/kör noktasını paylaşabilir ve test bu hatayı yakalayamaz. Bu nedenle simülatör, DUT'un ana çipinden (STM32H7) farklı bir sınıfta (STM32F4) ama aynı üretici ailesinde (tek araç zinciri, öğrenme kolaylığı) seçilmiştir.

## 8.3 Mimari — Restbus Simülasyonu

Aracı bütünüyle taklit etmek için, tek güçlü bir çip yazılımda birden fazla sanal ECU'yu (motor ECU, ABS, gösterge) farklı CAN kimlikleriyle canlandırır — bu, sektörde "restbus simülasyonu" olarak bilinen, gerçek CANoe/CANalyzer gibi araçların kullandığı standart yöntemdir.

```
        HOST (masaüstü bilgisayar, Linux)
        senaryo motoru, loglama, rapor
              │ USB/UART
        ┌─────┴──────┐
        │  STM32F4   │  ← SİMÜLATÖR DÜĞÜMÜ
        │ · restbus (çok sanal ECU)
        │ · basit araç dinamik modeli
        │ · CAN mesaj üretimi
        └──┬───────┬─┘
           │CAN    │kontrol
      ═════╪═══    │
      test │   ┌───┴────────┐
     edilen│   │ STM32F103  │ ← arıza enjeksiyonu +
     cihaz │   │ + prog.    │   programlanabilir besleme
     (DUT)─┘   │ besleme    │   (bozuk çerçeve, hat kesme,
               └────────────┘    voltaj profili)
```

## 8.4 MCU Seçimi ve Gerekçesi

| Bileşen | Çip | Gerekçe |
|---|---|---|
| Simülatör beyni | STM32F4 ailesi | FPU (araç dinamik modeli için), çok CAN çevre birimi, sektörde yaygın kullanım (bilinen bir açık kaynak araç-CAN donanım projesi de aynı çip ailesini kullanmaktadır — bağımsız doğrulama), araç ana çipinden (H7) farklı sınıf |
| Arıza/besleme kontrol | STM32F103 (mevcut donanım) | Basit, düşük maliyetli, voltaj/hat kontrolü için yeterli |
| Host | Masaüstü bilgisayar + Linux | SocketCAN native desteği, kalıcı test istasyonu/ileride CI runner potansiyeli |

**Değerlendirilip elenen alternatif:** Gerçek otomotiv sınıfı bir çip (örn. NXP S32K ailesi) simülatör için daha "otantik" olurdu, ancak geliştirme kartı maliyeti ve öğrenme eğrisi projenin bu aşaması için orantısız bulunmuş, Faz 2 hedefi olarak not edilmiştir.

## 8.5 Host ile Simülatör Ayrımı

Host bilgisayar (senaryo motorunu Python ile koşturan taraf) ile simülatör MCU'su (gerçek CAN sinyalini üreten taraf) net olarak ayrılmıştır: host "beyin/senaryo", simülatör "eller/sinyal üretimi" rolündedir. Bilgisayarın kendi başına CAN donanımı yoktur, bu nedenle simülatör MCU'su zorunludur.

## 8.6 Kontrol Paneli ve Görselleştirme

Host tarafında üç ayrı modül bulunur: senaryo motoru (mantık), kontrol paneli/görselleştirme (web tabanlı dashboard — canlı CAN trafiği, gecikme grafikleri, test durumu), değerlendirici (beklenen/gerçek karşılaştırması, rapor üretimi). Bu yapı, endüstriyel HIL sistemlerindeki (örn. dSPACE ControlDesk) kontrol masası mantığının ölçeklenmiş halidir. Gerçekçi bir sürüş simülatörü veya oyun deneyimi bilinçli olarak kapsam dışıdır — amaç test aracı olmak, eğlence/görselleştirme aracı olmak değildir.

## 8.7 HIL'in Doğruladığı Örnek Senaryo Sınıfları

- Besleme kaynaklı: marş anı voltaj çökmesi, düşük/yüksek gerilim, mikro kesinti
- Veri yolu kaynaklı: ECU yanıt vermemesi, bozuk çerçeve, aşırı veri yolu yükü, bus-off ve kurtarma
- Sinyal kaynaklı: mantıksız sıçrama, sinyal donması
- Dayanıklılık: uzun süreli kesintisiz çalışma

---

# 9. Sürdürülebilirlik ve Ölçeklenebilirlik Analizi

## 9.1 Yazılımsal Ölçeklenebilirlik

SDV domain-controller yaklaşımı sayesinde, yeni bir fonksiyon eklemek genellikle yeni donanım değil, mevcut bir düğüme yeni bir yazılım modülü eklemek anlamına gelir. Bu, projenin donanım maliyetini sabit tutarken fonksiyon setini büyütebilmesini sağlar — modern otomotiv endüstrisinin de aynı gerekçeyle benimsediği bir yaklaşımdır.

## 9.2 Araç Bağımsızlığı ve Taşınabilirlik

`moto-vehicle-defs` reposu, sinyal/protokol tanımlarını tek bir kaynakta tutarak, sistemin başka bir araca taşınabilirliğini mimari düzeyde destekler. HIL test tezgahı da bilinçli olarak araç bağımsız tasarlanmıştır (CL250, `vehicles/cl250/` altında sadece bir "uygulama" olarak durur) — ikinci bir araç eklemek, çekirdek koda dokunmadan yeni bir tanım klasörü eklemekle mümkündür. VSS'in (Vehicle Signal Specification) endüstri standardı bir taksonomi olması, bu taşınabilirliği kağıt üzerinde kalan bir iddia değil, gerçek bir mimari özellik yapar.

## 9.3 Bağımsız Sürümlenebilirlik

Çoklu-repo yapısı, her bileşenin (ör. `moto-rt-core` firmware'i, `moto-linux-node` yazılımı) `moto-vehicle-defs` sözleşmesine uyduğu sürece birbirinden bağımsız güncellenebilmesini sağlar. Bir modülün geliştirilmesi, diğerlerinin yeniden derlenmesini/test edilmesini gerektirmez.

## 9.4 Saha Güncellenebilirliği (OTA)

Bootloader modülü (UDS tabanlı, A/B bank, rollback korumalı), MCU firmware'lerinin fiziksel erişim olmadan güncellenmesini sağlar. Linux tarafında da benzer bir dağıtım mekanizması (basit servis, ileride konteyner tabanlı) planlanmıştır. Bu, sistemin dağıtıldıktan sonra da (donanım sabit kalarak) yazılım/model iyileştirmeleriyle gelişmeye devam edebileceği anlamına gelir.

## 9.5 Dayanıklılık — Kademeli Bozulma (Graceful Degradation)

Mimarinin "gevşek bağlama" ilkesi, her düğümün diğerleri olmadan da temel işlevini sürdürmesini garanti eder: Linux/Raspi çökerse güvenlik kritik fonksiyonlar (viraj uyarısı, kör nokta) çalışmaya devam eder; ana MCU ile Raspi arasındaki bağlantı kesilirse anomali tespitinde bile minimum bir kural tabanlı güvenlik ağı devrededir. Bu, sistemin kısmi arıza altında da güvenli kalmasını sağlayan bir sürdürülebilirlik/güvenilirlik özelliğidir.

## 9.6 Açık Kaynak Bağımlılık Stratejisi

Sistem, tescilli/kapalı araçlar yerine büyük ölçüde açık kaynak bileşenlere (Eclipse Kuksa, Velocitas, ESP-SR, kendi geliştirdiği `moto-mcp`) dayanır. Bu, uzun vadeli bakım maliyetini ve tek bir tedarikçiye bağımlılığı azaltır; ayrıca geliştirilen `moto-mcp` ve toplanan veri setinin (Hugging Face üzerinden) açık kaynak/açık veri olarak paylaşılması, projenin kendi ekosistemine katkı sağlamasını mümkün kılar.

## 9.7 Veri Odaklı Sürekli İyileştirme

Araçtan sunucuya akan veri, periyodik ve sürümlü (insan onaylı) yeniden eğitim döngüsüyle modelleri iyileştirir — "sürekli/anlık öğrenme" değil, kontrollü, test edilmiş, OTA ile dağıtılan model güncellemeleri. Bu, sistemin sahada kaldığı sürece veri biriktirerek "akıllanabileceği", ama bunun denetimsiz/güvenlik riski taşıyan bir şekilde olmayacağı anlamına gelir.

## 9.8 Kaynak Verimliliği (Çevresel Boyut)

Yük-saati bazlı bakım takibi modülü, sabit kilometre aralıklarıyla değil gerçek kullanıma göre bakım zamanlaması önerir — bu, gereksiz parça değişimini azaltarak kaynak israfını sınırlayan, mütevazı ama gerçek bir sürdürülebilirlik katkısıdır (SDG 12.5 ile ilişkili).

---

# 10. Sektörel Karşılaştırma: ADAS / SDV Standartlarına Uygunluk

## 10.1 Genel Çerçeve

Aşağıdaki tablo, projede izlenen yöntemlerin gerçek otomotiv endüstrisi pratikleriyle karşılaştırmasını sunar. Amaç, projenin resmi bir sertifikasyon iddiası taşımadığını açıkça belirtirken, izlenen mimari desenlerin ve yöntemlerin endüstri standardıyla ne ölçüde örtüştüğünü göstermektir.

## 10.2 Karşılaştırma Tablosu

| Endüstri standardı/pratiği | Bu projede karşılığı | Uygunluk düzeyi |
|---|---|---|
| AUTOSAR katmanlı yazılım mimarisi (SWC/RTE) | `moto-rt-core` içinde HAL/services/features katmanlı organizasyonu | Kavramsal olarak uyumlu (sertifikalı AUTOSAR aracı kullanılmıyor) |
| ISO 26262 — girişimden bağımsızlık | Fiziksel olarak izole güvenlik MCU'su (viraj kararı) | Doğrudan uygulanmış |
| ISO 26262 — ASIL sınıflandırma ve süreç | HARA (tehlike analizi) yapılması planlı | Süreç uygulanıyor; resmi ASIL sertifikasyonu yok |
| ISO 14229 (UDS) | Sıfırdan implementasyon, sunucu+istemci | Doğrudan uygulanmış |
| ISO 15765-2 (ISO-TP) | Sıfırdan implementasyon | Doğrudan uygulanmış |
| ISO 21434 (siber güvenlik, TARA) | Backlog'da (planlı ama çekirdek kapsamda değil) | Kısmi — gelecek çalışma |
| Restbus simülasyonu (CANoe/CANalyzer benzeri) | STM32F4 tabanlı özel HIL simülatörü | Aynı yöntem, farklı ölçek |
| Radar+kamera tabanlı ADAS (kör nokta, şerit takip) | 24 GHz radar (BSM) + kamera+IMU (LDW) | Aynı sensör modalitesi tercihleri, motosiklete uyarlanmış |
| VSS (Vehicle Signal Specification) | `moto-vehicle-defs` + Kuksa Databroker | Doğrudan uygulanmış (COVESA standardı) |
| SDV domain/zone controller mimarisi | 5 birimlik dağıtık mimari | Doğrudan uygulanmış |
| OTA güncelleme (UDS tabanlı) | Bootloader modülü, A/B bank | Doğrudan uygulanmış |
| MISRA-C kodlama standardı | Hedef, tam araç zinciri sertifikasyonu yok | Kısmi/aspirasyonel |
| Gerçek otomotiv sınıfı MCU (AURIX, S32K) | Öğrenilebilir muadiller (STM32 ailesi) kullanıldı | Kavramsal eşdeğer, sertifikalı silikon değil |

## 10.3 Dürüst Sınırlar

Bu proje, endüstri yöntemlerini ve mimari desenlerini uygulayan akademik/prototip ölçekli bir çalışmadır; resmi bir ASIL sertifikasyon sürecinden, MISRA-C araç zinciri denetiminden veya ISO 21434 TARA sürecinden geçmemiştir. Kullanılan MCU'lar (STM32 ailesi, ESP32) gerçek üretim araçlarında kullanılan sertifikalı silikon (AURIX, S32K gibi) değil, bunların öğrenme amaçlı, kavramsal olarak eşdeğer muadilleridir. Bu sınırlar, projenin akademik bağlamında beklenen ve kabul edilebilir bir durumdur; raporun amacı, hangi noktada gerçek endüstri pratiğine ne kadar yaklaşıldığını şeffaf şekilde ortaya koymaktır.

---

# 11. Sistem İş Akışı

## 11.1 Açılış Sırası (Kontak Açılışı)

1. Güç kartı, kontak sinyalini algılar, ana besleme hatları aktifleşir.
2. Her MCU kendi başlangıç rutinini çalıştırır (donanım soyutlama katmanı, CAN denetleyici, sensör arayüzleri).
3. Ana MCU (STM32H7), CAN hattını dinlemeye başlar; sinyal havuzu ve bağlam veri yolu servisleri başlatılır.
4. Güvenlik MCU'su ve I/O MCU'su bağımsız olarak kendi başlangıç kontrollerini yapar (watchdog, sensör sağlık kontrolü).
5. Bağlantı MCU'su (ESP32-S3), bilinen ağlara bağlanmayı dener (arka planda, kritik yola bağımlı değil).
6. Raspi 5, işletim sistemi açılışının ardından Kuksa Databroker ve bağlı servisleri başlatır; bu süreç, ana MCU'nun temel işlevlerinden bağımsız yürür.

## 11.2 Sürüş Sırasında Sürekli Akış

```
Sensörler (CAN, IMU, GPS, sıcaklık, radar, kamera, mikrofon)
        │
        ▼
Bağlam sınıflandırma + bağlam veri yolu (sürekli güncellenir)
        │
   ┌────┼────────┬─────────┬──────────┬───────────┐
   ▼    ▼         ▼         ▼         ▼           ▼
Kayıt  Viraj    Kör       Şerit     Anomali    Ekran/
       güvenlik nokta     takip     tespiti    ses geri
                                               bildirimi
```

Bu akış kesintisizdir; her modül kendi döngüsünde bağlam veri yolunu okur, kendi çıktısını üretir. Güvenlik kritik modüller (viraj, kör nokta) bu akıştan bağımsız, kendi izole döngülerinde de çalışabilir durumdadır.

## 11.3 Olay Bazlı Akış (Tetikleyici Anlar)

| Tetikleyici | Akış |
|---|---|
| Sürücü bas-konuş butonuna basar | Ses yakalanır → ESP-SR ile yerel tanıma → sabit yanıt (offline) VEYA bağlantı varsa Moto-MCP'ye yönlendirilir |
| Anomali eşiği aşılır | Olay günlüğüne yazılır → "kara kutu" tam çözünürlüklü kayıt tetiklenir → HMI'da bildirim |
| Kontak kapatılır | Güç kartı süper kapasitör tamponuna geçer → kayıt dosyası güvenli kapatılır → düğümler sırayla kapanır |
| Araç Wi-Fi menziline girer | Biriken veri sunucuya senkronize edilir → arşiv formatına (MDF4) dönüştürülür |
| Yeni firmware sürümü yayınlanır | Sunucudan indirilir → UDS bootloader ile ilgili MCU'ya A/B bank üzerinden yazılır → doğrulama → aktif banka değişimi |

## 11.4 Çevrimdışı (Sürüş Sonrası) Akış

Sunucuya ulaşan veri, periyodik model yeniden eğitimi için kullanılır (`moto-ml`); yeni model, test/doğrulama sonrası (insan onaylı) OTA ile araca geri dağıtılır. Bu, sistemin "öğrenen" tarafının sürüş sırasında değil, kontrollü bir çevrimdışı döngüde gerçekleştiğini gösterir.

---

# 12. Senaryo Bazlı İş Akışı Örnekleri

Bu bölüm, her ana fonksiyonun somut bir kullanım anında sistem içinde nasıl bir veri/karar akışı ürettiğini gösterir.

## Senaryo 1 — Kör Nokta: Sağdan Araç Yaklaşıyor

1. Sağ radar, 15 metre mesafede, yaklaşan bir nesne tespit eder.
2. I/O MCU, nesnenin hız/yön profilini analiz eder — sabit nesne (bariyer) değil, yaklaşan araç olduğuna karar verir.
3. Sağ ayna LED'i sabit kırmızıya döner.
4. Sürücü sağ sinyale basar (şerit değiştirme niyeti) → LED yanıp sönmeye başlar, uyarı güçlenir.
5. Durum CAN'a yayınlanır; ana MCU loglar, HMI isterse gösterir.

## Senaryo 2 — Viraj Güvenliği: Virajı Hızlı Alma

1. GPS + IMU, önde bilinen yarıçapta bir viraj ve artan hızı tespit eder.
2. Ana MCU'daki EKF, güncel sürtünme katsayısı ve kütle kestirimini günceller, CAN'a yayınlar.
3. Güvenlik MCU'su, kapalı form formülüyle güvenli maksimum hızı hesaplar, mevcut hızla karşılaştırır.
4. Eşik aşılmak üzereyse LED halka sarıya, aşılırsa kırmızıya döner; sportif profilde ekranda sayısal uyarı belirir.
5. Bu karar zinciri, ana MCU veya Raspi'nin o anki durumundan bağımsız olarak, güvenlik MCU'sunda tamamlanır.

## Senaryo 3 — Şerit Takip: Yorgunlukla Şeritten Kayma

1. Raspi'deki kamera pipeline'ı, şerit-merkez mesafesinin arttığını tespit eder.
2. Bağlam veri yolundan alınan yatış açısı ile görüntü ölçümü düzeltilir (yanlış pozitifi önlemek için).
3. Sinyal koluna basılmadığı doğrulanır (bilinçli şerit değişimi değil).
4. Eşik aşılırsa HMI/ses uyarısı tetiklenir.

## Senaryo 4 — İmmobilizer: Yetkisiz Çalıştırma Denemesi

1. Kontak açılır, marş denenir.
2. I/O MCU, geçerli bir NFC etiketi veya PIN girişi olmadığını tespit eder.
3. Bistable röle kilitli konumda kalır — marş rölesi bobin devresi açık, marş motoru enerjilenmez.
4. 10 saniyelik karar zaman aşımı sonunda sistem (güvenlik gerekçesiyle) varsayılan açık konuma döner — bu, "sonsuza kadar kilitli kal" değil, "belirsizlikte güvenli tarafa düş" ilkesidir.

## Senaryo 5 — Anomali Tespiti: Gelişmekte Olan Arıza

1. Motor bloğu ivmeölçeri, birkaç sürüş boyunca kademeli olarak değişen bir titreşim imzası kaydeder.
2. Raspi'deki birleşik anomali modeli, CAN+titreşim+akustik+termal veriyi birlikte değerlendirir, anomali skorunu yükseltir.
3. Skor eşiği aşarsa olay günlüğüne yazılır, HMI'da bakım önerisi olarak gösterilir.
4. Raspi o an kullanılamıyorsa, ana MCU'daki kural tabanlı güvenlik ağı (sıcaklık/devir eşikleri) minimum korumayı sürdürür.

## Senaryo 6 — Sesli Komut: Offline Bilgi Sorgusu

1. Sürücü gidon butonuna basılı tutup "motor sıcaklığı" der.
2. ESP32-S3, ESP-SR ile komutu ~150ms içinde tanır (bağlantı gerekmez).
3. Bağlam veri yolundan güncel motor sıcaklığı okunur, sabit bir ses yanıtıyla (TTS veya kayıtlı ses) geri bildirilir.

## Senaryo 7 — Moto-MCP: Bağlantılı Ortamda Sohbet

1. Sürücü, telefonun hotspot'una bağlıyken "az önce ne kadar yattım" diye sorar.
2. Ses, Raspi üzerinden bulut STT/LLM servisine akıtılır; LLM, `get_recent_stats` aracını çağırır.
3. Moto-MCP, bağlam veri yolundan son 60 saniyenin maksimum yatış açısını döner (hesabı LLM yapmaz, hazır sonucu alır).
4. LLM bu sonucu doğal dile çevirip ~2 saniye içinde sesli yanıt üretir.
5. Bağlantı aniden kesilirse, sistem bu etkileşimi tamamlayamaz ama hiçbir güvenlik fonksiyonu bundan etkilenmez (bağımsız katmanlar).

## Senaryo 8 — HIL: Marş Anı Voltaj Çökmesi Regresyon Testi

1. Geliştirici, host'ta `PWR-01` senaryosunu başlatır.
2. Simülatör MCU'su, normal CAN trafiğini yayınlamaya başlar; DUT bağlanır ve senkronize olur.
3. Arıza/besleme kontrol MCU'su, beslemeyi 300ms içinde 12.6V'tan 9.0V'a düşürür.
4. Değerlendirici, DUT'un yeniden başlamadığını ve kayıt dosyasının bozulmadığını doğrular.
5. Sonuç, otomatik test raporuna eklenir; bu senaryo her commit'te tekrar koşturulabilir (regresyon).

## Senaryo 9 — Bootloader: Yeni Firmware Dağıtımı

1. Sunucuda yeni bir `moto-rt-core` firmware sürümü onaylanır.
2. Raspi, araç Wi-Fi menzilindeyken yeni imajı indirir.
3. UDS bootloader servisleri (0x34/0x36/0x37) üzerinden imaj, pasif bankaya (B) yazılır.
4. Bütünlük doğrulaması (CRC/imza) başarılıysa aktif banka B'ye geçirilir.
5. Güç kesintisi/hata durumunda sistem otomatik olarak A bankasına (önceki bilinen iyi sürüm) geri döner.

---

---

# 13. Faz 2 / Sonraki Aşama (Konsolide Liste)

Aşağıdaki kalemler tek bir "sonraki aşama" havuzunda toplanmıştır; çekirdek teslim taahhüdüne dahil değildir, tam şeffaflık için raporlanmaktadır.

## 13.1 Kalıcı Olarak Elenenler

| Kalem | Neden |
|---|---|
| Gerçek ASIL çipi (NXP S32K / Infineon AURIX) — hem safety MCU hem HIL simülatörü için | Maliyet (~10.000 TL) projeyle orantısız — kalıcı karar |
| İmmobilizer'ın ECU ile tam (OEM sınıfı) entegrasyonu | Üreticinin kapalı protokolünü (seed-key) çözmeyi gerektirir — ayrı bir tersine mühendislik projesi. Mevcut tasarım **caydırıcı sınıf** kabul edilir, OEM güvenlik seviyesi iddia edilmez |

## 13.2 Onaylanmış Yol Haritası

| Kalem | Ne getirir |
|---|---|
| Velocitas SDK | Linux node modüllerini standart "Vehicle App" kalıbına taşır |
| Eclipse Kanto | Konteyner tabanlı OTA/uygulama yönetimi |
| SOME/IP | MCU'lar arası köprüyü otomotiv orta katman standardına taşır |
| DoIP | UDS'i Ethernet üzerinden taşıma |
| Derin öğrenme tabanlı şerit takip | Zor sahne dayanıklılığı — düşük öncelik |
| Moto-MCP aktüatör-yazma yeteneği (onay kapılı) | LLM'in yalnızca kendi eklenen çevre aktüatörlerini (ışık, ısıtma, kamera) tetikleyebilmesi; motor/ECU kontrolüne asla genişletilmez |
| NFC kriptografik yükseltme (MIFARE DESFire) | Klonlanmaya dayanıklılık |
| Nextion → LVGL+ESP32/round display | Ana ekran zenginleştirmesi |
| Raspi 5 özel taşıyıcı/güç PCB'si | Fonksiyon değil, üretim standartlaştırma adımı |

## 13.3 Dürüst Not

Bu liste, projenin "her şeyi düşündük ama bilinçli olarak sınırladık" duruşunu yansıtır — eksiklik değil, kapsam disiplini. Her kalemin neden şimdi değil sonra yapılacağı yukarıda gerekçelendirilmiştir.

---

*Bu rapor, projenin donanım mimarisi ve repo yapısı karar dokümanının (v2.0) yeniden yapılandırılmış, hoca sunumuna uygun halidir. Teknik ayrıntıların tam ve değişmemiş hali, ekte sunulan orijinal dokümanda korunmaktadır.*
