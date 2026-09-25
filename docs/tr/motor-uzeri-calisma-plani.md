# Araç Üzeri Çalışma Planı — Honda CL250

**Proje:** Gömülü teşhis ve sürücü destek ünitesi / HIL doğrulama altyapısı
**Doküman kapsamı:** Motosiklet üzerinde yapılacak tüm donanım entegrasyonu, parametre ölçümü, veri toplama ve saha testi faaliyetleri
**Sürüm:** 1.0 — Eylül 2026

---

## 1. Amaç ve Kapsam

Bu doküman, geliştirilen ünitenin araca entegrasyonunu, araç parametrelerinin ölçülmesini, veri toplama protokollerini ve saha doğrulama testlerini tanımlar.

**Kapsam dışı:** ECU yazılımına müdahale, motor kontrol parametrelerinin değiştirilmesi, emisyon sistemine müdahale. Gerekçeleri bölüm 12'de.

---

## 2. Araç Temel Verileri

Aşağıdaki değerler üretici spesifikasyonundan alınmıştır ve hesaplamalarda taban veri olarak kullanılacaktır.

| Parametre | Değer |
|---|---|
| Motor | 249 cc, su soğutmalı, DOHC 4 valf, tek silindir |
| Çap × strok | 76.0 × 55.0 mm |
| Sıkıştırma oranı | 10.7 |
| Maksimum güç | 18 kW (24 PS) / 8500 rpm |
| Maksimum tork | 23 N·m / 6250 rpm |
| Yakıt sistemi | PGM-FI |
| Şanzıman | 6 ileri, sürekli kavramalı |
| Ağırlık (dolu) | 172 kg |
| Aks mesafesi | 1485 mm |
| Kaster açısı | 27°00′ |
| Trail | 108 mm |
| Sele yüksekliği | 790 mm |
| Yerden yükseklik | 163 mm |
| Ön lastik | 110/80 R19 |
| Arka lastik | 150/70 R17 |
| Fren | Ön/arka hidrolik disk, ABS |
| Yakıt deposu | 12 L |

### 2.1 Aktarma Organları Oranları

| Konum | Oran |
|---|---|
| Birincil redüksiyon | 2.807 |
| İkincil redüksiyon | 2.642 |
| 1. vites | 3.416 |
| 2. vites | 2.250 |
| 3. vites | 1.650 |
| 4. vites | 1.350 |
| 5. vites | 1.166 |
| 6. vites | 1.038 |

**Toplam redüksiyon** = birincil × vites × ikincil

| Vites | Toplam oran |
|---|---|
| 1 | 25.33 |
| 2 | 16.68 |
| 3 | 12.23 |
| 4 | 10.01 |
| 5 | 8.645 |
| 6 | 7.698 |

Bu tablo vites tespiti, sanal dinamometre ve hız doğrulaması için kullanılacaktır.

### 2.2 Arka Tekerlek Yarıçapı (hesap)

Lastik 150/70 R17:
- Jant çapı: 17″ = 431.8 mm → jant yarıçapı 215.9 mm
- Yanak yüksekliği: 150 × 0.70 = 105.0 mm
- Yüksüz yarıçap: 215.9 + 105.0 = **320.9 mm**
- Dinamik (yüklü) yarıçap ≈ %2-4 daha küçük → **~311 mm** (ölçümle doğrulanacak)
- Yuvarlanma çevresi (yüksüz): 2π × 0.3209 = **2.016 m**

**Doğrulama yöntemi:** Sürücü üzerindeyken lastiğe tebeşir işareti konur, düz zeminde 10 tam tur yuvarlanır, alınan mesafe ölçülür ve 10'a bölünür. Bu değer hesaplanan çevreyle karşılaştırılır. Ölçülen değer kullanılacaktır.

### 2.3 Hız Doğrulama Formülü

```
v [m/s] = (rpm / 60) / toplam_oran × yuvarlanma_çevresi
```

Örnek: 6. vites, 6000 rpm
v = (6000/60) / 7.698 × 2.016 = 100 / 7.698 × 2.016 = **26.2 m/s = 94.3 km/h**

Bu hesap, CAN'dan okunan hız sinyalinin doğruluğunu bağımsız olarak kontrol etmek için kullanılacaktır. Sapma varsa gösterge hatası (motosikletlerde tipik olarak %5-10 yüksek gösterir) karakterize edilecektir.

---

## 3. Araca Monte Edilecek Donanım

### 3.1 Ana Ünite (DUT)

| Özellik | Karar |
|---|---|
| İşlemci | ESP32-S3 |
| Muhafaza | ABS veya alüminyum kutu, minimum IP54 |
| Montaj yeri | Sele altı veya yan panel içi (tercih: sele altı) |
| Titreşim yalıtımı | Silikon takoz veya çift taraflı titreşim bandı |
| Bağlantı | Ayrılabilir konnektör (araçtan sökülebilir olmalı) |
| Boyut hedefi | 100 × 70 × 30 mm altı |

