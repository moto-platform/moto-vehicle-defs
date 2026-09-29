# CLAUDE.md — [[REPO-ADI]]

## Bu repo ne

[[Tek-iki cümlede: bu repo hangi fiziksel birimde koşuyor (çip/Raspi/sunucu/telefon), ana sorumluluğu ne. Örnek doldurma rehberi aşağıda.]]

## Bu repo NE DEĞİL (kapsam sınırı)

[[Bu reponun YAPMAMASI gereken, ama karışabilecek işleri listele. Örnek: moto-linux-node için "UDS/bootloader burada değil, moto-rt-core'da" gibi.]]

## Bağımlılık

`moto-vehicle-defs`'ten sinyal tanımlarını okur (submodule: `[[VEHICLE-DEFS-PATH]]`).
[[Varsa diğer repo bağımlılıkları: örn. moto-ml → moto-server'dan veri okur.]]

## Derleme/çalıştırma

[[Bu reponun araç zincirini buraya yaz — dil/framework'e göre değişir.]]

## Bağlam

Tam mimari: `[[MIMARI-DOKUMAN-PATH]]` — [[ilgili bölüm numarasını yaz]].

---

## Doldururken referans alacağın repo-özel notlar (mimari dokümandan çıkarıldı)

### moto-safety-node (STM32 G4/F3)
- TEK işi: viraj güvenlik izleme — **deterministik karar katmanı burada** (kapalı form: v_max=√(µgR)). Başka HİÇBİR modül burada koşmaz — izolasyon amacı bu.
- Girdisini (yatış açısı, µ, kütle) `moto-rt-core`'un EKF'inden CAN üzerinden alır — kendi EKF'ini tekrar hesaplamaz.
- `moto-rt-core`'un çökmesi/gecikmesi bu düğümün karar VERMESİNİ etkilememeli; ama veri gecikirse/kesilirse ne olacağı (kendi minimal sensörle devam / düşük-güven uyarı durumuna geçme) **açık karar** — donanımı netleşince çözülecek.

### moto-io-node (STM32 G0/F0)
- Kör nokta (radar+LED) + immobilizer + güç yönetimi — BİRLEŞİK zone-controller, ayrı ayrı çip değil.
- İmmobilizer: SADECE marş rölesi bobin devresi. Ateşleme/yakıt pompası/ECU hattına ASLA dokunma.
- Fail-safe: varsayılan konum AÇIK, gizli mekanik bypass, 10sn zaman aşımı.

### moto-linux-node (Raspi 5, Python/C++)
- Kuksa Databroker + CAN köprüsü (VSS) — bu katman önce kurulur, gerisi onun üstüne oturur.
- Şerit takip: KLASİK CV (OpenCV), derin öğrenme DEĞİL — eğitim verisi gerektirmiyor, bilinçli seçim.
- Anomali modeli (birleşik, çok modaliteli) burada — ama `moto-rt-core`'daki `anomaly-safety-net` kural tabanlı yedeği BOZMA.
- Zengin akustik/ağır model periyodik pencere analiziyle koşar, sürekli tam hızda DEĞİL (Raspi kapasite bütçesi).
- Kanto (konteyner OTA) MVP'de YOK — basit Linux process yeterli.

### moto-server (Python/Go)
- InfluxDB+Grafana (zaman serisi) veya basit dosya+Python ile başla, büyürse ölçekle.
- MDF4 formatına dönüşüm burada yapılır (araçta değil).

### moto-ml (Python, offline)
- Eğitim burada, ÇIKARIM burada DEĞİL (çıkarım ilgili düğümün `features/` klasöründe).
- CWRU/MaFaulDa/MIMII gibi açık veri setleri metodoloji referansı, doğrudan eğitim verisi DEĞİL (domain gap).
- Eğitim/test ayrımı SEANS bazlı yapılmalı — aksi halde yanıltıcı yüksek doğruluk.

### moto-mobile (Flutter/RN)
- Companion — kritik hiçbir işe karışmaz, gevşek bağlı. Sistem telefonsuz tam çalışmalı.

### moto-mcp (Python, bağımsız açık kaynak repo)
- Aynı Raspi'de koşsa da BAĞIMSIZ repo (paylaşım/vitrin amacı).
- Araç (tool) listesi: `get_live_snapshot`, `get_recent_stats`, `get_event_log`, `get_anomaly_status`, `get_maintenance_status`, `query_ride_history`.
- LLM kendi matematiğini YAPMAZ — sadece hazır hesaplanmış sonucu anlatır (OVMS projesinin uyarısı).
- GPS ham konumu bulut LLM'e gönderilmez.
