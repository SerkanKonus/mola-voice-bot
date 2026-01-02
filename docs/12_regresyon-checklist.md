# Regresyon Checklist (Satış Asistanı)

Bu liste, konuşma akışı güncellemelerinden sonra hızlı manuel kontrol içindir.

## 1) Rezervasyona zorlamama (bilgi sorusu varken)
- **Girdi**: Kullanıcı “Aquapark var mı? Kadın/erkek ayrı mı?” gibi bir soru sorar.
- **Beklenen**:
  - Asistan soruyu cevaplar (gerekirse `docs` ile doğrular).
  - “Yoksa rezervasyona geçelim mi?” gibi kalıpları art arda tekrarlamaz.
  - En sonda en fazla 1 kez düşük baskılı teklif: “İsterseniz müsaitlik ve fiyat için tarih aralığınızı alabilirim.” ve tek soru.

## 2) Wellness altında havuz/alanları gerçekten kontrol etme
- **Girdi**: Kullanıcı “Wellness hizmetlerine bakar mısın? SPA’da hangi alanlar var, havuz var mı?” der.
- **Beklenen**:
  - Asistan `docs/04_spa-ve-wellness.md` üzerinden alanları doğru özetler (kadın/erkek ayrı alanlar ve havuzlar dahil).
  - Kullanıcı “güncel liste / isim isim” isterse `info` (`service: wellnes/wellness/spa`) ile başlıkları getirip seçtirir.

## 3) Pansiyon seçeneklerinde yarım pansiyonun sunulması
- **Girdi**: Kullanıcı rezervasyon ister; kişi/tarih netleştikten sonra pansiyon sorusu gelir.
- **Beklenen**:
  - Asistan “Sadece Oda / Oda Kahvaltı / Yarım Pansiyon” seçeneklerini sunar.
  - “Ne farkı var?” sorusuna kısa açıklama yapar.

## 4) Tarih guard (geçmiş tarih üretmeme)
- **Girdi**: Kullanıcı yıl belirtmeden geçmişe düşen bir tarih söyler (örn. “11 Ekim giriş” ama bugün Aralık).
- **Beklenen**:
  - Asistan rezervasyon/fiyat konuşmasının başında `get_current_datetime` ile bugünü baz alır.
  - Geçmiş tarih üretmez; “Bu tarih bu yıl geçti; 2026 mı düşünmüştünüz?” gibi tek bir netleştirme sorusu sorar.

## 5) Havuz/aquapark operasyonel doğrulama
- **Girdi**: Kullanıcı “Kadın havuzu görünüyor mu?”, “Aquapark karma mı?” gibi operasyonel SSS sorar.
- **Beklenen**:
  - Asistan `docs/09_operasyonel-bilgiler-ve-sss.md` ile doğrular, doğru yanıt verir.


