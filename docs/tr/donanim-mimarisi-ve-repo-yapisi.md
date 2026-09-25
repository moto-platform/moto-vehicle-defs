# Donanım Mimarisi ve Repo Yapısı — Karar Dokümanı

**Proje:** Motosiklet gömülü teşhis, telemetri ve sürücü destek platformu
**Kapsam:** SDV-uyumlu araç donanım mimarisi, çip seçimleri, HIL tezgahı donanımı, repo yapısı
**Sürüm:** 1.0 — Eylül 2026

---

## 1. Mimari Felsefe

Modern SDV (yazılım tanımlı araç) mantığı: az sayıda güçlü işlem birimi + bir güvenlik izleyici + gerektiği kadar uç düğüm. Eski "her fonksiyona bir ECU" paradigmasından kaçınılır. Yeni fonksiyon = yeni donanım değil, mevcut birime yazılım modülü.

**Temel ilke:** Gerçek zamanlı/güvenlik kritik iş ile zengin/hesaplama yoğun iş aynı çipte olmaz.
- Gerçek zamanlı, deterministik iş → MCU (bare-metal/RTOS)
- Zengin, determinizm gerektirmeyen iş → Linux (Raspi)

---

## 2. Hedef Donanım Mimarisi (5 birim)

```
                ARAÇ CAN-FD HATTI
        ═════╤═════════╤═════════╤═══════
             │         │         │
        ┌────┴───┐ ┌───┴───┐ ┌──┴────┐
        │STM32H7 │ │STM32  │ │STM32  │
        │DOMAIN  │ │G4/F3  │ │G0/F0  │
        │(ana)   │ │SAFETY │ │I/O    │
        └──┬──┬──┘ └───────┘ └───┬───┘
           │  │SPI               │
      ┌────┴┐ └──┐          aktüatörler
      │ESP32│ ┌──┴───┐       (ışık, ısıtma,
      │S3   │ │Raspi5│        immobilizer, güç)
      │BLE/ │ │LINUX │
      │ML   │ │HPC   │
      └─────┘ └──────┘
```

| Birim | Çip | SDV rolü | Görev |
|---|---|---|---|
| Ana MCU | **STM32H7** (H743/H723) | Domain controller | CAN, telemetri, kayıt, füzyon, bakım takibi, koordinasyon |
| Bağlantı+ML | **ESP32-S3** | Yardımcı düğüm | Wi-Fi/BLE, sesli komut (TinyML), sunucu/telefon senkronu |
| Güvenlik | **STM32 G4/F3** (FPU'lu) | Safety monitor | Viraj güvenlik uyarısı, bağımsız izleme — izole |
| I/O | **STM32 G0/F0** | Zone/edge | Aktüatör (ışık, ısıtma), immobilizer, güç yönetimi |
| Linux | **Raspi 5** | HPC | Kamera, görüntü işleme, ağır ML çıkarımı, HMI, harita |

**Karar (kesinleşti):** Ana MCU **STM32H7**. ESP32-S3, ana MCU değil — sadece bağlantı+ML yardımcı düğümü. Ana MCU'da koşan işler (telemetri, kayıt, füzyon, UDS/ISO-TP/bootloader, XCP, viraj EKF kestirimi, bağlam sınıflandırma, sanal dinamometre hesabı, anomali çıkarımı) **STM32H7**'de; ESP32-S3'te sadece Wi-Fi/BLE senkron ve sesli komut (TinyML — vektör hızlandırıcı burada).

---

## 3. Standart Çip Seçimleri (işe göre)

| Rol | Standart çip | Neden bu sınıf |
|---|---|---|
| Domain (ana) | STM32H7 (Cortex-M7, 480 MHz, FPU, DSP, CAN-FD) | Otomotiv domain controller sınıfının öğrenilebilir muadili |
| Safety | STM32G4/F3 (FPU, deterministik) | Öğrenmesi kolay; gerçek muadili AURIX/S32K (ASIL) → Faz 2 |
| I/O/edge | STM32G0/F0 (ucuz, CAN'lı) | Edge düğüm basit olmalı, güçlü değil |
| Bağlantı+ML | ESP32-S3 (Wi-Fi/BLE, vektör hızlandırıcı) | RF + TinyML tek çipte, veri bölünmüyor |
| HPC | Raspi 5 | Gerçek muadili otomotiv SoC (S32G, NVIDIA); öğrenilebilir versiyon |

---

## 4. CAN Bağlantı Kuralları

- Her MCU **kendi transceiver'ıyla doğrudan** CAN hattına bağlı (aracı/köprü üzerinden değil) → modüller arası gecikme ortadan kalkar
- CAN yayın hattı: her mesajı herkes eşzamanlı ve deterministik alır ("alma önceliği" diye bir şey yok; öncelik sadece gönderme arbitrasyonunda)
- **Sadece bir birim yazar** (ana MCU, teşhis için), diğerleri dinler → hat çakışması önlenir
- Araçta **ekstra sonlandırma direnci konmaz** (araç zaten sonlandırılmış); tezgahta kendi hat kurulduğu için orada sonlandırılır
- Raspi CAN'a MCP2515+transceiver veya CAN HAT ile bağlanır (SocketCAN)

---

## 5. Gerçek Zamanlılık / Latency İlkesi

Latency fiziksel kanaldan gelir, repo/kod bölünmesinden değil.

| Kanal | Kimler arası | Gecikme | Determinizm |
|---|---|---|---|
| CAN | MCU ↔ araç | mikrosaniye | Yüksek |
| SPI/UART köprü | MCU ↔ MCU/Raspi | µs-ms | Orta-yüksek |
| BLE | telefon ↔ ESP | 30-100+ ms | Düşük |
| WiFi | Raspi/telefon ↔ sunucu | 10-100+ ms | Düşük |

**Altın kural:** Kritik iş asla yavaş/deterministik olmayan kanala bağlı olmaz.
- Mikrosaniye kritik (CAN uyarısı, güvenlik) → MCU + CAN, başka hiçbir şeye muhtaç değil
- Milisaniye toleranslı (HMI, kamera) → Raspi, köprü
- Gecikme umursamaz (ayar, rapor, geçmiş) → telefon BLE/WiFi

**Gevşek bağlama:** Her birim diğerleri olmadan temel işini yapar. Linux çökse, telefon gitse, köprü kopsa → kritik iş sürer. Raspi/telefon "zenginlik" ekler, "olmazsa olmaz" değil.

---

## 5b. Araç Alt Sistemleri

### 5b.0 Bağlam Sınıflandırma Katmanı (temel katman — diğer modelleri besler)

**Kritik konum:** Bağlam sınıflandırma ayrı/bağımsız bir özellik değil, sistemin geri kalanını koşullandıran **temel katman**. Diğer tüm ML modelleri (anomali, viraj, asistan, kayıt) bu katmandan beslenir. Bu yüzden ilk kurulacak ML modeli budur — hem etiketlemesi en kolay, hem diğerlerinin temeli.

**Neden merkezi:** "Yüksek devirde normal olan titreşim, rölantide anormal" — anomali/uyarı modelleri ancak bağlamı bilirse doğru çalışır. Bağlam, diğer modellere "şu an hangi koşuldayız" bilgisini verir; onlar da "bu koşulda ne normal/güvenli" diye bakar.

```
        IMU + CAN + GPS ham veri
               │
       [BAĞLAM SINIFLANDIRMA]  ← temel katman
               │
    ┌──────┬───┼────────┬──────────┐
    ▼      ▼   ▼        ▼          ▼
 [Anomali][Viraj][Asistan][Kayıt frek.][Uyarı eşiği]
  koşullu  eşik  davranış   ayarı       ayarı
```

**Alt problemler ve yöntemleri (literatürden):**

| Bağlam | Girdi | Yöntem | Ağırlık | Nereye |
|---|---|---|---|---|
| Yol tipi (şehir/kırsal/otoyol) | CAN (hız, gaz, vites) + istatistik | Klasik ML / eşik | Hafif (~%85) | ESP32-S3 |
| Yol yüzeyi (düz/bozuk/parke/toprak) | IMU titreşim | 1D-CNN (TinyML) | Orta (~%93) | ESP32-S3 |
| Sürüş olayı (hızlanma/fren/viraj) | IMU | Klasik ML / 1D-CNN | Hafif | ESP32-S3 |
| Gündüz/gece | Işık sensörü / kamera | Eşik / hafif model | Çok hafif | ESP32 |
| Hava (kuru/ıslak) | Yüzey titreşim + sıcaklık | Hafif model | Hafif | ESP32 |
| Trafik yoğunluğu | Hız değişkenliği + dur-kalk | İstatistik | Çok hafif | ESP32 |

**Donanım:** Çoğu mevcut donanımla (IMU + CAN + GPS) yapılır, Raspi şart değil — ESP32-S3 vektör hızlandırıcı yeterli. Gündüz/gece için opsiyonel ışık sensörü (küçük ek).

**Etiketleme avantajı:** Sürüşte "şimdi otoyoldayım / bozuk yol" demek kolay ve dürüst etiket — arıza verisindeki çıkmaz yok. İlk kurulacak ML modeli olmasının bir sebebi de bu.

**Genellenebilirlik uyarısı:** Model, eğitimde görmediği yol/koşulda test edilmeli. Tüm veriyi karıştırıp eğitmek "sahte yüksek doğruluk" verir; bilinmeyen bağlamda genelleme yeteneğini göstermez.

### 5b.0b Genişletilmiş Koşullandırıcı Bağlam Katmanı

Akademik literatür (context-aware ADAS) bu tür sistemleri üç kategoride ele alıyor — **sürücü, araç, çevre** — ve izole tek-özellik yaklaşımlarını (sadece yol veya sadece sürücü yükü) yetersiz buluyor; doğru tasarım üçünü bütün olarak ele alır. Bu üçlü çerçeveye göre, yol bağlamı dışında sistemi koşullandıran etkenler:

**A) Araç durumu**

| Koşullandırıcı | Ne etkiler | Kaynak | Model mi ölçüm mü |
|---|---|---|---|
| Kütle / yük (tek-çift kişi, bagaj) | Viraj limiti, fren mesafesi, tork ihtiyacı, sanal dinamometre | İvme-tork ilişkisi | Kestirim (EKF) |
| Termal durum (soğuk/çalışma sıcaklığı/aşırı ısınma) | Anomali eşiği (soğuk motor farklı titreşim/ses verir) | Sıcaklık sensörü | Ölçüm |
| Lastik basıncı / aşınma | Yuvarlanma direnci, titreşim imzası, viraj tutuş | TPMS veya dolaylı kestirim | Ölçüm/kestirim |
| Zincir/mekanik gerginlik | Titreşim imzası referansı | Bakım kaydı + titreşim | Ölçüm |
| Akü/besleme durumu | Sistem güvenilirliği, düşük güç moduna geçiş | INA226 | Ölçüm |

**B) Sürücü durumu**

