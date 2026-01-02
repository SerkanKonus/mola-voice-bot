import re
import random
import requests
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# MCP Server veya API URL'niz (Örnek)
MCP_API_URL = "http://localhost:5000" 

class ActionFiyatSorgula(Action):
    def name(self) -> Text:
        return "action_fiyat_sorgula"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # 1. KURAL: Tool çağrısı öncesi kısa dolgu ifadesi
        filler_messages = ["Hmmm, bir bakayım...", "Hemen kontrol ediyorum...", "Şimdi sistemden bakıyorum..."]
        dispatcher.utter_message(text=random.choice(filler_messages))

        # Slotları al
        tarih = tracker.get_slot("tarih")
        kisi = tracker.get_slot("kisi_sayisi")
        cocuk_yaslari = tracker.get_slot("cocuk_yaslari")

        # 2. KURAL: Eksik bilgi toplama akışı
        if not tarih:
            dispatcher.utter_message(text="Fiyatlarımız tarihe göre değişiyor. Hangi tarih aralığını düşünüyorsunuz?")
            return []
        
        if not kisi:
            dispatcher.utter_message(text="Kaç yetişkin konaklayacaksınız?")
            return []

        # Eğer çocuk varsa ve yaşları alınmamışsa (Senaryo gereği)
        # Not: NLU'da 'çocuk var' bilgisi algılandığında bu tetiklenir
        has_child = tracker.get_slot("has_child")
        if has_child and not cocuk_yaslari:
            dispatcher.utter_message(text="Çocukların yaşlarını yıl olarak paylaşır mısınız?")
            return []

        # 3. KURAL: Tool Çağrısı (quick_price_check)
        try:
            # Burada gerçek MCP server'ına veya ilgili fonksiyonuna istek atıyorsun
            # payload = {"startDate": tarih, "adults": kisi, "childAges": cocuk_yaslari}
            # response = requests.post(f"{MCP_API_URL}/quick_price_check", json=payload)
            # data = response.json()
            
            # Örnek Tool Çıktısı (Simülasyon)
            fiyat_ozet = "15-18 Ocak arası 2 kişi için en uygun seçenek 12.500 TL, oda kahvaltı dahil."
            
            # 4. KURAL: Satışçı gibi cevapla ve TEK SORU sor
            dispatcher.utter_message(text=f"{fiyat_ozet} Devam edelim mi?")
            
        except Exception as e:
            dispatcher.utter_message(text="Üzgünüm, şu an fiyat sistemine ulaşamıyorum. Bir saniye sonra tekrar deneyelim mi?")
        
        return []

class ActionEtkinlikSorgula(Action):
    def name(self) -> Text:
        return "action_etkinlik_sorgula"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hemen etkinlik takvimimize bakıyorum...")

        # info(service="concert") çağrısı simülasyonu
        etkinlikler = ["Tarkan Konseri (20 Ocak)", "Sıla Konseri (22 Ocak)"]
        
        msg = f"Bu hafta harika programlarımız var: {', '.join(etkinlikler)}. Hangisinin detayını istersiniz?"
        dispatcher.utter_message(text=msg)
        
        return []

class ActionSSSYanitla(Action):
    def name(self) -> Text:
        return "action_sss_yanitla"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Kullanıcının ne sorduğunu metinden anla (Entity kaçsa bile çalışır)
        last_message = tracker.latest_message.get('text', '').lower()

        if "saat" in last_message or "giriş" in last_message:
            dispatcher.utter_message(text="Giriş sabah 09:00, çıkış ertesi gün 23:00'e kadar. Oldukça esnek bir vaktimiz var!")
        elif "hayvan" in last_message or "köpek" in last_message:
            dispatcher.utter_message(text="Maalesef evcil hayvan kabul edemiyoruz efendim. Başka bir sorunuz var mı?")
        else:
            dispatcher.utter_message(text="Tesisimizle ilgili tüm detaylara hakimim, tam olarak neyi merak etmiştiniz?")

        return []