**Montaj yeri gerekçesi:** Sele altı hem sıcaktan (egzoz, silindir) uzak hem de doğrudan yağmura maruz kalmıyor. Motor bloğuna yakın montajdan kaçınılacak — sıcaklık ve titreşim iki katına çıkar.

### 3.2 Veri Yolu Bağlantısı

| Öğe | Detay |
|---|---|
| Nokta | Teşhis konnektörü (DLC) |
| Kullanılan hatlar | CANH, CANL, GND |
| Bağlantı şekli | Y kablo — orijinal konnektöre paralel, kesme yok |
| Sonlandırma | **Ekleme.** Hat zaten iki uçtan sonlandırılmış durumda; üçüncü direnç hattı bozar |
| Kablo | Bükümlü çift, mümkünse ekranlı |
| Uzunluk | 50 cm altı |

**Kritik not:** CAN hattına ek sonlandırma direnci konulmayacaktır. Tezgahta simülatör tarafı ayrı bir hat olduğu için orada sonlandırma gerekir; araçta gerekmez.

**Güvenlik notu:** İlk bağlantı motor kapalıyken ve sadece dinleme modunda yapılacak. Hatta mesaj yazılmayacak. Yazma denemesi ancak trafiğin yapısı tam anlaşıldıktan sonra, kapalı alanda ve motor rölantideyken yapılacak.

### 3.3 Güç Beslemesi

| Öğe | Detay |
|---|---|
| Besleme noktası | Kontakla beslenen hat (sürekli akü hattı değil) |
| Sigorta | 2 A, cam veya bıçak tipi, ünite girişinde |
| Ters polarite koruması | Seri Schottky diyot veya P-MOSFET |
| Geçici aşırı gerilim | TVS diyot (bidireksiyonel, 24-30 V clamp) |
| Gerilim düşürme | Geniş girişli buck (6-40 V giriş, 5 V çıkış) |
| Filtreleme | Giriş tarafında elektrolitik + seramik |
| Toprak | Şasi değil, aracın negatif hattına doğrudan |

**Gerekçe:** Kontak hattından beslemek, motosiklet park halindeyken akünün boşalmasını engeller. Sürekli hat kullanılacaksa uyku akımı 1 mA altında tutulmalı ve bu ölçülerek doğrulanmalı.

### 3.4 IMU (Ivme + Jiroskop)

| Öğe | Detay |
|---|---|
| Sensör | 6 eksen MEMS (ivme + jiroskop), tercihen 9 eksen |
| Montaj yeri | Ana ünite içinde veya şasi üzerinde sabit nokta |
| Montaj sertliği | Rijit — titreşim yalıtımı **yapılmayacak** |
| Örnekleme | Minimum 100 Hz, tercihen 200 Hz |
| Eksen hizalaması | Aracın boyuna ekseniyle hizalı, sapma ölçülüp yazılımda düzeltilecek |

**Kritik not:** IMU titreşim takozuna monte edilmemeli. Takoz kendi rezonansını ölçüme katar ve yatış açısı kestirimini bozar. Buna karşılık motor titreşimi (tek silindirde belirgin) alçak geçiren filtreyle bastırılacak.