| Koşullandırıcı | Ne etkiler | Kaynak | Model mi ölçüm mü |
|---|---|---|---|
| Sürücü kimliği | "Normal" tanımı kişiye özel olur (agresif/temkinli farklı referans) | Sürüş imzası | **Model** (sınıflandırma) |
| Yorgunluk / dikkat | Uyarı hassasiyeti, sesli asistan müdahale sıklığı | Sürüş düzensizliği paterni (IMU) | Model (K7'de zaten planlı) |
| Sürüş tarzı (agresif/sakin) | Uyarı eşiği kişiselleştirme, sigorta/skor | IMU + hız paterni | Model |

**C) Çevre durumu**

| Koşullandırıcı | Ne etkiler | Kaynak | Model mi ölçüm mü |
|---|---|---|---|
| Hava (kuru/ıslak/soğuk) | Sürtünme katsayısı (μ), viraj limiti, fren mesafesi | Yüzey titreşim + sıcaklık + nem | Hafif model/ölçüm |
| Gündüz/gece | Gösterge parlaklığı, LED hassasiyeti, kamera modu | Işık sensörü | Ölçüm/eşik |
| Trafik yoğunluğu | Sesli asistan müdahale sıklığı, uyarı önceliklendirme | Hız değişkenliği, dur-kalk sıklığı | İstatistik |
| Zamansal (sürüşün başı/ortası/sonu) | Yorgunluk, motor ısınma fazı, yakıt azalma | Sayaç + sensör | Ölçüm |

**Yalnızca gerçek model gerektirenler:** yol bağlamı (5b.0), sürücü kimliği, yorgunluk/dikkat, sürüş tarzı, hava (μ kestirimi). Geri kalanı ölçüm veya fizik kestirimi — ayrı ML modeli değil.

### 5b.0c Bağlam Veri Yolu Mimarisi

Tüm koşullandırıcılar tek tek modellere dağıtılmaz; ortak bir **bağlam veri yolu**nda toplanır, her model ihtiyacı olanı buradan okur. Yeni koşullandırıcı eklemek mevcut modelleri değiştirmez — sadece veri yoluna eklenir.

```
[Yol bağlamı model] ──┐
[Sürücü kimliği model]─┤
[Yorgunluk/tarz model]─┤
[Kütle/EKF kestirim] ──┼→ [BAĞLAM VERİ YOLU] → ilgili modeller okur
[Termal ölçüm] ─────────┤     (ortak paylaşılan durum)
[Lastik/mekanik] ───────┤
[Hava/μ] ───────────────┤
[Gündüz-gece/trafik] ───┘
        │                          │
        ▼                          ▼
  [Anomali tespiti]         [Viraj güvenlik]
  (koşullu normal)          (koşullu eşik)
        │                          │
        ▼                          ▼
  [Sesli asistan]           [Kayıt frekansı /
  (müdahale sıklığı)         uyarı hassasiyeti]
```

**Tez değeri:** "Bağlam-farkında (context-aware) sürücü destek mimarisi" — literatürde aktif bir araştırma alanı, izole tek-bağlam yaklaşımlarının ötesine geçen bütüncül tasarım. Motosiklete uygulanmış hali özgün bir katkı olur.

---

### 5b.1 Kör Nokta Uyarı Sistemi (BSM) — radar tabanlı

Refleks hızında, deterministik, bağımsız çalışması gerektiği için **MCU işi** (Raspi değil). Sensör ve LED arkada/yanda olduğu için ayrı bir I/O düğümü olarak kurulur — ana üniteyi yormaz, uzun kablo gerektirmez.

**Onaylanan kararlar:**
- **2 radar** (sol + sağ, tam yan kapsama)
- **24 GHz** mmWave radar (kör nokta için yeterli; 60/77 GHz hassasiyeti gereksiz, daha pahalı)
- **LED'ler sabah güneşinde de okunabilir olmalı** → yüksek parlaklıkta, güneş altında görünür tip; ayna içine gömülü
- **AI asistana bağlanmaz** — refleks hızı gerekir, LED doğru arayüz, kelime gecikme/gürültü ekler

**İşleyiş düğümü:** Elindeki **STM32F103** arka I/O düğümü olarak — 2 radarı okur, yaklaşma mantığını çalıştırır, ayna LED'lerini sürer, durumu CAN'a yayınlar. Kör nokta kararı tamamen F103'te verilir; CAN'a sadece sonuç yazılır → ana ünite/CAN çökse bile LED çalışır (bağımsız, güvenli).

