import re
import random
import requests
import json
import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime, timedelta

# ================== API ENDPOINTS ==================
BOARD_TYPES_API = "https://molaistanbul.com/apigw/file-service/redirect/board-types"
ROOM_TYPES_API = "https://molaistanbul.com/apigw/file-service/redirect/room-types"
PRICE_API = "https://molaistanbul.com/apigw/reservation-service/redirect/SP_PORTALV4_HOTELDETAILPRICE"
DAILY_PRICE_API = "https://molaistanbul.com/apigw/payment-service/daily-prices/calculate-total-daily-price"

# ================== SSS DATABASE ==================
FAQ_DB_PATH = os.path.join(os.path.dirname(__file__), "../data/faq_database.json")

def load_faq_database():
    """Load FAQ database from JSON file"""
    try:
        with open(FAQ_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

# ================== UTILITY FUNCTIONS ==================
def num_to_turkish_text(number):
    """Convert numbers to Turkish text (12500 -> 'on iki bin beş yüz')"""
    if not isinstance(number, (int, float)):
        return str(number)
    
    num = int(number)
    if num == 0:
        return "sıfır"
    
    units = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    tens = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
    
    def convert_group(n):
        if n == 0:
            return ""
        result = ""
        hundreds = n // 100
        remainder = n % 100
        tens_digit = remainder // 10
        units_digit = remainder % 10
        
        if hundreds > 0:
            if hundreds == 1:
                result += "yüz "
            else:
                result += units[hundreds] + " yüz "
        
        if tens_digit > 0:
            result += tens[tens_digit] + " "
        
        if units_digit > 0:
            result += units[units_digit] + " "
        
        return result.strip()
    
    if num < 1000:
        return convert_group(num)
    elif num < 1000000:
        thousands = num // 1000
        remainder = num % 1000
        result = ""
        if thousands == 1:
            result = "bin"
        else:
            result = convert_group(thousands) + " bin"
        if remainder > 0:
            result += " " + convert_group(remainder)
        return result.strip()
    else:
        return str(num)  # Fallback for very large numbers

def format_price_turkish(price):
    """Format price with Turkish text (9026.32 -> 'dokuz bin yirmi altı lira')"""
    try:
        price_int = int(float(price))
        return num_to_turkish_text(price_int) + " lira"
    except:
        return str(price) + " lira"

# ================== FORM VALIDATION ==================
class ValidateFiyatForm(FormValidationAction):
    """Validate fiyat form slots"""
    
    def name(self) -> Text:
        return "validate_fiyat_form"
    
    async def validate_tarih_baslangic(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate tarih slot"""
        # Simple validation - accept any text for now
        # TODO: Add date parsing and validation
        if slot_value:
            return {"tarih_baslangic": slot_value}
        return {"tarih_baslangic": None}
    
    async def validate_kisi_sayisi(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate kisi_sayisi slot"""
        # Extract number from text
        if slot_value:
            # Try to extract number
            import re
            numbers = re.findall(r'\d+', str(slot_value))
            if numbers:
                return {"kisi_sayisi": numbers[0]}
            return {"kisi_sayisi": slot_value}
        return {"kisi_sayisi": None}

# ================== QUICK PRICE CHECK ==================
class ActionQuickPriceCheck(Action):
    """Quick price check using real API"""
    
    def name(self) -> Text:
        return "action_quick_price_check"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Dolgu ifadesi
        filler = random.choice(["Bir bakayım...", "Hemen kontrol ediyorum...", "Şimdi sistemden bakıyorum..."])
        dispatcher.utter_message(text=filler)
        
        # Get slots
        tarih = tracker.get_slot("tarih_baslangic")
        kisi = tracker.get_slot("kisi_sayisi")
        cocuk_yaslari = tracker.get_slot("cocuk_yaslari") or []
        
        # Check if we have required information
        if not tarih:
            dispatcher.utter_message(response="utter_ask_tarih_baslangic")
            return []
        
        if not kisi:
            dispatcher.utter_message(response="utter_ask_kisi_sayisi")
            return []
        
        try:
            # TODO: Parse date properly - for now use a default
            # This needs proper date parsing logic
            checkin = "2026-01-15"  # Placeholder
            checkout = "2026-01-16"  # Placeholder
            
            # Prepare API payload
            payload = {
                "Parameters": {
                    "IPCOUNTRY": None,
                    "PORTALSELLERID": None,
                    "VPNFLAG": None,
                    "POSID": None,
                    "INSTALLMENT": None,
                    "RATETYPEID": None,
                    "BOARDTYPEID": None,
                    "ROOMCOUNT": None,
                    "GROUPHOTEL": None,
                    "BOOKINGHOTELID": None,
                    "ROOMTYPEGROUPID": None,
                    "PORTALID": 1,
                    "LANGUAGE": "tr",
                    "IPADDRESS": "",
                    "GUESTID": None,
                    "HOTELID": 33514,
                    "CHECKIN": checkin,
                    "CHECKOUT": checkout,
                    "ADULT": int(kisi) if str(kisi).isdigit() else 1,
                    "CHILDAGES": "",  # CSV format if needed
                    "PROMOCODE": "",
                    "SESSION": None,
                    "COUNTRYCODE": None,
                    "ROOMTYPEID": None,
                    "CURRENCY": "TRY"
                },
                "Action": "Execute",
                "Object": "SP_PORTALV4_HOTELDETAILPRICE"
            }
            
            # Call API
            response = requests.post(PRICE_API, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and len(data[0]) > 0:
                    # Get first offer
                    offer = data[0][0]
                    price = offer.get("Price", 0)
                    room_type = offer.get("RoomType", "")
                    board_type = offer.get("BoardType", "")
                    
                    # Format response
                    price_text = format_price_turkish(price)
                    response_text = f"{tarih} için {kisi} kişi, {room_type}, {board_type} seçeneği {price_text}. Devam edelim mi?"
                    dispatcher.utter_message(text=response_text)
                    return [SlotSet("conversation_stage", "fiyat_verildi")]
                else:
                    dispatcher.utter_message(text="Maalesef bu tarihler için müsaitlik bulamadım. Başka tarih deneyelim mi?")
            else:
                raise Exception("API error")
        
        except Exception as e:
            # Fallback response
            dispatcher.utter_message(text="Üzgünüm, şu an fiyat sistemine ulaşamıyorum. Bir saniye sonra tekrar deneyelim mi?")
            print(f"Price API error: {e}")
        
        return []

# ================== FAQ SEARCH ==================
class ActionSearchFAQ(Action):
    """Search FAQ database for quick answers"""
    
    def name(self) -> Text:
        return "action_search_faq"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get last message
        last_message = tracker.latest_message.get('text', '').lower()
        
        # Load FAQ database
        faq_db = load_faq_database()
        
        # Search in FAQ
        best_match = None
        max_score = 0
        
        for category in faq_db.values():
            for item_key, item in category.items():
                if "anahtar_kelimeler" in item and "cevap" in item:
                    # Check if any keyword matches
                    score = sum(1 for keyword in item["anahtar_kelimeler"] 
                               if keyword.lower() in last_message)
                    if score > max_score:
                        max_score = score
                        best_match = item["cevap"]
        
        if best_match:
            dispatcher.utter_message(text=best_match)
        else:
            # Fallback to generic response
            dispatcher.utter_message(text="Tesisimizle ilgili tüm detaylara hakimim, tam olarak neyi merak etmiştiniz?")
        
        return []

# ================== BOARD TYPE COMPARISON ==================
class ActionGetBoardComparison(Action):
    """Compare board types (pansiyon)"""
    
    def name(self) -> Text:
        return "action_get_board_comparison"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            response = requests.get(BOARD_TYPES_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 200 and data.get("data"):
                    board_types = data["data"]
                    
                    # Format response
                    response_parts = ["Pansiyon seçeneklerimiz:"]
                    for board in board_types[:4]:  # Limit to top 4
                        name = board.get("name", "")
                        desc = board.get("description", "")
                        response_parts.append(f"{name}: {desc}")
                    
                    # Keep it short - only first 2
                    short_response = f"{board_types[0]['name']} ve {board_types[1]['name']} seçeneklerimiz var. Hangisini tercih edersiniz?"
                    dispatcher.utter_message(text=short_response)
                    return []
        except Exception as e:
            print(f"Board types API error: {e}")
        
        # Fallback
        dispatcher.utter_message(text="Sadece Oda, Oda Kahvaltı ve Yarım Pansiyon seçeneklerimiz var. Hangisini istersiniz?")
        return []

# ================== ROOM TYPES ==================
class ActionGetRoomTypes(Action):
    """Get room types from API"""
    
    def name(self) -> Text:
        return "action_get_room_types"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            response = requests.get(ROOM_TYPES_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 200 and data.get("data"):
                    rooms = data["data"]
                    
                    # Create short summary
                    room_names = [room.get("roomName", "") for room in rooms[:4]]
                    response_text = f"Oda tiplerimiz: {', '.join(room_names)}. Hangisini merak ediyorsunuz?"
                    dispatcher.utter_message(text=response_text)
                    return []
        except Exception as e:
            print(f"Room types API error: {e}")
        
        # Fallback
        dispatcher.utter_message(text="Deluxe, Executive, Premium ve Superior odalarımız var. Hangisi ilginizi çeker?")
        return []

# ================== REZERVASYON ONAY ==================
class ActionRezervasyonOnay(Action):
    """Reservation confirmation summary"""
    
    def name(self) -> Text:
        return "action_rezervasyon_onay"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get all slots
        tarih = tracker.get_slot("tarih_baslangic")
        kisi = tracker.get_slot("kisi_sayisi")
        oda_tipi = tracker.get_slot("oda_tipi")
        pansiyon = tracker.get_slot("pansiyon_tipi")
        
        summary = f"Özet: {tarih} tarihinde {kisi} kişi için rezervasyon. "
        if oda_tipi:
            summary += f"Oda tipi: {oda_tipi}. "
        if pansiyon:
            summary += f"Pansiyon: {pansiyon}. "
        
        summary += "Onaylıyor musunuz?"
        
        dispatcher.utter_message(text=summary)
        return []

# ================== LEGACY ACTIONS (Compatibility) ==================
class ActionFiyatSorgula(Action):
    """Legacy action - redirects to form"""
    def name(self) -> Text:
        return "action_fiyat_sorgula"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Redirect to quick price check
        return []

class ActionEtkinlikSorgula(Action):
    """Legacy action for events"""
    def name(self) -> Text:
        return "action_etkinlik_sorgula"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Etkinlik takvimimize bakıyorum...")
        # TODO: Implement events API
        dispatcher.utter_message(text="Bu hafta canlı müzik performanslarımız var. Detaylı bilgi için tesise geldikten sonra öğrenebilirsiniz.")
        return []

class ActionSSSYanitla(Action):
    """Legacy SSS action - redirects to search_faq"""
    def name(self) -> Text:
        return "action_sss_yanitla"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Call search_faq
        action = ActionSearchFAQ()
        return action.run(dispatcher, tracker, domain)