**Hizalama prosedürü (bölüm 5.4'te detaylı):** Motosiklet düz zeminde dik tutulur, sıfır referansı alınır; ardından bilinen açıda (örneğin sehpayla 10°) yatırılıp ölçüm doğrulanır.

### 3.5 GPS Modülü

| Öğe | Detay |
|---|---|
| Modül | u-blox NEO-M8N veya eşdeğeri |
| Güncelleme hızı | Minimum 5 Hz, tercihen 10 Hz |
| Anten | Aktif, seramik yamalı |
| Montaj yeri | Gökyüzü görüşü açık — gidon bölgesi veya sele arkası |
| Kullanım | Konum, yer hızı, viraj yarıçapı hesabı, tur analizi |

**Not:** Metal muhafaza içine konulmayacak. GPS'in yer hızı verisi, CAN hız sinyalinin doğrulanmasında ikinci bağımsız referans olarak kullanılacak.

### 3.6 Sesli Komut Donanımı (G4 modülü için)

| Öğe | Detay |
|---|---|
| Mikrofon | Gürültü önleyici elektret veya hazır interkom mikrofonu |
| Yerleşim | Kask içi, ağız hizası |
| Bağlantı | Kablolu (tercih) veya mevcut interkom üzerinden BT |
| Tetikleme | Gidona monte bas-konuş butonu |
| Buton yerleşimi | Sol gidon, eldivenle basılabilir konumda |
| Geri bildirim | Kask içi hoparlör veya interkom hoparlörü |

**Gerekçe:** Wake word yerine bas-konuş seçilmesi, rüzgar gürültüsünde yanlış tetiklenme problemini tamamen ortadan kaldırır ve işlemci yükünü düşürür.

### 3.7 Opsiyonel — Süspansiyon Enstrümantasyonu

| Öğe | Detay |
|---|---|
| Sensör | Lineer potansiyometre veya çekme telli enkoder |
| Konum | Ön çatal ve arka amortisör paralelinde |
| Ölçüm | Süspansiyon stroku, hız |
| Kullanım | Yol yüzeyi sınıflandırma, ön-arka yük dağılımı, ayar etkisi |

Bu kalem genişletilmiş kapsamdadır. Eklenirse yol yüzeyi sınıflandırma modelinin girdi kalitesini belirgin şekilde artırır.

### 3.8 Opsiyonel — Sıcaklık Sensörleri

| Nokta | Sensör | Amaç |
|---|---|---|
| Ortam | Dijital (ünite içinde) | Referans, düzeltme |
| Ünite içi | Dijital | Termal davranış izleme |
| Fren diski | Temassız IR | Fren yükü analizi |
| Egzoz (opsiyonel) | K tipi termokupl | Yanma kalitesi göstergesi |

Egzoz sıcaklığı ölçümü arıza tespiti çalışması için değerlidir ancak Faz 2 kapsamındadır.

---

## 4. Kablolama ve Elektriksel Entegrasyon

### 4.1 Genel Kurallar

- Orijinal tesisatta **kesme yapılmayacak**. Tüm bağlantılar paralel veya konnektör aracılığıyla.
- Ünite tek bir ayrılabilir konnektörle araçtan sökülebilir olmalı (test, servis, muayene için).
- Kablolar titreşimden korunacak: spiral sargı veya oluklu boru içinde.
- Hareketli parçalardan (direksiyon, süspansiyon, zincir) uzak güzergâh.
- Isı kaynaklarından (egzoz, silindir, radyatör) minimum 15 cm uzaklık veya ısı kalkanı.
- Her kablo ucu etiketlenecek; kablolama şeması dokümante edilecek.

### 4.2 Gürültü ve EMC Önlemleri

Tek silindirli motorlarda ateşleme sistemi güçlü elektromanyetik gürültü üretir. Önlemler:

- Sinyal kabloları ateşleme bobini ve buji kablosundan uzak tutulacak
- CAN hattı bükümlü çift olacak
- Analog sinyaller (varsa) ekranlı kablo, ekran tek uçtan topraklanacak
- Besleme girişinde LC filtre
- Ünite muhafazası metal ise şasi toprağına bağlanacak

**Doğrulama:** Motor çalışırken ve çalışmazken aynı ölçüm alınıp karşılaştırılacak. Motor çalışırken sinyal gürültüsünde belirgin artış varsa filtreleme gözden geçirilecek.

### 4.3 Uyku Akımı Doğrulaması

Kontak kapalıyken ünitenin çektiği akım multimetre veya INA sensörüyle ölçülecek. Hedef: **< 1 mA**. Aşılırsa besleme hattı kontakla anahtarlanacak.

---

## 5. Araç Parametrelerinin Ölçülmesi

Bu parametreler hem sanal dinamometre hem viraj güvenlik modülü hem de HIL plant modeli için gereklidir.

### 5.1 Toplam Kütle

| Yöntem | Detay |
|---|---|
| Baskül | Ön ve arka tekerlek ayrı ayrı tartılır |
| Ölçüm koşulları | Boş depo / dolu depo / sürücülü / sürücü + yük |
| Kayıt | Her senaryo için ayrı değer tablosu |

Baskül bulunamazsa üretici değeri (172 kg) + sürücü ağırlığı + yakıt (12 L × 0.75 kg/L = 9 kg) kullanılır; yöntem tezde belirtilir.

### 5.2 Ağırlık Dağılımı ve Ağırlık Merkezi

**Boylamsal dağılım:** Ön ve arka tekerlek ayrı tartımıyla bulunur.

```
x_CG = L × (W_arka / W_toplam)      (ön akstan uzaklık)
```

**Yükseklik (h_CG):** Motosikletin arka tekerleği yükseltilerek (bilinen açıda) ön akstaki yük değişimi ölçülür ve h_CG hesaplanır. Bu ölçüm özen ister; alternatif olarak literatürden benzer sınıf motosiklet değeri (tipik 0.45-0.60 m) kullanılıp tezde varsayım olarak belirtilir.

h_CG, viraj güvenlik modülünde kritik yatış açısı hesabına doğrudan girer.

### 5.3 Tekerlek Yarıçapı

Bölüm 2.2'deki yuvarlanma ölçümü. Sürücü üzerindeyken ve normal lastik basıncında yapılacak. Lastik basıncı kaydedilecek (sonraki ölçümlerde aynı basınç kullanılacak).

### 5.4 IMU Hizalama ve Kalibrasyon

| Adım | İşlem |
|---|---|
| 1 | Motosiklet düz, yatay zeminde, merkez sehpada dik konumda |
| 2 | 60 saniye statik kayıt → ivmeölçer ofset ve jiroskop sapması (bias) hesaplanır |
| 3 | Bilinen açıda yatırma (örneğin 10° ve 20°, açıölçerle doğrulanmış) → eksen ölçek doğrulaması |
| 4 | Boyuna eksen hizalama: düz yolda sabit hızda gidilir, boyuna ivme sıfıra yakın olmalı |
| 5 | Elde edilen düzeltme matrisi yazılıma gömülür |

**Sıcaklık etkisi:** MEMS jiroskop sapması sıcaklıkla değişir. Farklı ortam sıcaklıklarında (sabah/öğle) statik ölçüm tekrarlanıp sapma-sıcaklık ilişkisi çıkarılacak.

### 5.5 CAN Sinyal Haritasının Çıkarılması

| Adım | İşlem | Beklenen çıktı |
|---|---|---|
| 1 | Kontak açık, motor kapalı, 5 dk ham kayıt | Bus'ta hangi ID'ler var, periyotları ne |
| 2 | Rölantide 5 dk kayıt | Devirle değişen byte'ların tespiti |
| 3 | Kontrollü gaz açma (durağan) | Devir ve TPS byte'larının izolasyonu |
| 4 | Düşük hızda sürüş | Hız byte'ının tespiti |
| 5 | Motor ısınma süreci (soğuktan) | Sıcaklık byte'ının tespiti |
| 6 | Fren uygulama | Fren anahtarı biti |
| 7 | Standart OBD2 PID taraması | Desteklenen PID listesi |

Her adımda değişen byte'lar işaretlenerek sinyal tanım dosyası (DBC benzeri) oluşturulacak. Bu dosya, HIL tezgahının araç bağımsız mimarisinde CL250 tanımı olarak kullanılacak.

**Not:** Üreticiye özel mesajların anlamı kesinleştirilemezse, tanım dosyasında "doğrulanmamış" etiketiyle kaydedilecek. Tahmine dayalı yorum yapılmayacak.

---

## 6. Veri Toplama Planı

### 6.1 Kaydedilecek Sinyaller

| Kaynak | Sinyal | Frekans |
|---|---|---|
| CAN | Motor devri | 10-20 Hz |
| CAN | Araç hızı | 10 Hz |
| CAN | Gaz kelebeği pozisyonu | 10-20 Hz |
| CAN | Motor sıcaklığı | 1 Hz |
| CAN | Emme basıncı / hava akışı | 10 Hz |
| CAN | Yakıt trim (varsa) | 1 Hz |
| CAN | Akü gerilimi | 1 Hz |
| CAN | Arıza kodları | Olay bazlı |
| IMU | 3 eksen ivme | 100-200 Hz |
| IMU | 3 eksen açısal hız | 100-200 Hz |
| Türetilmiş | Yatış açısı | 100 Hz |
| GPS | Enlem, boylam, yer hızı, yön | 5-10 Hz |
| Ünite | Besleme gerilimi, akım | 10 Hz |
| Ünite | İç sıcaklık | 0.1 Hz |
| Ünite | Yığın kullanımı, görev süreleri | 1 Hz |

**Profil bazlı frekans:** Şehir profilinde düşük, sportif profilde yüksek örnekleme (bölüm 9'daki asistan profilleri).

### 6.2 Meta Veri (her seans için)

Her kayıt seansının başında aşağıdakiler kaydedilecek:

- Tarih, saat, seans kimliği
- Ortam sıcaklığı, hava durumu (kuru/ıslak)
- Lastik basıncı (ön/arka)
- Yakıt seviyesi
- Sürücü ağırlığı, ek yük
- Motosikletin konfigürasyonu (dişli, egzoz, filtre — modifikasyon deneyleri için)
- Güzergâh türü (şehir / kırsal / otoyol / kapalı alan)
- Serbest not alanı

Bu meta veri, ileride kurulacak modellerin etiketlenmesi için zorunludur. Meta verisiz kayıt, sonradan kullanılamaz hale gelir.

### 6.3 Saklama

| Öğe | Karar |
|---|---|
| Format | İkili (binary) kayıt + JSON meta veri |
| Zaman damgası | Mikrosaniye, monoton sayaç + GPS senkronizasyonu |
| Ortam | microSD (araçta) → sunucu (seans sonrası) |
| Dosya bölme | Seans başına bir dosya, maksimum 100 MB |
| Bütünlük | Her bloğa CRC, ani kesintide son blok kurtarılabilir olmalı |
| Yedekleme | Her seans sonrası bilgisayara kopyalama, ikinci kopya bulutta |

**Kritik:** Veri kaybı geri alınamaz. Kayıt formatı ve yedekleme disiplini daha ilk seanstan itibaren oturmalı.

### 6.4 Toplama Takvimi

Veri toplama, proje takviminin 4. haftasından itibaren sürekli işletilecektir. Her sürüş bir veri seansıdır. Hedef: dönem sonunda minimum **40 saat** etiketli sürüş verisi.

---

## 7. Saha Test Protokolleri

### 7.1 Test Sınıfları ve Ortamları

| Sınıf | Ortam | Hız aralığı |
|---|---|---|
| T0 — Statik | Garaj/atölye | 0 |
| T1 — Düşük hız | Kapalı otopark | 0-30 km/h |
| T2 — Orta hız | Boş sanayi yolu / kapalı alan | 30-70 km/h |
| T3 — Yüksek hız | Kırsal yol (trafik dışı saatler) | 70-100 km/h |
| T4 — Limit testleri | **Yalnızca kapalı alan / pist** | Değişken |

**Kural:** T4 sınıfı testler hiçbir koşulda kamu yolunda yapılmayacaktır.

### 7.2 T0 — Statik Testler

| Test | Prosedür | Başarı kriteri |
|---|---|---|
| Bağlantı doğrulama | Kontak açık, CAN trafiği okunuyor mu | Mesaj alınıyor, hata sayacı artmıyor |
| Uyku akımı | Kontak kapalı, akım ölçümü | < 1 mA |
| Marş anı davranışı | Marş basılırken kayıt | Ünite reset atmıyor, kayıt bozulmuyor |
| Rölanti kararlılığı | 10 dk rölanti kaydı | Devir dalgalanması karakterize edildi |
| Isınma profili | Soğuktan çalışma sıcaklığına | Sıcaklık sinyali doğrulandı |
| Gürültü ölçümü | Motor açık/kapalı sinyal karşılaştırması | Gürültü artışı kabul sınırında |
| Sesli komut (garajda) | 20 komut × 10 tekrar | Tanıma oranı > %90 |

### 7.3 T1 — Düşük Hız Testleri

| Test | Prosedür |
|---|---|
| Hız sinyali doğrulama | Bilinen mesafe, sabit hız; CAN hızı vs GPS hızı vs hesap |
| Vites tespiti | Her viteste sabit hız; devir/hız oranından vites çıkarımı doğrulaması |
| IMU yatış doğrulama | Düşük hızda dar daire, yatış açısı kaydı |
| Fren sinyali | Kademeli fren, sinyal ve ivme korelasyonu |
| Kayıt bütünlüğü | Sürüş sırasında kontak kesme, dosya kurtarılabilirliği |

### 7.4 T2/T3 — Yol Testleri

| Test | Prosedür |
|---|---|
| Sabit hız seyri | Her viteste 2 dk sabit hız; tüketim ve yük verisi |
| Hızlanma koşuları | Sanal dinamometre (bölüm 8) |
| Fren testleri | Kademeli yavaşlama, fren ivmesi karakterizasyonu |
| Viraj verisi | Normal sürüş virajları, yatış açısı dağılımı |
| Uzun seyir | 1+ saat kesintisiz, termal ve bellek davranışı |
| Sesli komut (sürüşte) | Farklı hızlarda tanıma oranı: 30/50/70/90 km/h |

**Sesli komut testi notu:** Hız arttıkça rüzgar gürültüsü artar. Tanıma oranının hıza göre değişimi ölçülüp raporlanacak — bu, tezde gerçek bir deney sonucu olur.

### 7.5 T4 — Limit ve Güvenlik Testleri

**Bu testler yalnızca kapalı alanda, koruyucu ekipmanla ve kademeli yaklaşımla yapılacaktır.**

| Test | Prosedür | Güvenlik kuralı |
|---|---|---|
| Viraj limiti kalibrasyonu | Bilinen yarıçaplı daire, hız kademeli artırılır | Her kademe +5 km/h, yatış açısı izlenir, rahatsızlık hissinde durulur |
| Uyarı eşiği doğrulama | Uyarı tetiklenme noktası kaydedilir | Uyarı sonrası limit zorlanmaz |
| Acil fren | Kuru zeminde maksimum fren | ABS devrede, kademeli yaklaşım |
| Düşük sürtünme (opsiyonel) | Islak zemin, düşük hız | Yalnızca 30 km/h altı |

**Zorunlu güvenlik kuralları:**

1. Tam koruyucu ekipman: kask, sırt koruması, ceket, eldiven, bot
2. Test alanında ikinci bir kişi bulunacak
3. Tek seansta limit testi süresi 30 dakikayı geçmeyecek (yorgunluk)
4. Veri kaydının çalışıp çalışmadığı sürüş sırasında kontrol edilmeyecek — seans öncesi doğrulanacak
5. Yeni yazılım sürümü ilk kez T4'te denenmeyecek; önce T1'de doğrulanacak
6. Hava durumu uygun değilse (ıslak, rüzgarlı) seans ertelenecek

**Metodolojik not:** Viraj limiti kalibrasyonunda amaç "sınırı bulmak" değil, **modelin tahmin ettiği sınıra güvenli bir mesafeden yaklaşıp modelin tutarlılığını doğrulamaktır.** Gerçek devrilme/kayma sınırına ulaşılmayacaktır.

---

## 8. Sanal Dinamometre Protokolü

### 8.1 Yöntem

Tekerlek gücü, boyuna ivmeden ve direnç kuvvetlerinden hesaplanır:

```
F_tekerlek = m·a + F_yuvarlanma + F_aerodinamik + m·g·sin(eğim)

F_yuvarlanma = C_rr · m · g
F_aero = 0.5 · ρ · C_d · A · v²

P_tekerlek = F_tekerlek · v
T_motor = (F_tekerlek · r_tekerlek) / toplam_oran
```

### 8.2 Ölçüm Prosedürü

| Adım | İşlem |
|---|---|
| 1 | Düz, eğimsiz, boş bir yol kesimi seçilir (eğim GPS ile doğrulanır) |
| 2 | Motor çalışma sıcaklığına getirilir |
| 3 | Sabit vitesle (3. veya 4.) düşük devirden kırmızı bölgeye kadar tam gaz hızlanma |
| 4 | Aynı koşu **her iki yönde** tekrarlanır (rüzgar ve eğim etkisini iptal etmek için) |
| 5 | Minimum 5 tekrar |
| 6 | Aykırı değerler ayıklanır, ortalama alınır |

### 8.3 Katsayıların Belirlenmesi

**Yuvarlanma ve aerodinamik direnç — yavaşlama (coast-down) testi:**

Motor boşa alınır, belirli bir hızdan serbest yavaşlamaya bırakılır, hız-zaman eğrisi kaydedilir. Bu eğriye direnç modeli uydurularak C_rr ve C_d·A birlikte kestirilir.

| Parametre | Beklenen aralık (motosiklet) |
|---|---|
| C_rr | 0.012 - 0.020 |
| C_d · A | 0.35 - 0.60 m² (dik sürüş pozisyonu) |
| ρ (hava yoğunluğu) | Sıcaklık ve basınçtan hesaplanır |

Coast-down testi de her iki yönde yapılacak.

### 8.4 Doğrulama

| Ayak | Yöntem | Amaç |
|---|---|---|
| Tekrarlanabilirlik | Aynı koşulda 10 koşu, standart sapma | Ölçüm belirsizliği (hedef < %5) |
| Duyarlılık | Bilinen değişiklik (dişli oranı), beklenen vs ölçülen | Sistem değişimi doğru yakalıyor mu |
| Doğruluk | Gerçek dinamometre seansı | Mutlak hata yüzdesi |

**Beklenen değerler karşılaştırması:** Üretici 8500 rpm'de 18 kW ve 6250 rpm'de 23 N·m açıklıyor. Bunlar krank çıkışı değerlerdir; tekerlek gücü aktarma kayıpları nedeniyle tipik olarak **%8-15 daha düşük** çıkar. Ölçüm sonucunun bu aralıkta olması beklenir; dışında çıkarsa yöntem gözden geçirilecektir.

---

## 9. Asistan Profilleri (Araç Üzeri Davranış)

Motor parametreleri değiştirilmez; değişen şey ünitenin davranışıdır.

| Profil | Örnekleme | Gösterge | Uyarı eşiği | Sesli geri bildirim |
|---|---|---|---|---|
| Şehir | Düşük (10 Hz) | Sade: hız, vites, sıcaklık | Muhafazakâr | Minimum |
| Tur | Orta (20 Hz) | Menzil, tüketim, vites önerisi | Muhafazakâr | Yakıt ve mola uyarıları |
| Sportif | Yüksek (100 Hz) | Yatış açısı, ivme, tur süresi | Geç (deneyimli sürücü) | Sadece kritik |
| Eko | Düşük (10 Hz) | Anlık/ortalama tüketim, sürüş skoru | Muhafazakâr | Gaz ve vites koçluğu |

**Eko profil deneyi:** Aynı güzergâh, aynı koşullarda, eko profil açık ve kapalı olarak sürülür; tüketim farkı ölçülür. Bu, tezde ölçülebilir bir sonuç üretir.

---

## 10. Modifikasyon Deneyleri (Ölçüm Sistemi Duyarlılık Doğrulaması)

Bu deneylerin amacı performans artışı değil, **ölçüm sisteminin bilinen bir değişimi doğru yakaladığını göstermektir.**

### 10.1 Birincil Deney — Dişli Oranı Değişimi

| Öğe | Detay |
|---|---|
| Değişiklik | Ön dişli 1 diş küçültme (veya arka 2-3 diş büyütme) |
| Neden birincil | Beklenen sonuç **matematiksel olarak hesaplanabilir** |
| Beklenen etki | Tekerlek torku oranla artar, tepe hız aynı oranda düşer |
| Ölçüm | Öncesi/sonrası sanal dinamometre + 0-60 km/h süresi |
| Başarı kriteri | Ölçülen değişim, hesaplanan değişimle %5 içinde uyuşuyor |
| Maliyet | 300-600 TL |
| Geri alınabilir | Evet |

Örnek: Ön dişli 14T→13T ise oran değişimi 14/13 = 1.0769, yani tekerlek torkunda **%7.7 artış** beklenir. Cihaz bu değeri ölçebiliyorsa sistem doğrulanmış olur.

### 10.2 İkincil Deneyler

| Deney | Beklenen etki | Ölçülebilirlik | Geri alınabilir |
|---|---|---|---|
| Lastik basıncı değişimi | C_rr değişimi, coast-down eğrisi | Yüksek | Evet |
| Ek yük (sürücü + yolcu/bagaj) | Kütle artışı, ivme düşüşü | Yüksek | Evet |
| Hava filtresi kısmi tıkanma | Hacimsel verim düşüşü, yakıt trim sapması | Orta | Evet |
| Sürüş pozisyonu (dik/eğik) | C_d·A değişimi | Orta | Evet |
| Egzoz değişimi (varsa) | Küçük güç değişimi | Düşük | Evet |

**Not:** Hava filtresi ve emme kısıtlama deneyleri Faz 2'deki arıza tespiti çalışması için de veri üretir.

### 10.3 Yapılmayacak Modifikasyonlar

| Modifikasyon | Gerekçe |
|---|---|
| ECU yazılımı değişikliği | Yasal (tadilat), garanti, güvenlik riski; kazanç ~%3-5 |
| Piggyback / tuning box | Geniş bant lambda ve EGT olmadan körlemesine; motor hasarı riski |
| Emisyon sistemine müdahale | Yasal |
| Fren/süspansiyon güvenlik parçaları | Güvenlik; test aracının bütünlüğü korunmalı |
| Kalıcı tesisat kesme/lehim | Araç orijinal haline dönebilmeli |

---

## 11. Gerçek Dinamometre Referans Seansı

| Öğe | Detay |
|---|---|
| Amaç | Sanal dinamometrenin mutlak doğruluğunun belirlenmesi |
| Zamanlama | Ölçüm sistemi olgunlaştıktan sonra, tez yazımından önce |
| Süre | Yarım gün |
| Maliyet | 3000-6000 TL (ticari) |
| Alternatif | Üniversite makine mühendisliği motor test laboratuvarı (ücretsiz olabilir — **önce sorulacak**) |
| Prosedür | Aynı gün, aynı koşullarda hem dyno hem kendi sistemimizle ölçüm |
| Çıktı | Tork-devir ve güç-devir eğrisi karşılaştırması, hata yüzdesi |

**Not:** Dyno seansında motosikletin kendi verisi de kaydedilecek; bu veri HIL plant modelinin tork haritasını beslemek için kullanılacak.

---

## 12. Yasal ve Güvenlik Çerçevesi

### 12.1 Yasal Durum

| Faaliyet | Durum |
|---|---|
| Teşhis konnektöründen veri okuma | Sorunsuz — pasif dinleme |
| Ek elektronik ünite montajı (sökülebilir) | Sorunsuz |
| Dişli oranı değişimi | Yaygın uygulama; muayenede sorun beklenmiyor, yine de kayda alınacak |
| ECU yazılımı değişikliği | **Yapılmayacak** — ruhsat dışı tadilat kapsamına girebilir |
| Emisyon sistemine müdahale | **Yapılmayacak** |
| Aydınlatma/ek donanım | Yapılırsa mevzuata uygun olacak |

Muayene öncesi tüm ek donanım sökülebilir olmalıdır. Bu, tasarım gereksinimlerinden biridir.

### 12.2 Güvenlik Protokolü

**Her seans öncesi kontrol listesi:**

- [ ] Lastik basıncı kontrol edildi ve kaydedildi
- [ ] Fren ve zincir kontrol edildi
- [ ] Tüm montaj noktaları sıkılığı kontrol edildi (titreşim gevşetir)
- [ ] Kablolar hareketli parçalardan uzak, sıkışma yok
- [ ] Kayıt sistemi çalışıyor (seans öncesi doğrulandı)
- [ ] Koruyucu ekipman tam
- [ ] Hava ve yol koşulları uygun
- [ ] Yazılım sürümü daha önce düşük riskli ortamda test edildi

**Sürüş sırasında yasak:**

- Ekrana/telefona bakmak
- Kayıt durumunu kontrol etmek
- Yazılım hatası araştırmak
- Yeni yazılımı ilk kez yüksek hızda denemek

**Tasarım kuralı:** Ünitenin hiçbir arızası sürüşü etkilememelidir. Ünite tamamen çökse bile motosiklet normal çalışmaya devam etmelidir. Bu, bağlantı topolojisiyle garanti altına alınmıştır (pasif dinleme, orijinal tesisatta kesme yok).

---

## 13. Araç Üzeri Malzeme Listesi ve Maliyet

| Kalem | Amaç | Tahmini (TL) |
|---|---|---|
| ESP32-S3 (ana ünite) | İşlem birimi | 300-450 |
| CAN transceiver | Fiziksel katman | 80-150 |
| IMU (6/9 eksen) | Hareket verisi | 150-300 |
| GPS modülü + anten | Konum, hız, viraj yarıçapı | 250-450 |
| microSD kart + yuva | Kayıt | 150-250 |
| Güç devresi (buck, koruma, filtre) | Besleme | 200-350 |
| Akım/gerilim sensörü (INA226) | Güç izleme | 80-150 |
| OBD2/DLC Y kablo + konnektör | Bağlantı | 150-250 |
| Mikrofon + buton + hoparlör | Sesli komut | 250-450 |
| Muhafaza (IP54) | Koruma | 150-300 |
| Titreşim takozu, bağlantı elemanları | Montaj | 100-200 |
| Kablo, konnektör, spiral sargı, sigorta | Tesisat | 250-400 |
| PCB üretimi (ana ünite) | Kart | 400-700 |
| **Ara toplam (zorunlu)** | | **2510-4400** |
| Süspansiyon potansiyometreleri (ops.) | Enstrümantasyon | 300-600 |
| Sıcaklık sensörleri (ops.) | Termal analiz | 150-400 |
| Dişli (deney için) | Duyarlılık testi | 300-600 |
| **Ara toplam (opsiyonel)** | | **750-1600** |
| Dinamometre seansı | Doğruluk referansı | 0-6000 |
| Pist günü (opsiyonel) | Kontrollü veri | 0-3000 |
| **Genel toplam** | | **3260-15000** |

Geniş aralığın sebebi dyno ve pist kalemleridir. Üniversite imkanları kullanılabilirse alt banda yakın kalınır.

---

## 14. Araç Üzeri Çalışma Takvimi

| Hafta | Faaliyet |
|---|---|
| 1 | CAN bağlantısı, pasif dinleme, ilk ham kayıtlar |
| 2 | Sinyal haritası çıkarma (bölüm 5.5), OBD2 PID taraması |
| 3 | Geçici montaj (delikli plaket, kablo bağı), güç devresi testi |
| 4 | IMU hizalama ve kalibrasyon, T0 statik testler |
| 4+ | **Sürekli veri toplama başlar** |
| 5-6 | Araç parametrelerinin ölçümü (kütle, CG, tekerlek yarıçapı) |
| 6 | PCB siparişi verilir |
| 7-8 | T1 düşük hız testleri, hız/vites doğrulaması |
| 8-9 | Coast-down testleri, direnç katsayılarının belirlenmesi |
| 9-10 | Kalıcı montaj (PCB + muhafaza), T2/T3 yol testleri |
| 10-11 | Sanal dinamometre koşuları, tekrarlanabilirlik ölçümü |
| 11 | Dişli deneyi (duyarlılık doğrulaması) |
| 12 | T4 limit testleri (kapalı alan), viraj modülü kalibrasyonu |
| 12-13 | Dinamometre referans seansı (ayarlanabilirse) |
| 13 | Sesli komut saha testleri, eko profil karşılaştırma deneyi |
| 13-14 | Veri analizi, sonuçların raporlanması |

---

## 15. Riskler ve Önlemler

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| CAN mesajlarının anlamlandırılamaması | Orta | Yüksek | Standart OBD2 PID'leri taban alınır; ham mesaj çözümü opsiyonel |
| Titreşimden kaynaklı bağlantı arızası | Yüksek | Orta | Lehimli bağlantı, kablo bağı, düzenli kontrol; her seans öncesi kontrol listesi |
| Su/nem girişi | Orta | Yüksek | IP54 muhafaza, konnektör yönü aşağı, silikon conta |
| Isı kaynaklı arıza | Orta | Orta | Egzozdan uzak montaj, iç sıcaklık izleme |
| Ateşleme gürültüsü veri bozulması | Orta | Orta | Ekranlı kablo, filtreleme, motor açık/kapalı karşılaştırma testi |
| Veri kaybı (kart bozulması, kesinti) | Orta | Çok yüksek | CRC'li blok yapısı, her seans sonrası çift yedekleme |
| Test sırasında kaza/yaralanma | Düşük | Çok yüksek | Kademeli yaklaşım, kapalı alan, koruyucu ekipman, güvenlik protokolü |
| Motosikletin arızalanması (proje aracı) | Düşük | Yüksek | Düzenli bakım, geri alınamaz modifikasyon yok |
| Hava koşulları nedeniyle takvim kayması | Yüksek | Orta | Kış aylarında T0/T1 testlerine ağırlık, yol testleri esnek planlanır |
| Dyno seansı ayarlanamaması | Orta | Orta | Üniversite laboratuvarı alternatifi; olmazsa belirsizlik analizi ile yetinilir ve tezde belirtilir |

---

## 16. Çıktılar

Bu çalışma planının sonunda elde edilecekler:

1. Araca monte edilmiş, çalışır durumda ünite (sökülebilir)
2. CL250 sinyal tanım dosyası (HIL tezgahının araç tanımı)
3. Ölçülmüş araç parametre seti (kütle, CG, tekerlek yarıçapı, direnç katsayıları)
4. Minimum 40 saat etiketli sürüş verisi
5. Sanal dinamometre tork/güç eğrileri ve belirsizlik analizi
6. Dişli deneyi duyarlılık raporu
7. Dinamometre karşılaştırma raporu (seans yapılabilirse)
8. Sesli komut tanıma oranının hıza göre değişim grafiği
9. Eko profil tüketim karşılaştırma sonucu
10. Viraj güvenlik modülü kalibrasyon verisi
11. Saha test raporları ve video kayıtları