**LED mantığı:**
- Yeşil: yan boş
- Kırmızı sabit: yanda araç var
- Kırmızı yanıp sönen: o yöne sinyal verilirken/şerit değiştirilirken araç yaklaşıyor (sinyal bilgisi CAN'dan veya ayrı girişten)

**Güneş altında okunurluk:** Yüksek parlaklıkta LED (yüksek mcd), ayna içinde gölgelenmiş/tünel yerleşim (doğrudan güneş vurmasın), gerekirse ortam ışığına göre otomatik parlaklık.

**İletişim:**
```
[24GHz Radar sol] ─┐
                   ├→ [STM32F103 arka düğüm] → [Ayna LED sol/sağ]
[24GHz Radar sağ] ─┘         │ CAN (durum yayını)
                       ══════╪══════ ARAÇ CAN HATTI
                             │
                    [Ana ünite]   [HMI/Nextion]
```
- Radar → F103: modül tipine göre analog/SPI/UART
- F103 → LED: GPIO veya WS2812 hattı
- F103 → CAN: kör nokta durumu (ana ünite loglar, HMI gösterebilir)
- Sinyal bilgisi: CAN'dan veya sinyal koluna bağlı giriş

**Donanım:**

| Parça | Rol | Durum | Tahmini (TL) |
|---|---|---|---|
| STM32F103 | Arka I/O düğümü | Elde var | 0 |
| 24 GHz radar ×2 | Sol+sağ yan tespit | Alınacak | 600-1600 |
| CAN transceiver | F103 → CAN | Alınacak | 80-150 |
| Yüksek parlaklık LED (ayna içi) | Görsel uyarı, güneşte okunur | Alınacak | 80-200 |
| Gidon aynası (LED gömülecek) | — | Zaten alınacak | — |
| Kablo, konnektör, muhafaza | Montaj | Alınacak | 150-300 |
| **Toplam** | | | **~910-2250** |

**Geliştirme yönü:** (1) radar tek başına test/tanıma → (2) eşik + yanlış alarm mantığı (sabit nesne vs yaklaşan araç ayrımı — sistemin kalbi, tez değeri) → (3) LED sürme → (4) CAN entegrasyonu → (5) sinyal entegrasyonu → (6) yol testi ve eşik ayarı.

**En zor kısım:** Yanlış alarm filtresi — radar bariyeri, park etmiş aracı, direği de görür. "Gerçekten yaklaşan araç" ayrımı hız+yön analizi ister.

---

### 5b.2 Viraj Güvenlik Uyarı Sistemi — üç katmanlı mimari (fizik + EKF + ML)

Motosikletlere özgü, güvenlik kritik fonksiyon. **Katmanlar farklı çiplerde** — bu bilinçli bir izolasyon kararı, tek çipte "yazılımsal izolasyon" değil.

**Üç katman — hangisi hangi çipte:**

```
Katman 1 — Deterministik karar (moto-safety-node, STM32 G4/F3, İZOLE)
   Kapalı form fizik: v_max = √(µ·g·R), tan(θ) = v²/(g·R)
   → Uyarı ve LED tetikleme BURADA. Ana MCU/Raspi çökse/gecikse bile bağımsız çalışır.
   → Girdisini (yatış açısı, µ, kütle) Katman 2'den CAN üzerinden alır.

Katman 2 — EKF kestirim (moto-rt-core, STM32H7 — bağlam veri yolunun parçası)
   µ (sürtünme), kütle, ağırlık merkezi yüksekliği, yatış açısı — fiziksel aralıklara KIRPILIR
   Aralık dışına çıkarsa → varsayılan güvenli değere düşülür
   → CAN üzerinden hem safety-node'a hem diğer tüketicilere (dyno, ekran LED halkası, şerit takip) yayınlanır — TEK hesaplama, çoklu kullanım

Katman 3 — ML uyarlama (moto-rt-core, bağlam modeliyle birlikte, isteğe bağlı)
   Sürücü profili, yol yüzeyi bağlamı (5b.0'dan) → eşiği ayarlar
   → Güvenlik TAVANINI asla gevşetemez, sadece muhafazakâr tarafta ince ayar yapar
```

**Açık karar (donanım netleşirken çözülecek):** `moto-safety-node`, H7'den gelen CAN verisi (yatış açısı, µ) gecikir/kesilirse ne yapmalı? Seçenekler: (a) kendi minimal IMU'suyla tamamen bağımsız çalışabilsin, (b) veri kesilince düşük-güven/muhafazakâr uyarı durumuna geçsin. Şimdilik karar verilmedi — `moto-safety-node` donanımı netleşince (Grup 7) çözülecek.

**Neden PINN/ağır ML değil, kapalı form + EKF:** Viraj limiti kapalı formda çözülüyor (analitik çözümü var), sinir ağı eğitmek gereksiz ve **açıklanamaz** — güvenlik fonksiyonunda "ağ öyle dedi" savunulabilir değil. Gri kutu (EKF ile parametre kestirimi) hem açıklanabilir hem test edilebilir: µ=0.62 çıktığında bunun fiziksel anlamı var, sinir ağı ağırlığının yok.

**Girdi verisi (Katman 2, moto-rt-core'da):** IMU (yatış açısı, açısal hız), GPS (viraj yarıçapı, hız), CAN (hız, ivme). Yatış açısı EKF çıktısı, bağlam veri yolu (5b.0c) üzerinden hem ekran LED halkasına (5b.4) hem şerit takip düzeltmesine (5b.5) hem safety-node'a paylaşılıyor.

**Çıktı — iki kanal:**
- **Round LED halka** (göstergenin iki yanı, 5b.4'te tanımlı, `moto-safety-node` veya I/O düğümünden sürülür): yeşil→sarı→kırmızı, anlık yatış durumu
- **Sesli/HMI uyarı** (eşik aşılırsa): ana ekran profilinde ("sportif" profilde görünür) + gerekirse sesli komut sisteminden (5b.6) sabit bir uyarı cümlesi

**Kalibrasyon ve saha testi:** Motor üstü çalışma planındaki T4 sınıfı testler (bölüm 7) — kapalı alan, kademeli hız artışı, **sınıra yaklaşma amaçlı değil, modelin tutarlılığını doğrulama amaçlı.** Gerçek devrilme/kayma sınırına ulaşılmaz.

**HIL doğrulaması:** `moto-hil-bench` üzerinde sabit yarıçap+değişken hız senaryolarıyla test edilir — beklenen uyarı noktası hesaplanıp gerçek tetiklenme noktasıyla karşılaştırılır (bkz. motor üstü plan, bölüm 8 test senaryoları).

**Donanım:** Ek donanım gerekmiyor — mevcut IMU/GPS/CAN altyapısı ve `moto-safety-node` çipi (zaten Grup 7'de listeli) yeterli. Bu modülün maliyeti donanımda değil, yazılımda (60-100 saat, kapsam listesinde zaten var).

---

### 5b.3 I/O Düğümü — İmmobilizer + Park Modu/Takip + Güç Kartı (birleşik)

Aynı fiziksel düğümde (`moto-io-node`, STM32 G0/F0) kör nokta ile birlikte koşar — SDV zone-controller mantığı: az sayıda düğüm, çok modül.

**İmmobilizer:**
- Müdahale noktası: **marş rölesi bobin devresi** (düşük akım, motor çalışırken işlevsiz — giden motoru asla kesemez). Ateşleme/yakıt pompası/ECU hattına KESİNLİKLE dokunulmaz.
- **Bistable (latching) röle** — park halinde enerji harcamaz, sadece konum değiştirirken kısa darbe çeker
- **Fail-safe:** varsayılan konum açık (sistem ölürse motor çalışabilir) + gizli mekanik bypass anahtarı + 10 sn karar zaman aşımında açık konuma geç
- **Yetkilendirme:** NFC (PN532) birincil (eldivenle okunur), PIN gidon üzerinden yedek. Parmak izi kullanılmaz (eldiven/nem ile güvenilmez)

**Park modu / hırsızlık takibi:**
- IMU wake-on-motion ile derin uyku → hareket algılanınca uyanma (hedef uyku akımı < 1 mA)
- Bildirim: Wi-Fi öncelikli (ev menzilinde, bedava) — bu düğümün kendi Wi-Fi'ı yoksa `moto-connectivity-node`'a (ESP32-S3) CAN üzerinden bildirir, o gönderir
- Opsiyonel genişletme: ayrı, gizli yerleşimli, kendi bataryalı GSM takip modülü (hat kesilse bile çalışır) — ayrı alt donanım, bu düğüme entegre değil
- Yanlış alarm filtresi: eşik + süre + hareket karakteri (3 katmanlı, kör nokta ile aynı disiplin)

**Güç kartı (ayrı fiziksel kart, subframe/tail yerleşimi, ünitelere ortak besleme sağlar):**
- Giriş: sigorta, ters polarite (P-MOSFET), TVS diyot, LC filtre
- Regülasyon: geniş girişli buck (6-40V→5V, 2-3A)
- **Süper kapasitör tamponu** — kontak kesilince 3-10 sn enerji, kayıt dosyasını güvenli kapatmaya yeter (HIL'deki PWR-02 senaryosuyla eşleşir)
- İzleme: INA226 (gerilim/akım/güç)
- Kontak anahtarlama: düşük gerilimde (<12.2V) düşük güç moduna geçiş

**Donanım (ek, kör nokta listesine ilaveten):**

| Parça | Rol | Tahmini (TL) |
|---|---|---|
| Bistable röle | Marş devresi kilitleme | 80-200 |
| NFC okuyucu (PN532) | Yetkilendirme | 100-250 |
| Süper kapasitör seti + dengeleme | Güvenli kapanma | 150-300 |
| Buck + koruma (TVS, ters polarite, sigorta) | Güç kartı | 300-550 |
| INA226 | Güç izleme | 100-300 |
| Gizli mekanik bypass anahtarı | Fail-safe | 50-100 |
| **Toplam (ek)** | | **~780-1700** |

**Referanslar (araştırma ile doğrulanmış):**
- **motogadget mo.lock NFC** — ticari ürün, senin tasarımınla aynı prensip: temassız NFC, röle üzerinden anahtarlama (40A'ya kadar), pilsiz pasif etiket, plastik panel arkasına gizlenebilir montaj. Custom motosiklet dünyasında yaygın — tasarımın pazarda kanıtlanmış bir mimariye dayandığını gösteriyor.
- **Hackster.io "Start Your [ANYTHING] with NFC"** — açık kaynak, doğrudan uyarlanabilir: bistable röle + 2 pinle aç/kapat kontrolü; MCU'nun marş anındaki ani voltaj düşüşünde beklenmedik kapanmaması için düzenleyici (regülatör) kullanma gerekçesi bizim güç kartı/süper kapasitör kararımızı bağımsız olarak doğruluyor.
- **Honda immobilizer patenti (US7855470)** — gerçek üretici mimarisi: güç hattı ve "motor durdurma rölesi" hattı AYRI tutulur (tek noktadan kesme yapılmaz), anahtarda pasif transponder. Bizim "bobin devresi ayrı, motor çalışırken işlevsiz" prensibiyle uyumlu.
- **Forum tartışması (ISO 26262 bağlamı)** — kendi immobilizer'ını ekleyen birine yöneltilen uyarı: ek arıza noktası riski, gerçek immobilizer'ların düşük akü voltajında (soğuk marş) bile çalışacak şekilde test edildiği vurgusu → düşük voltaj senaryosu HARA'ya eklenmeli.
- **Megamos çip kırılganlığı (Wikipedia, immobiliser)** — yaygın kullanılan bir immobilizer çipinin kriptografik olarak kırılabildiği kanıtlandı; basit UID okuyan NFC yerine kriptografik doğrulamalı etiket (örn. MIFARE DESFire) ileride değerlendirilebilir (Faz 2, klonlanmaya dayanıklılık).

**Süreç önerisi:** (1) marş rölesi bobin devresini teşhis et → (2) bistable röle masa üstü test → (3) güç kartı (düzenleyici+süper kapasitör) → (4) NFC okuma/doğrulama yazılımı → (5) fail-safe mantığı (varsayılan açık + bypass + zaman aşımı) → (6) HARA'ya düşük voltaj/ani kesinti/yanlış anahtar senaryolarını ekle.

---

### 5b.4 Ekran ve Görsel Uyarı Mimarisi

**Genel ilke — tek bilgi ekranı, çoklu ışık göstergesi:** İki ayrı fiziksel bilgi ekranı (ör. "mühendis görünümü" + "medya görünümü") yan yana koymak, sürüş sırasında hangi ekrana bakılacağına karar verme yükü ekliyor (bilişsel yük, tarama süresi artışı). Gerçek yarış göstergeleri (MoTeC, AIM) bu ayrımı **tek ekranda sayfa/profil** olarak çözüyor, fiziksel düğmeyle geçiş yapılıyor — dokunmatikle değil. Bu proje aynı deseni izler.

**Yenileme hızı netliği (araştırmayla doğrulandı):** Gerçek yarış göstergelerindeki "ekran gecikmesi" şikayetleri ekranın kendi yenileme hızından değil, **CAN veri yayın frekansından** kaynaklanıyor (100 Hz yayında algılanabilir gecikme yok, 20 Hz gösterim için yeterli; sorun düşük frekanslı OBD2 sorgulamada çıkıyor). Nextion'ın yenileme hızı yüzlerce Hz; darboğaz firmware'in seri porta ne sıklıkla veri bastığı. Mevcut Nextion donanımı bu açıdan yeterli, "standarda uymuyor" endişesi teknik olarak asılsız.

**Ekran/gösterge envanteri:**

| Konum | Donanım | Rol | Bağlantı | Not |
|---|---|---|---|---|
| Orijinal Honda round gösterge | — | Zorunlu bilgi (hız, yakıt, arıza lambası) | — | **Dokunulmaz** — yasal/garanti |
| Gidon-depo arası | **1× Nextion** (mevcut donanım) | Ana bilgi ekranı — profil bazlı sayfalar | UART → ana MCU (H7) | Kritik, Linux/Raspi çökse de çalışır |
| Göstergenin solu | Round **LED halka** (WS2812, dairesel) | Sol yatış açısı göstergesi | I/O düğümü veya ana MCU | Grafik ekran DEĞİL — bkz. gerekçe |
| Göstergenin sağı | Round **LED halka** (WS2812, dairesel) | Sağ yatış açısı göstergesi | I/O düğümü veya ana MCU | Aynı |
| Ayna uçları (sol/sağ) | LED (5b.1'de tanımlı) | Kör nokta uyarısı | I/O düğümü (STM32) | Ekran değil; yatış açısına göre telafi edilir (bkz. aşağı) |
| Ana ekran üstü/kenarı (opsiyonel) | RGB LED şerit (WS2812) | Shift-light (devir arttıkça yeşil→kırmızı) | Ana MCU | Aynı sürücü teknolojisi, ek maliyet düşük |
| Telefon | — | Uzak arayüz (ayarlar, geçmiş, rapor) | BLE/WiFi → `moto-connectivity-node` | Kritik işe karışmaz, gevşek bağlı |

**Profil bazlı sayfa sistemi:** Ayrı "mühendis görünümü" ve "medya görünümü" ekranı yerine, mevcut asistan profili mekanizması (bölüm 9, moto-telemetri) genişletilir:

| Profil | Ana ekranda gösterilen |
|---|---|
| Şehir | Hız, vites, yakıt, arıza lambası, kör nokta durumu |
| Tur | Menzil, tüketim, vites önerisi, yakıt uyarısı |
| Sportif ("mühendis görünümü") | Devir + shift-light, yatış açısı sayısal, tur/segment zamanı, sürüş skoru — ham/detaylı veri |
| Eko | Anlık/ortalama tüketim, gaz koçluğu |
| Medya | Spotify/Google Maps, sesli asistan geri bildirimi (şarkı adı, komut teyidi, yön oku) |

**Sayfa/profil geçişi:** Gidon üzerinde fiziksel düğme (yarış standardı — MoTeC/AIM 3 programlanabilir sayfa, düğmeyle geçiş). Dokunmatik/menü gezinme YOK — sürüş konforunu bozar.

**Yatış açısı göstergesi — neden LED halka, neden grafik ekran değil:**
- Ticari referans **KurvX** (X-Log): gidona takılan, ivmeölçerle yatış ölçen, eşik aşılınca **LED flaş** veren cihaz (grafik ekran kullanmıyor) — flaş sıklığı yatışla artıyor, güvensiz seviyede sürekli yanıyor.
- Patent referansı: yatış açısı göstergesi **renkli halka segmentleri** (yeşil→sarı→turuncu→koyu turuncu→kırmızı) olarak tasarlanmış, güvenlik seviyesine göre aydınlanıyor — "oOo" görsel konseptiyle birebir örtüşüyor.
- **İnsan faktörleri gerekçesi:** Virajda periferik görüş bir *rengi* anında algılar; bir *grafiği/sayıyı* okumak gözü sabitlemeyi ve yorumlamayı gerektirir. LED halka, tam grafikli round display'den daha hızlı okunur, daha ucuz, daha az güç çeker, daha basit yazılım (grafik motoru gerekmez).
- **Karar:** Pozisyon ve fonksiyon korunur (göstergenin iki yanında, "oOo" görünümü), uygulama **round WS2812 LED halka** olur — TFT/OLED round display değil.

**Kör nokta LED'inin yatış açısı telafisi (özgünlük noktası):** Araştırma, motosiklet kör nokta sistemlerinin genelde yatış açısını telafi etmediğini, bunun bilinen bir eksiklik olduğunu gösteriyor (yatışta aynadan görünen alan değişir). Sistem zaten EKF'den yatış açısını ürettiği için (bağlam veri yolu, 5b.0c), kör nokta mesafe eşiği yatış açısına göre hafifçe ayarlanabilir — rakip sistemlerin çoğunda olmayan bir fark, tez için özgünlük noktası.

**Kural:** Nextion doğrudan H7'ye bağlı, Linux/Raspi çökse de çalışır. LED halkalar ve shift-light basit sürücü mantığı, ana MCU veya I/O düğümünden — ağır işlem gerektirmez. Telefon hiçbir kritik işe karışmaz.

**Faz 2 notu (yükseltme referansı, şimdi yapılmayacak):** Nextion yerine LVGL+ESP32/round display'e geçiş istenirse açık kaynak referanslar: `dev-ale/moto2000` (ESP32-S3 AMOLED round, BLE, telefon-taraflı mantık, ~₺1250-1450 BOM, IP67 PG7 kablo rakoru + silikon O-ring montaj), `emdzej/opencluster` (ESP32+LVGL, çoklu ekran CAN üzerinden, masaüstü simülatörü), `barcu00/DIY-dash-5` (ESP32-S3, tablo tabanlı CAN çözücü, UI'dan izole mimari), `hpeyerl/evj55-dashboard` (büyük panel → Raspi/Linux framebuffer LVGL, ESP32'nin yetersiz kaldığı sınır).

**IP67 montaj notu:** Sızdırmazlıkta O-ring, karmaşık yüz-yüze contalardan daha güvenilir; düşük sertlikte silikon conta yüzey düzensizliklerine uyum sağlar; muhafaza gövdesi rijit olmalı (esneyen gövde contayı bükip sızdırabilir). Ticari motosiklet ekranları standart olarak IP67 + 700-1000 nit parlaklık + eldivenle çalışan kapasitif dokunmatik kullanıyor — Nextion muhafazası bu üç kritere göre 3D-baskı tasarlanmalı.

---

### 5b.5 Şerit Takip / Şerit İhlali Uyarı Sistemi (LDW) — kamera + IMU tabanlı

Raspi 5 üzerinde koşar (görüntü işleme MCU işi değil). Motosiklete özgü kritik fark: **yatış açısı kamera görüntüsünü döndürür**, bu yüzden otomobil LDW algoritması doğrudan kopyalanamaz — IMU ile düzeltme şart.

**Literatürden kilit bulgu:** Motosikletin kendi yönünü tahmin etmek için, sürüş paterni sınıflandırmasından ziyade **doğrudan yatış açısı ölçümü** daha iyi sonuç veriyor. Bu senin avantajın — viraj güvenlik modülü için zaten EKF ile yatış açısı üretiyorsun (bağlam veri yolu, 5b.0c); aynı veri burada da kullanılır, ayrı hesaplama gerekmez.

**Klasik açık kaynak pipeline (OpenCV, derin öğrenme gerekmez — Raspi 5'te rahat koşar):**

1. Kamera kalibrasyonu — lens distorsiyonu düzeltme (satranç tahtası deseniyle)
2. Renk + gradyan eşikleme — HLS renk uzayı (S kanalı, farklı aydınlatmada sağlam) + Sobel filtre
3. Perspektif dönüşümü — kuş bakışı görünüm (şerit çizgileri paralel hale gelir, hesap azalır)
4. Şerit piksel takibi + eğri uydurma
5. Araç/şerit merkez pozisyonu hesabı

Referans (açık kaynak, doğrudan incelenebilir): JunshengFu/driving-lane-departure-warning, RACRAMES/Lane-Departure-Warning-LDW-System (GitHub, OpenCV tabanlı, adım adım bu pipeline'ı uyguluyor).

**Motosikletlere özgü düzeltme (patentli yöntemin mantığı, açık kaynak uyarlanabilir):**

1. Kamera optik ekseni ile şerit çizgisi arası mesafe ölçülür
2. Mesafe, **yaw/yatış açısına göre düzeltilir** (dönüş/yatış sırasında görüntü kayması telafi edilir)
3. Düzeltilmiş mesafe, ön tekerlekten şerit çizgisine gerçek mesafeye çevrilir
4. Eşik aşılırsa uyarı (örnek pratikte: birkaç cm eşik, birkaç saniye sonra otomatik kapanma)

**Sinyal mantığı:** Kör nokta sistemiyle tutarlı — sinyal verilirken (bilinçli şerit değişimi) uyarı bastırılır. Sinyal bilgisi CAN'dan okunur, ayrı entegrasyon gerekmez.

**Geniş açı lens notu:** Ucuz/geniş açılı kamera distorsiyon sorunu büyütür (literatürde ayrıca ele alınan bir problem — vanishing point tahmini + lens karakteristiğine göre düzeltme gerektirir). Mümkünse standart açılı kamera tercih edilmeli; geniş açı kullanılırsa ekstra distorsiyon düzeltme adımı eklenmeli.

**Motosiklete özgü eşik farkı:** Motosiklet doğal sürüşte otomobilden daha fazla yanal hareket eder (denge/sürüş davranışı) — eşik otomobil LDW'sinden daha gevşek tutulmalı, aksi halde yanlış alarm oranı yüksek olur.

**Mimari:**
```
[Raspi 5 Kamera] → distorsiyon düzeltme → renk/gradyan eşikleme
                                              → kuş bakışı dönüşüm
                                              → şerit tespiti + eğri uydurma
                                                        │
[Bağlam veri yolu: EKF yatış/yaw açısı] ──────────────→ [Düzeltme]
                                                        │
                                              [Şerit-merkez mesafesi]
                                                        │
                                    [Eşik + sinyal durumu] ← CAN'dan sinyal bilgisi
                                                        │
                                              [Uyarı: HMI/LED/ses]
```

Not: Yatış açısı bağlam veri yolundan (5b.0c) okunur — viraj güvenlik modülüyle aynı kaynağı paylaşır, ayrı ada değil.

**Donanım:**

| Parça | Rol | Durum | Not |
|---|---|---|---|
| Raspi 5 | İşlem (OpenCV pipeline) | Zaten planda | Ekstra maliyet yok |
| Raspi Kamera Modülü | Görüntü | Alınacak | Standart açı tercih; geniş açıysa distorsiyon düzeltme ek iş |
| Kamera montajı (ön, titreşim izole) | Sabit açı | Alınacak | Titreşim → yanlış şerit tespiti riski |

**Geliştirme sırası:** (1) OpenCV klasik pipeline'ı referans projelerden uyarlayıp statik görüntüde çalıştır → (2) kuş bakışı + eğri uydurmayı motosiklet kamera açısına kalibre et → (3) IMU yatış/yaw düzeltmesini entegre et → (4) eşik + sinyal mantığı → (5) motosiklete özgü yanlış alarm eşiğini yol testiyle ayarla.

**Referans/açık kaynak listesi:** JunshengFu/driving-lane-departure-warning (GitHub), RACRAMES/Lane-Departure-Warning-LDW-System (GitHub), Bosch LDW teknik tanımı (sistem davranışı referansı — ~60-100m algılama, sinyal bastırma mantığı).

**Yöntem kararı — klasik CV vs derin öğrenme (araştırmayla doğrulandı):**

| | Klasik CV (SEÇİLEN) | Derin öğrenme (UFLD tarzı, Faz 2 notu) |
|---|---|---|
| Eğitim verisi | **Gerekmiyor** — algoritmik | Gerekli (fine-tuning) |
| Hız | Raspi 5 CPU'sunda rahat | GPU'da 3-6ms; Raspi CPU'sunda hızlandırıcı olmadan sınırda |
| Zor sahne dayanıklılığı | Orta (gölge, silik çizgi, gece zorlanır) | Yüksek (CULane gece/kalabalık/çizgisiz senaryoları kapsıyor) |
| Domain gap | Yok — öğrenmiyor | Var — TuSimple/CULane otomobil-kaputu-sabit-dik-açı verisiyle eğitilmiş; yatan motosiklet kamerasına doğrudan aktarılmaz (CWRU rulman verisi / motor sesi analizindeki aynı domain gap problemiyle aynı kategori) |

**Karar:** Klasik CV yöntemi kullanılır. Gerekçe: sıfır veri toplama yükü (proje veri bütçesi zaten bağlam sınıflandırma, arıza tespiti, sesli komut arasında paylaşılmış durumda), Raspi 5 CPU'sunda hızlandırıcısız çalışır, açık kaynak referansları doğrudan uyarlanabilir. Derin öğrenme (UFLD, Fast-CenLaneNet) daha yüksek dayanıklılık isteniyorsa Faz 2'de değerlendirilir — ama kendi motosiklet verisiyle ince ayar gerektirir (~5-10 saat çeşitli yol/hava/gece verisi + etiketleme).

**Veri toplama gerekliliği: YOK.** Bu alt sistem, projenin diğer ML modüllerinden (bağlam sınıflandırma, arıza tespiti, sesli komut) farklı olarak eğitim verisi gerektirmiyor — algoritma hesaplıyor, öğrenmiyor.

---

### 5b.6 Sesli Komut Sistemi (offline, kırsal-dayanıklı)

**Karar:** Espressif'in resmi **ESP-SR** çerçevesi kullanılır — kendi model eğitimi gerekmez.

| Bileşen | Teknoloji | Not |
|---|---|---|
| Tetikleme | Bas-konuş (gidon butonu) | Wake word değil — rüzgar gürültüsünde yanlış tetiklenmeyi baştan eler |
| Komut tanıma | **ESP-SR MultiNet** | 300 kelimeye kadar, **yeniden eğitim gerektirmez**, hazır |
| Ses ön işleme | ESP-SR Audio Front-end (AEC, VAD, gürültü bastırma) | Rüzgar/motor gürültüsüne karşı ilk savunma |
| Donanım | I2S mikrofon (kask içi/interkom) | — |
| Konum | **ESP32-S3** (`moto-connectivity-node`) | Vektör hızlandırıcı burada; Raspi'ye taşımak gereksiz köprü gecikmesi ekler |
| Referans | ESP-SR (espressif/esp-sr, GitHub) — WakeNet (~80ms, <%2 yanlış pozitif), MultiNet | Resmi Espressif çerçevesi |

**Gecikme:** ~100-200ms, tamamen offline, bağlantı gerektirmez — kırsalda çalışır.

**Not (TinyML iddiası):** Hazır ESP-SR kullanımı teknik olarak TinyML'dir ama model eğitilmemiş, entegre edilmiştir. Projenin "kendi eğitilmiş model" TinyML iddiası bağlam sınıflandırma modelinde (5b.0) karşılanır; burada hız/güvenilirlik önceliklidir.

---

### 5b.7 Moto-MCP — Bağlam Temelli Sürüş İçi LLM Asistanı

**Mimari — iki katman, iki gecikme profili:**

```
SÜRÜŞ SIRASINDA (bağlantı VARSA)
  Mikrofon → Raspi 5 (VAD) → ~internet (telefon hotspot)
      → Bulut Realtime API (STT+LLM+TTS akış) → ~2 sn → kask hoparlörü
  LLM, cevap üretirken moto-mcp araçlarını (tool call) çağırır

SÜRÜŞ SIRASINDA (bağlantı YOKSA — kırsal fallback)
  → 5b.6 kapalı sözlük sistemi devreye girer (offline, ~100-200ms)

EV/SONRASI (demo, bonus)
  Claude Desktop / herhangi bir MCP istemcisi → moto-mcp (uzaktan) 
      → "dünkü sürüşüm nasıldı" tarzı sorgular
```

**Temel ilke (OVMS projesinin uyarısıyla doğrulanmış):** LLM kendi matematiğini yapmaz, sadece **hazır hesaplanmış sonucu** doğal dile çevirir. Ham sayısal seriyi yorumlatmak güvenilmez ve LLM bunu kullanıcıya söylemeden yanlış üretebilir (OVMS projesi: "mevcut AI araçları sınırlamalarını bildirmeden, kendinden emin ama yanlış sonuç üretiyor").

**Araç (tool) listesi — mevcut alt sistemlerin doğal API'si:**

| Araç | Ne döner | Kaynak |
|---|---|---|
| `get_live_snapshot()` | Anlık hız, devir, motor sıcaklığı, yatış açısı, lastik sıcaklığı, gerilim | Bağlam veri yolu (5b.0c) |
| `get_recent_stats(pencere_sn)` | Son N saniyede maks/ort/trend | Halka arabellek |
| `get_event_log(adet)` | Son olaylar (anomali, sert yatış/fren, kör nokta, mod değişimi) | Olay günlüğü |
| `get_anomaly_status()` | Anomali skoru/sınıflandırma | Anomali modeli çıktısı (ayrı model değil — mevcut çıktının tüketicisi) |
| `get_maintenance_status()` | Yük-saati bazlı bakım durumu | Bakım takibi modülü |
| `query_ride_history(tarih_araligi)` | Geçmiş sürüş özetleri | `moto-server` (tool call, ekstra gecikme) |

**Bağlama şekli:** MVP'de yerel köprü — Raspi'deki `moto-linux-node`, `moto-mcp`'yi yerel (localhost) çağırır, sonucu bulut LLM'e bağlam olarak ekler; bulut asla doğrudan araca bağlanmaz. Ev demo modunda `moto-mcp` gerçek bir MCP sunucusu olarak (kimlik doğrulamalı) dışarı açılabilir — Claude Desktop gibi istemcilerle "dünkü sürüşümü anlat" sorgulanabilir.

**Mahremiyet ve şifreleme (güncellendi — tartışma sonucu):**

- **Genel bağlam paketi:** Ham GPS koordinatı bulut LLM'e/bağlam paketine gönderilmez; bunun yerine Raspi'de yerel olarak hesaplanmış, geri döndürülemez bir özet gider (örn. "kırsal bölge", "evden 12 km", "bilinen güzergah") — çevrimdışı harita önbelleğinin (5b.8) doğal uzantısı, ekstra iş değil.
- **Koordinat gerektiren özel çağrılar (navigasyon vb.):** Ham GPS SADECE o tool call'a özel gönderilir, genel bağlam paketine karışmaz. "Bugün nasıl sürdüm" gibi konum gerektirmeyen sorularda GPS hiç LLM'e gitmez.
- **Şifreleme — doğru yerde kullanılır, genel bağlam iletiminde değil:** HTTPS/TLS zaten her bulut API çağrısında var (ek şey gerekmez). Şifrelemenin gerçek katma değeri iki yerde: (1) `moto-mcp`'nin "ev demo" dışarı-açık modu — TLS + kimlik doğrulama (API anahtarı/token) zorunlu, tüm telemetriyi (sadece GPS değil) korur; (2) `moto-server`'da saklanan geçmiş GPS verisi — saklama şifrelemesi (disk/DB düzeyi), fiziksel erişimde konum geçmişinin kolayca okunmasını engeller.
- **Not:** Bu karar ileride (gerçek kullanım/tehdit modeli netleşince) değiştirilebilir — şimdilik varsayılan bu.

**Ek sensörler (bu alt sistem + anomali modeli için çekirdeğe eklendi):**

| Sensör | Amaç | Maliyet |
|---|---|---|
| IR lastik/fren sıcaklık sensörü | Gerçek ölçüm (tahmine gerek kalmaz) | 150-350 TL |
| EGT (egzoz sıcaklığı) | Motor sağlığı, yanma kalitesi | 300-600 TL |

**Repo:** `moto-mcp` — **bağımsız açık kaynak repo** (bkz. bölüm 8, istisna gerekçesi). Aynı Raspi 5'te koşsa da paylaşım/vitrin amacıyla ayrı.

**Referanslar (araştırmayla doğrulanmış):**
- **Mater** (Vasu1712/mater) — Redis "sıcak yol" (anlık) + TimescaleDB "soğuk yol" (geçmiş) ayrımı, tek MCP araç katmanı, iki LLM ajanı (sürücü sesli / sahip sohbet). Bu projenin anlık/geçmiş veri ayrımının doğrudan referansı.
- **car-ai** (iqureshi123/car-ai) — Raspi 5 (GPU'suz) kısıtı altında tool-calling destekleyen en küçük modelin llama3.2:3b (Q4_K_M, ~2GB) olduğunu gösteriyor; "telemetri = konum verisi, araçtan çıkmamalı" mahremiyet gerekçesi.
- **OVMS** (openvehicles/Open-Vehicle-Monitoring-System-3) — LLM'lerin muhakeme değil örüntü öğrendiği, mevcut AI araçlarının sınırlamalarını bildirmeden yanlış-ama-kendinden-emin sonuç ürettiği uyarısı → "LLM kendi matematiğini yapmasın" kuralının gerekçesi.
- **Connected-Car-AI-Support-Agent** — aktüatör/OTA işlemlerinden önce operatör onay kapısı deseni (ISO 26262 uyumu) — bu proje salt okunur olduğu için şimdilik uygulanmıyor, ileride aktüatör eklenirse referans.

**Faz 2 — Aktüatör-LLM Bağlantısı (yazma yeteneği, onay kapılı):** Şu an tüm Moto-MCP araçları salt okunur. Faz 2'de, LLM'e **sadece kendi eklediğimiz çevre aktüatörlerini** (ışık, ısıtmalı kumanda, kamera tetikleme — F17 sınıfı, motor kontrolüne dokunmayan) tetikleme yetkisi verilebilir. Motor/ECU kontrolüne asla genişletilmez. Her yazma çağrısı, Connected-Car-AI-Support-Agent deseninde olduğu gibi bir **operatör onay kapısından** geçer (sesli/HMI onayı olmadan aktüatör tetiklenmez) — LLM'in doğrudan bir şeyi değiştirmesi, okuma yapmasından kategorik olarak farklı bir risk sınıfıdır ve bu ayrım korunur.

---

### 5b.8 Linux Node — SDV Katmanı ve Genişletilmiş Roller

**Amaç:** `moto-linux-node`'u kendi icat edilmiş bir mimariden, Eclipse SDV ekosisteminin (Bosch/BMW/Microsoft ortak geliştirmesi) standart yapısına taşımak.

**Katmanlı mimari:**

| Katman | Teknoloji | Rol |
|---|---|---|
| Sinyal aracısı | **Kuksa Databroker** (Docker container) | Tek gerçek kaynak, VSS semantik model — hiçbir uygulama CAN'a doğrudan dokunmaz |
| CAN köprüsü | Kendi yazılan servis | CAN → VSS çevirisi (`moto-vehicle-defs` şemasını kullanır) |
| Uygulama çerçevesi | Velocitas SDK (Faz 2) | Her fonksiyon (şerit takip, moto-mcp, HMI) bir "Vehicle App" |
| Haberleşme | gRPC (yerel) + MQTT (bulut/`moto-server`) | Standart protokoller |
| Konteyner/OTA yönetimi | Eclipse Kanto (Faz 2) | MVP'de basit process, olgunlukla konteynere geçiş |

**Referans donanım:** Eclipse Kuksa CANOPi — Raspi CM4 tabanlı, 2× CAN-FD arayüzü, OBD'den beslenebilen resmi SDV prototipleme kartı. Senin MCP2515/CAN HAT kurulumunun profesyonel/otomotiv-sınıfı karşılığı.

**Fleet Management referansı:** Eclipse'in resmi uçtan-uca demosu — Databroker → Zenoh → bulutta InfluxDB+Grafana. `moto-server` bu deseni izler.

**Kapasite notu (Raspi 5 8GB, kaba bütçe):** Şerit takip (orta), Kuksa+CAN köprü (düşük), zengin akustik anomali (**en büyük yeni yük** — periyodik pencere analiziyle koşturulmalı, sürekli tam hızda değil), video encode (donanım hızlandırıcılı, düşük), HMI (düşük-orta), Kanto (orta ek yük — **MVP'de ertelenir**). Bu ayarlarla toplam yük Raspi 5'in kapasitesi içinde kalır.

**Genişletilmiş rol listesi:**

| Rol | Açıklama | Öncelik |
|---|---|---|
| Çevrimdışı harita önbelleği | OSM ekstraktı yerel, kırsalda navigasyon internetsiz çalışır | Yüksek — kırsal önceliğiyle uyumlu |
| Sürüş videosu + telemetri bindirme | Kamera + telemetriyi birleştirip anomali/kör nokta anlarının klipleri | Yüksek — tez/portföy değeri yüksek, düşük ek maliyet |
| Çoklu sürüş özet raporu | Haftalık/aylık km, tüketim, skor — mevcut veriden, sıfır yeni veri | Yüksek |
| MCU firmware dağıtım merkezi | `moto-server`'dan indirip CAN/UDS bootloader ile MCU'lara dağıtma | Orta — bootloader çalışmasının doğal Linux-tarafı |
| Düğüm sağlık paneli | Tüm MCU'ların heartbeat/durumu tek ekranda | Orta — HIL test raporunun araç-üstü canlı karşılığı |
| Veri ön işleme hattı | Ham veriyi araçtayken pencereleyip özellik çıkarımı, sunucu yükünü azaltır | Orta |
| Olay tabanlı "kara kutu" kaydedici | Anomali/kaza öncesi-sonrası birkaç saniyeyi tüm modalitelerde tam çözünürlükte ayrı saklama | Orta — tez için güçlü, az yer kaplar |
| Hafif yerel zaman serisi DB (SQLite/DuckDB) | Son birkaç günün verisi yerel, tam InfluxDB yerine | Orta |
| XCP/A2L host aracı | Kalibrasyon arayüzü (F18) için basit host/log görüntüleyici | Düşük — F18 implemente edilirse |
| NTP zaman sunucusu | GPS zamanını diğer MCU'lara dağıtır | Düşük — zaman senkronizasyonu açık kararını çözer |
| Kenar analitiği arabelleği | Bağlantı zayıfken özet gönder, tam veri sonra tamamlanır | Düşük — kısmi/koşullu çözüm |
| Uzaktan geliştirme erişimi | SSH üzerinden log/durum kontrolü | Düşük — geliştirici konforu |
| DoIP ağ geçidi | UDS'i Ethernet üzerinden taşıma (yeni nesil teşhis protokolü) | **Faz 2** — kırsal öncelikle doğrudan ilgisiz, CV/mülakat notu |

**CI/CD ile OTA ayrımı (netleştirme):** CI/CD'nin kendisi (derleme, otomatik test, HIL regresyon) **i7 masaüstünde** (HIL host, bölüm 9b) — Raspi'ye taşınmaz. OTA **dağıtımı** (yeni firmware indirip UDS bootloader ile MCU'lara yazma) Raspi'de kalır ama Kanto olmadan, basit bir Linux servisiyle — hafif iş, konteyner orkestrasyonu gerekmez.

**Donanım envanteri (düzeltilmiş):** Kullanıcının elinde **Raspi 5 8GB** (araçta, ana Linux node) ve **Raspi 3B+** (1GB RAM, zayıf — Pi 4 8GB satılık listeden alınmayacak, bu bir önceki karıştırmaydı). 3B+'a araçta ikinci tam Linux düğümü rolü verilmez (CV/ML için yetersiz, HIL host zaten i7). Zorla bir rol uydurulmaz; iki hafif seçenek: (a) HIL kontrol panelinin ekran/arayüz ucu (i7 ağır işi yapar, 3B+ sadece paneli gösterir), (b) şimdilik atanmamış yedek — ileride basit bir ihtiyaç (ikinci NTP kaynağı, log toplayıcı) çıkarsa devreye girer.

**Raspi 5 güç, ısı ve yerleşim (MCU'lardan ayrı ele alınmalı):**

- **Ayrı güç hattı zorunlu.** Raspi 5 boşta 3-5W, yükte (kamera+CV+ses modeli) 8-15W çeker — MCU güç bütçesinin (5b.3, 2-3A) çok üstünde. Raspi kendi regülatörünü ve hattını alır, MCU'ların (H7, safety, I/O) paylaştığı raydan **izole**. Gerekçe: Raspi'nin ani yük dalgalanması ortak hatta gerilim düşüşü yaratabilir, bu da safety MCU'yu resetleyebilir — güvenlik kritik düğüm, Raspi'nin güç dalgalanmasından etkilenmemeli.
- **Mekanik/elektriksel besleme kaynağı:** Araç aküsü/alternatöründen, kendi regülatörüyle (ayrı bir mekanik jeneratör değil) — MCU'larla aynı kaynak, ayrı devre. Alternatör kapasitesinin ek yükü (birkaç watt) karşıladığı doğrulanmalı (servis el kitabından, bkz. bölüm 5b.3).
- **Isı yönetimi — IP67 kutuda gözden kaçan risk:** Sızdırmaz kutu ısıyı da hapseder; yük altında (kamera+CV+ses aynı anda) Raspi 5 ısınıp sıcak havada performans sınırlamasına (throttling) girebilir. Çözüm: pasif soğutucu (heatsink) + su geçirmez ama nefes alan membran (basınç dengeleme valfi, IP67 elektronik kutularında yaygın) veya büyük yüzeyli pasif soğutma bloğu. Güç kartı tasarımıyla birlikte düşünülmeli, sonradan eklemesi zor.
- **Şasi yerleşimi:** MCU güç kartından daha büyük hacim gerektirir. Öneriler: sele altı (yeterli boşluk varsa, ısı kaynaklarından uzak) veya yan panel/kaporta içi boşluk (CL250'nin scrambler gövdesinde sınırlı olabilir, kontrol edilmeli). Motor bloğu ve egzozdan uzak tutulması şart.
- **Yeni PCB zorluğu (kabul edilen risk):** Raspi 5 için ayrı güç/taşıyıcı kartı (izole regülatör, koruma, ısı yönetimi) gerçek bir tasarım-üret-test döngüsü. İlk turda delikli plaket/hazır güç modülleriyle basit tutulur, PCB tasarım oturunca basılır (bkz. bölüm 6, modül/çip kademelendirmesi).

---

### 5b.9 Anomali Tespit Modeli — Birleşik Model Mimarisi (Raspi) + ESP Güvenlik Ağı

**Veri şeması:**

| Modalite | Sinyal | Örnekleme | Ne yakalar |
|---|---|---|---|
| CAN | Devir, TPS, motor sıcaklığı, MAP, yakıt trim, akü gerilimi, tekerlek hızı (varsa) | 1-20 Hz | Yavaş arızalar (filtre, sızıntı, sensör kayması) |
| IMU (titreşim) | 3 eksen ivme, yüksek frekans | 1000+ Hz | Mekanik: dengesizlik, gevşeklik, ateşleme düzensizliği |
| Akustik | Mikrofon → MFCC/spektral özellik | Ses karesi bazlı | Genel motor sağlığı, yanma kalitesi |
| Termal | Motor sıcaklığı, EGT, ortam | 0.1-1 Hz | Yanma kalitesi, aşırı ısınma |
| Bağlam (koşullandırıcı) | Bağlam veri yolundan: yük, hava, sürüş modu | Olay bazlı | "Bu koşulda ne normal" |

**Füzyon kararı — tek birleşik model (Raspi'de) + ESP'de kural tabanlı güvenlik ağı:**

**Karar değişti (tartışma sonucu):** İlk kararımız geç füzyondu (ayrı skorlar, ayrı yerlerde). Tartışma sonrası **erken füzyona** geçildi — gerekçe: Kuksa Databroker zaten CAN+IMU verisini Raspi'ye taşıyor (VSS köprüsü), bu veriyi zaten oradayken tek birleşik modelde değerlendirmek **çapraz-modalite korelasyonu** yakalayabilir (ayrı ayrı skorların kaçırabileceği, "iki sinyal birlikte anlamlı ama tek başına eşik aşmayan" durumlar) ve geliştirme/senkronizasyon açısından da daha basit.

```
Raspi 5 (tek birleşik anomali modeli):
   [CAN + Titreşim + Akustik + Termal + Bağlam] → birleşik model (erken füzyon)
   → tek anomali skoru/sınıflandırma

ESP32-S3 (H7) — minimum güvenlik ağı, ML DEĞİL, birkaç sabit kural:
   Motor sıcaklığı eşiği, devir mantıksız sıçrama, akü gerilimi eşiği vb.
   → Raspi çökse/yeniden başlasa bile SIFIRA düşmeyen minimum kontrol
```

Bu, "tek modelde geliştirme kolaylığı + korelasyon yakalama" (Raspi) ile "hiçbir zaman tamamen sessiz kalmama" (ESP kural tabanlı yedek, ayrı ML modeli değil — ekstra geliştirme yükü yok) ikisini birden veriyor.

**Etiketleme:** Motor üstü çalışma planındaki arıza enjeksiyon seansları (buji, hava filtresi, zincir, lastik basıncı) sırasında CAN+IMU+ses aynı anda kaydedilir — tek seansta üç modalite birden etiketlenir, ekstra kayıt turu gerekmez.

**Veri yeterliliği — ek sensör önerileri:**

| Eksik/geliştirme noktası | Öneri | Maliyet | Öncelik |
|---|---|---|---|
| Titreşim sensörü konumu | Mevcut IMU (sele altı) yatış/EKF için; motor titreşim imzası (piston, supap, rulman) motor bloğuna yakın en temiz alınır. **Ayrı, küçük, motor bloğuna monte ivmeölçer** eklenmeli (mevcut IMU'dan bağımsız, sadece anomali için) | 150-250 TL | **Yüksek — somut iyileştirme** |
| Yağ basıncı/sıcaklığı | CAN'da muhtemelen yok (basit motor); yağlama kaynaklı arızalar için gerçek sinyal | 300-600 TL, montaj zor olabilir | Opsiyonel |
| CAN, akü/güç, termal, bağlam | Zaten yeterli | — | — |

**Metodolojik sınırlar ve doğrulama protokolü (karara bağlandı):**

- **Hedef:** Hem (A) ikili anomali tespiti ("normalden sapma var mı") hem (B) arıza türü sınıflandırma birlikte hedefleniyor. (B) için sınıf başına dengeli, yeterli veri şart — mevcut 30-40 dk/arıza seans planı (A) için güçlü, (B) için sınırlı; (B)'nin doğruluğu buna göre daha düşük çıkabilir ve tezde bu ayrım net raporlanmalı.
- **Modalite kör noktası riski:** Planlı arıza senaryolarının (buji, vakum sızıntısı, hava filtresi, zincir, lastik basıncı, rölanti) çoğu CAN sinyallerinde (yakıt trim, devir kararsızlığı, MAP) zaten net iz bırakıyor. Bu, titreşim/akustik katmanının (motor bloğu ivmeölçeri, mikrofon) hiç doğrulanmadan yüksek doğruluk görünmesi riski yaratır (doğruluk CAN'dan gelip pahalı sensör altyapısı test edilmemiş olabilir). **Çözüm:** En az bir-iki arıza senaryosu **öncelikle titreşimde görünen, CAN'da zayıf iz bırakan** türden olmalı (örn. kontrollü gevşetilmiş montaj cıvatası — geri alınabilir). Hangi modalitenin hangi arızayı yakaladığı ayrı ayrı raporlanmalı.
- **Doğrulama:** Eğitim/test ayrımı **seans bazlı** yapılmalı (aynı sürüşün verisi hem eğitim hem testte olmamalı) — aksi halde model ezberler, yanıltıcı yüksek doğruluk çıkar.
- **Açık kaynak veri setleri (CWRU, MaFaulDa, MIMII):** Doğrudan kullanım için işe yaramaz (domain gap — farklı makine/titreşim karakteri). Değeri **metodoloji referansı** (öznitelik çıkarım yöntemi) olarak sınırlı; transfer öğrenme ile alt katman aktarımı denenebilir ama kanıtlanmamış, "denendi, sonucu şu" şeklinde raporlanacak bir deney.
- **Doğruluk beklentisi (gerçekçi):** Test edilen spesifik arızalar için ~%80-90 tespit oranı beklenebilir (doğru koşullarla). Hiç test edilmemiş gerçek/organik arızalara (rulman aşınması, supap sorunu) genelleme **test edilmemiştir ve bilinmemektedir** — tezde bu açıkça bir sınırlama olarak belirtilmeli, sahte/abartılı genel doğruluk iddiası kurulmamalı (OVMS projesinin "sınırlamasını söylemeden kendinden emin yanlış sonuç" uyarısına karşı).

---

### 5b.10 Sanal Dinamometre (özellik havuzundan taşındı — çekirdeğe eklendi)

Motorun tekerlek gücü/torkunu harici dinamometre olmadan hesaplayan modül. Boylamsal ivme (IMU) + hız (CAN/GPS) + bilinen araç parametreleri (kütle, aktarma oranları, tekerlek yarıçapı) ile tekerlek kuvveti/gücü hesaplanır; yuvarlanma/aerodinamik direnç katsayıları coast-down testiyle kalibre edilir. Doğrulama: tekrarlanabilirlik + duyarlılık (bilinen değişiklik — dişli oranı — ile karşılaştırma) + mümkünse harici dinamometre referansı.

**Donanım:** Ek donanım gerekmiyor — mevcut IMU/CAN/GPS altyapısı yeterli. Sadece yazılım (60-90 saat).

### 5b.11 Konfor, Enerji ve Sürücü Destek Fonksiyonları (özellik havuzundan taşındı)

Bağlam veri yolu üzerine kurulu, düşük-orta ek maliyetli tamamlayıcı fonksiyonlar (özellik havuzu §9c'den, tam liste orada):

**Konfor (K1-K10):** Adaptif gösterge parlaklığı, ısıtmalı kumanda kontrolü, otomatik sinyal iptali, acil fren sinyali, yokuş kalkış desteği, rüzgar/hava uyarısı, yorgunluk/dikkat tespiti, sürüş günlüğü, sosyal/grup sürüş takibi, sesli navigasyon entegrasyonu.

**Enerji (E1-E5):** Enerji akış izleme, akü şarj durumu/sağlık kestirimi, düşük gerilim koruma, rejeneratif fren analizi (kavramsal, gelecek EV için), uyku/uyanıklık güç bütçesi yönetimi.

**Sürücü Destek (DR1-DR5):** Sürücü kimliği/kişisel profil, sürüş becerisi gelişim takibi, **kaza sonrası otomatik bildirim (eCall benzeri — F7 düşme tespiti + konum + GSM, motosiklet güvenliğinde somut ihtiyaç)**, geofence/bölge uyarıları, harita tabanlı hız limiti uyarısı.

**Kapsam notu:** Bu 20 alt fonksiyonun tamamı Faz 2/genişletilmiş kapsamda değerlendirilir; hiçbiri çekirdek teslim taahhüdüne dahil değildir, hoca raporunda tam kapsam şeffaflığı için listelenmiştir.

---

## 6. Modül mü Çip mi

Aşamaya ve çip türüne göre:

| Aşama | Ne kullanılır |
|---|---|
| Aşama 1 — prototip (şu an) | Hazır dev board (Nucleo, Discovery, ESP32 dev kit, Raspi kartı) |
| Aşama 2 — entegrasyon | Kendi taşıyıcı PCB; çip türüne göre modül veya çip |
| Aşama 3 — ürün (Faz 2+) | Çipler kendi PCB'de |

Çip türüne göre kural:
- **ESP32-S3 (RF çip):** modül al (WROOM/WROVER) — RF/anten/sertifikasyon işi, çıplak çip koyma
- **STM32 (saf MCU):** çıplak çip konabilir (referans devreyle) — öğretici, otomotivde standart
- **Raspi 5 (bilgisayar):** kart veya Compute Module (CM5)

**Sıra:** Önce Nucleo/dev board ile yazılım otursun, sonra çıplak çipe geç. İlk turda çıplak çip = donanım+yazılım hatasını aynı anda ayıklamak, kaçın.

---

## 7. Kademeli Kurulum

Hedef 5 birim ama hepsi bugün kurulmaz. İşlev geldikçe eklenir.

| Aşama | Birim | Tetikleyici |
|---|---|---|
| Şimdi | ESP32-S3 (geçici, tek — mevcut telemetri kodu) | Mevcut kod, henüz H7'ye geçilmedi |
| + | STM32H7 ana MCU'ya geçiş | Ana iş (telemetri, UDS, füzyon, kayıt) buraya taşınır; ESP32-S3 rolü daralır (bağlantı+ses) |
| + | Safety MCU | Viraj güvenlik modülü yapılınca |
| + | I/O MCU | Kör nokta / immobilizer / güç yönetimi birleşik düğümü (5b.1, 5b.3) yapılınca |
| + | Raspi 5 | Şerit takip / kamera / HMI gelince |
| Ayrı | HIL simülatör MCU | Tezgah (araçta değil) |

**Kural:** Her birim, kullanılacağı işlev gelene kadar eklenmez. Kullanılmayan birim = bakım yükü.

---

## 8. Repo Yapısı (çoklu-repo)

Repo sınırı = çalışma zamanı sınırı (farklı yerde/dilde/donanımda koşan şeyler ayrı repo). Kod modülü sınırı ise repo içinde klasörle çözülür.

| # | Repo | Çalışma zamanı | Dil |
|---|---|---|---|
| 1 | `moto-rt-core` | **STM32H7** (ana domain) | C/C++ |
| 2 | `moto-connectivity-node` | **ESP32-S3** (bağlantı+ses) | C/C++ |
| 3 | `moto-safety-node` | STM32 G4/F3 (viraj güvenlik) | C/C++ |
| 4 | `moto-io-node` | STM32 G0/F0 (kör nokta+immobilizer+güç) | C/C++ |
| 5 | `moto-linux-node` | Raspi 5 (şerit takip, kamera, HMI) | Python/C++ |
| 6 | `moto-hil-bench` | Simülatör MCU (STM32F4) + host PC | C/C++ + Python |
| 7 | `moto-server` | Sunucu | Python/Go |
| 8 | `moto-ml` | Offline eğitim | Python |
| 9 | `moto-mobile` | Telefon | Flutter/RN |
| 10 | `moto-vehicle-defs` | Paylaşılan tanım | DBC/YAML/VSS |
| 11 | **`moto-mcp`** | Raspi 5 (aynı çalışma zamanı, **ayrı repo — bağımsız açık kaynak proje**) | Python |

**moto-mcp neden ayrı repo (istisna gerekçesi):** Çalışma zamanı `moto-linux-node` ile aynı (Raspi 5), normalde tek repo/modül olurdu. Ama burada **paylaşım sınırı** geçerli sebep: bağımsız açık kaynak proje olarak yayınlanması hedefleniyor (başka DIY araç/motosiklet projeleri de kullanabilsin), GitHub'da kendi yıldız/katkı geçmişi olsun, kariyer vitrini parçası olsun isteniyor. `moto-linux-node` MCP istemcisi olarak `moto-mcp`'yi bir bağımlılık/alt süreç olarak çağırır.

**Ayrım gerekçesi (1 ve 2):** H7 ve ESP32-S3 farklı fiziksel çip, farklı derlenen binary, farklı flaş — gerçek çalışma zamanı sınırı. Aynı sebeple safety-node ve io-node de ayrı (farklı STM32 çip/flaş). Ana MCU'daki fonksiyonlar (UDS, XCP, EKF, bağlam, dinamometre, anomali çıkarımı) ise TEK repo içinde modül — hepsi aynı H7 binary'sinde derleniyor, ayrı repo sahte izolasyon olur.

**moto-vehicle-defs kilit taşı:** Sinyal tanımları, CAN mesaj haritası, VSS modeli. Diğer on repo bunu kaynak alır (submodule/paket). Tek gerçek kaynak → "iki birim aynı sinyali farklı biliyor" problemi hiç oluşmaz.

**Repo içi modüller (ayrı repo DEĞİL):** UDS/ISO-TP/bootloader, XCP, viraj EKF kestirimi, bağlam sınıflandırma, sanal dinamometre, anomali çıkarımı → `moto-rt-core` (H7) içinde `features/` altında klasör. Sesli komut (TinyML) → `moto-connectivity-node` (ESP32-S3) içinde modül.

**ML ayrımı:** Eğitim (Python, offline) → `moto-ml`. Çıkarım (araçta koşan model) → ilgili düğümün `features/` klasörü (bağlam/anomali → rt-core, sesli komut → connectivity-node, şerit takip → linux-node).

**Bağımlılık yönü (tek yönlü):**
```
moto-vehicle-defs → herkes okur
moto-rt-core → moto-vehicle-defs
moto-connectivity-node → moto-vehicle-defs, (köprüyle) rt-core
moto-safety-node → moto-vehicle-defs
moto-io-node → moto-vehicle-defs
moto-linux-node → moto-vehicle-defs, (köprüyle) rt-core, moto-mcp (alt süreç/bağımlılık olarak çağırır)
moto-mcp → moto-vehicle-defs (araç şemaları için), bağlam veri yoluna Raspi üzerinden yerel erişim
moto-hil-bench → moto-vehicle-defs
moto-server → moto-vehicle-defs
moto-ml → moto-vehicle-defs, moto-server
moto-mobile → moto-vehicle-defs, moto-server
```

**Disiplin:** `moto-vehicle-defs` sürümlenir (v1.0, v1.1); diğer repolar belirli sürüme sabitlenir. Sinyal değişince hangi reponun güncelleneceği net olur, hiçbiri sessizce bozulmaz.

---

## 9. Repo Kurulum Sırası

1. `moto-vehicle-defs` — herkes buna bağlı, önce bu (küçük ama temel)
1. `moto-vehicle-defs` — herkes buna bağlı, önce bu (küçük ama temel)
2. `moto-hil-bench` — uzaktan geliştirilebilir (donanımsız, host+simülatör, Renode ile bile)
3. `moto-connectivity-node` (ESP32-S3) — mevcut kod burada zaten çalışıyor, geçiş kolay
4. `moto-rt-core` (STM32H7) — ana MCU geçişi, atölyede donanımla
5. `moto-server` — veri toplama sunucusu
6. `moto-ml` — veri birikince
7. `moto-safety-node` — viraj güvenlik modülü yapılınca
8. `moto-io-node` — kör nokta/immobilizer/güç birleşik düğümü yapılınca
9. `moto-linux-node` — Raspi/şerit takip entegrasyonu gelince
10. `moto-mobile` — en son

---

## 9b. HIL Tezgahı Donanım Mimarisi

HIL tezgahı, araç sistemini test eden **ayrı** bir donanımdır — araçtaki 5 birimlik mimariyle karışmaz. Kendi çipi, beslemesi ve ölçüm katmanı vardır. Amacı: DUT'un (test edilen araç ünitesi) gerçek araçta göreceği elektriksel ortamı masada taklit etmek.

### 9b.1 Temel İlke — Neyin Aynı, Neyin Farklı Olduğu

- **DUT ve DUT'un gördüğü arayüz AYNI olmalı** (gereklilik): CAN transceiver, CAN hızı/protokol, OBD2 konnektör, sinyal tanımları, besleme gerilim profili. Aksi halde test geçersiz olur.
- **Simülatörün beyni FARKLI olmalı** (bağımsızlık ilkesi): simülatör çipi, araç ana çipiyle aynı olmamalı — aynı olursa aynı kör noktayı/hatayı paylaşır, test onu yakalayamaz. Denge: aynı üretici ailesi (STM32 — tek araç zinciri), farklı sınıf ve rol, farklı kütüphane kullanımı.

### 9b.2 Mimari — Restbus Simülasyonu

Aracı bütün olarak taklit etmek için **restbus simülasyonu** kullanılır: tek güçlü çip, yazılımda birden çok sanal ECU olarak (motor ECU, ABS, gösterge) farklı CAN ID'lerinden konuşur. Her ECU için ayrı çip gerekmez — CAN zaten tek hat, farklı ID yeterli. Sektör standardı yaklaşım, sadelik prensibiyle uyumlu.

```
        HOST (i7 5. nesil masaüstü + Linux/SocketCAN)
        senaryo motoru, loglama, rapor  —  kalıcı test istasyonu / ileride CI runner
              │ USB/UART
        ┌─────┴──────┐
        │  STM32F4   │  ← SİMÜLATÖR DÜĞÜMÜ
        │ · restbus (çok sanal ECU)
        │ · araç dinamik modeli (gaz→devir→hız)
        │ · CAN mesaj üretimi
        └──┬───────┬─┘
           │CAN    │kontrol
      ═════╪═══    │
      test │   ┌───┴────────┐
     edilen│   │ STM32F103  │ ← arıza enjeksiyon + besleme kontrolü
     cihaz │   │ + prog.    │   (bozuk çerçeve, hat kesme,
     (DUT)─┘   │ besleme    │    programlanabilir voltaj)
               └────────────┘
```

### 9b.3 Bileşenler ve Çip Seçimi

| Bileşen | Çip/donanım | Durum | Rol |
|---|---|---|---|
| Simülatör beyni | **STM32F4** (F407/F429) | Alınacak | Restbus + araç modeli + CAN üretimi |
| Arıza/besleme kontrol | **STM32F103** | Elinde var | Voltaj oynatma, hat kesme, bozuk çerçeve |
| Host (senaryo motoru) | **i7 5. nesil masaüstü** + Linux | Elinde var | Python senaryo motoru, SocketCAN |
| CAN transceiver ×2 | SN65HVD230 vb. | Alınacak | Simülatör + DUT tarafı fiziksel katman |
| Programlanabilir besleme | Buck + DAC/dijital pot | Alınacak | Akü/marş/aşırı-düşük voltaj senaryoları |
| DUT bağlantısı | OBD2 konnektör, kablo, sonlandırma | Alınacak | DUT'u gerçek soketle bağlama |

**Çip gerekçesi (STM32F4):** FPU (araç dinamik modeli için), çok CAN, sektörde çok yaygın (bol örnek), makul fiyat. openpilot panda da STM32F4 kullanıyor (araç-CAN donanımı doğrulaması). Araç ana çipi H7/ESP32-S3'ten farklı sınıf → bağımsızlık sağlanır. H7 simülatör için israf, F103 (elde) tek CAN + FPU yok olduğu için ana simülatör düğümü olarak zayıf — yardımcı role uygun.

**Elenen:** NXP S32K (gerçek otomotiv çipi, öğretici olurdu ama kart ~10 bin TL — maliyet nedeniyle Faz 2'ye).

### 9b.4 Host = Bilgisayar (simülatör değil)

Ayrım önemli: bilgisayar (i7) **host**tur, senaryo motorunu koşturur ("voltajı düşür, bozuk mesaj gönder" komutları). STM32F4 **simülatör**dür, o komutları gerçek CAN sinyaline çevirir. Bilgisayarın CAN donanımı yok, tek başına sinyal üretemez — F4 şart. Bilgisayar "beyin/senaryo", F4 "eller/sinyal".

Host için i7 masaüstüne Linux kurulması önerilir: SocketCAN native çalışır, kalıcı açık kalıp test otomasyonu/CI runner'a dönüşebilir, Mac'i serbest bırakır.

### 9b.5 Kaba Maliyet

Alınacak tek ana parça STM32F4 kartı; gerisi elde veya ucuz. Toplam yeni harcama ~800-1600 TL (STM32F4 300-600, transceiver 160-300, besleme 200-400, konnektör/kablo 150-300). Host ve F103 elde.

**Onay durumu:** Bu HIL donanım listesi (STM32F4 simülatör + STM32F103 arıza/besleme + i7 host + transceiver ×2 + programlanabilir besleme + OBD2 bağlantı) kullanıcı tarafından onaylandı.

### 9b.6 Host Tarafı Görselleştirme ve Kontrol Paneli

HIL host'unda test bir monitör üzerinden izlenip yönlendirilir. İki katman ayrı tutulur:

- **Kontrol paneli / görselleştirme (host'ta):** Senaryo başlat/durdur, parametre ayarı (voltaj, devir), canlı CAN trafiği, gecikme grafikleri, geçen/kalan test göstergesi. Araç: web dashboard veya Foxglove/PlotJuggler. **Çekirdek — yapılacak.** Demo ve sunum değeri yüksek; endüstriyel HIL'deki kontrol masası (dSPACE ControlDesk) mantığının ölçekli hali.
- **Araç dinamik modeli (simülatör firmware'inde):** Başlangıçta basit fizik (gaz→devir→hız); detaylı model (vites, tork eğrisi, direnç) sonra. Endüstriyel HIL'deki Simulink model katmanının karşılığı.

**Sınır:** 3D motosiklet modeli, gerçekçi sürüş fiziği, animasyonlu ortam YAPILMAYACAK — bunlar HIL'i test aracı olmaktan çıkarıp sürüş simülatörü/oyun projesine kaydırır. Panel + basit gösterge + grafik yeterli.

---

## 10. Faz 2 / Sonraki Aşama (Konsolide Liste)

Aşağıdaki tüm kalemler **tek bir "sonraki aşama" havuzunda** toplanmıştır — alt fazlara ayrılmamıştır, önceliklendirme/sıralama kullanıcı tarafından ayrıca yapılacaktır. Çekirdek teslim taahhüdüne dahil değildir.

### 10.1 Kalıcı Olarak Elenenler (Faz 2'de bile değerlendirilmeyecek)

| Kalem | Neden kalıcı elendi |
|---|---|
| NXP S32K / Infineon AURIX (safety MCU gerçek ASIL çipi) | Maliyet (~10.000 TL) proje bütçesiyle orantısız — kalıcı, "ileride bakılır" değil |
| NXP S32K (HIL simülatör çipi) | Aynı maliyet gerekçesi — STM32F4 kalıcı karar |
| İmmobilizer'ın ECU ile tam entegrasyonu (OEM sınıfı) | Honda'nın kapalı protokolünü (seed-key) çözmek gerektirir — ayrı bir tersine mühendislik projesi, kapsam dışı. Mevcut röle tabanlı tasarım **caydırıcı sınıf** olarak kabul edilir, OEM güvenlik seviyesi iddia edilmez — tezde açıkça belirtilecek bir sınırlama |

### 10.2 Onaylanmış Faz 2 Yol Haritası (yapılacak, zamanlaması sonraki aşama)

| Kalem | Ne getirir | Bağımlılık/not |
|---|---|---|
| Velocitas SDK | Linux node modüllerini standart "Vehicle App" kalıbına taşır | Kuksa Databroker'ın (çekirdek) üstüne oturur |
| Eclipse Kanto | Konteyner tabanlı OTA/uygulama yönetimi (Linux tarafı) | Raspi kapasite bütçesi elverdiğinde |
| SOME/IP | H7↔ESP32 köprüsünü otomotiv orta katman standardına taşır | Şu anki basit mesajlaşmanın yerini alır |
| DoIP | UDS'i Ethernet üzerinden taşıma (yeni nesil teşhis protokolü) | Raspi'nin doğal Ethernet arayüzü üzerinden |
| Derin öğrenme LDW yükseltmesi (UFLD/Fast-CenLaneNet) | Zor sahne (gece, silik çizgi) dayanıklılığı | Düşük öncelik — kullanıcı şerit takibe fazla önem vermeyecek, klasik CV yeterli görülüyor |
| Moto-MCP aktüatör-yazma yeteneği (onay kapılı) | LLM'in kendi eklenen çevre aktüatörlerini (ışık, ısıtma, kamera) tetikleyebilmesi | Motor/ECU kontrolüne asla genişletilmez; operatör onay kapısı zorunlu |
| NFC kriptografik yükseltme (MIFARE DESFire) | Klonlanmaya dayanıklılık | PN532 donanımı destekliyor, ek kütüphane (yazılım) gerekir |
| Nextion → LVGL+ESP32/round display | Ana ekranın zenginleştirilmesi | Referanslar: moto2000, opencluster, DIY-dash-5, evj55-dashboard |
| Raspi 5 özel taşıyıcı/güç PCB'si | **Fonksiyon değil, standartlaşma adımı** — üretim olgunlaştırma | Liste sonunda, tasarım oturunca yapılacak |

### 10.3 Diğer Açık Notlar

- Safety MCU'nun ana MCU'yu nasıl denetleyeceği (watchdog/heartbeat) — safety MCU donanımı netleşince tasarlanacak
- HIL simülatörünün gerçekçilik seviyesi (kayıtlı mesaj tekrarı mı, canlı araç dinamik modeli mi) ve ilk hedef test fonksiyonu henüz seçilmedi
- Araç hattının klasik CAN mı CAN-FD mi olduğu doğrulanmalı (sinyal haritası çıkarırken)
- Süspansiyon potansiyometreleri — Grup 11'de (donanım tedarik listesi), ekleme kararı henüz kesinleşmedi

### 10.4 Çekirdeğe Taşınanlar (artık Faz 2'de DEĞİL — hatırlatma)

Önceki tartışmalarda "opsiyonel/Faz 2" işaretliyken, sonradan çekirdeğe alınan kalemler (karışıklığı önlemek için):

- Yağ basıncı/sıcaklık sensörü — donanım listesine eklendi
- GSM modülü (park modu/hırsızlık takibi) — artık çekirdek, WhatsApp bildirim kanalıyla birlikte
- Fren hattı basınç sensörü — donanım listesine eklendi
- ECU davranış analizi — ev sunucusunda (Raspi 3B+ üzerinde), offline analiz olarak planlandı. **Yöntem (meşru, ECU flash'ına YAZMADAN):** çalışma anı CAN/OBD verisinden ECU davranışını karakterize etmek — gaz haritası tepkisi, yakıt trim, sıcaklık telafisi, devir limiti, yük hesabı ("black-box characterization"); çıkarılan davranış HIL araç modeline beslenebilir. Chiptuning ile farkı: okuma/analiz meşru ve planlı, flash'tan harita çıkarma teknik olarak çok zor (Honda koruması, seed-key) ve ayrı bir tersine mühendislik işi; ECU'ya YAZMA (harita değiştirme) yasal/garanti/güvenlik nedeniyle kalıcı olarak kapsam dışı (bkz. 10.1).
- Sanal dinamometre, konfor/enerji/sürücü destek fonksiyonları (20 alt fonksiyon) — bölüm 5b.10-5b.11'e eklendi

---
