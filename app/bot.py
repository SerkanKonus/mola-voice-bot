#!/usr/bin/env python3
import sys
import os
import requests
import time
import uuid
import asyncio
import edge_tts
import re

# --- AYARLAR ---
WHISPER_URL = "http://127.0.0.1:8000/v1/audio/transcriptions"
RASA_URL = "http://127.0.0.1:5005/webhooks/rest/webhook"
BASE_SOUNDS_DIR = "/var/lib/asterisk/sounds"
CUSTOM_DIR_NAME = "custom"
FULL_RECORD_DIR = os.path.join(BASE_SOUNDS_DIR, CUSTOM_DIR_NAME)
ELEVENLABS_API_KEY = "sk_fa16387fdcd08cc5a2a8c56324020b288e57ff8aff1e8790"
VOICE_ID = "axtmxCPnqPghs9C5SjJ8"

def num_to_tr_text(text):
    """Metin içindeki sayıları Türkçe okunuşlarına çevirir."""
    units = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    tens = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
    thousands = ["", "bin", "milyon", "milyar"]

    def convert_group(n):
        res = ""
        h = n // 100
        t = (n % 100) // 10
        u = n % 10
        if h > 0:
            res += (units[h] if h > 1 else "") + "yüz "
        if t > 0:
            res += tens[t] + " "
        if u > 0:
            res += units[u] + " "
        return res

    def number_to_words(n):
        if n == 0: return "sıfır"
        if n < 0: return "eksi " + number_to_words(abs(n))
        res = ""
        group_idx = 0
        while n > 0:
            group = n % 1000
            if group > 0:
                group_text = convert_group(group)
                if group_idx == 1 and group == 1: # "bir bin" yerine "bin"
                    res = "bin " + res
                else:
                    res = group_text + thousands[group_idx] + " " + res
            n //= 1000
            group_idx += 1
        return res.strip()

    # Metin içindeki sayıları bul ve değiştir
    import re
    return re.sub(r'\d+', lambda x: number_to_words(int(x.group())), text)

def log(msg):
    sys.stderr.write(f"[BOT] {msg}\n")
    sys.stderr.flush()

def agi_cmd(cmd):
    sys.stdout.write(cmd + "\n")
    sys.stdout.flush()
    result = sys.stdin.readline().strip()
    return result

def text_to_speech(text):
    if not text:
        return None
    
    # Akıcılık için sadece basit temizlik yapıyoruz
    # Noktaları kısa bir es için virgüle çeviriyoruz, diğerlerini siliyoruz
    clean_text = text.replace(".", ",").replace("!", "").replace("?", "")
    clean_text = re.sub(r',+', ',', clean_text)
    
    log(f"🗣️ Okunuyor: {clean_text}")
    
    filename_base = f"tts_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    filepath_mp3 = os.path.join(FULL_RECORD_DIR, f"{filename_base}.mp3")
    filepath_wav = os.path.join(FULL_RECORD_DIR, f"{filename_base}.wav")
    
    try:
        async def generate():
            # SSML etiketlerini sildik, onun yerine parametreleri kullandık.
            # Bu yöntem SSML ile aynı kaliteyi verir ama etiket okuma hatasını engeller.
            communicate = edge_tts.Communicate(
                text=clean_text, 
                voice="tr-TR-EmelNeural",
                rate="+12%",    # Konuşma hızı (akıcılık için)
                pitch="-1Hz"    # Ses perdesi (daha doğal bir ton için)
            )
            await communicate.save(filepath_mp3)
        
        asyncio.run(generate())

        # FFmpeg ile sessizlik budama (akışkanlık için en önemli adım burası)
        convert_cmd = (
            f"ffmpeg -i {filepath_mp3} -ar 8000 -ac 1 "
            f"-af \"volume=1.5\" "
            f"-y {filepath_wav} > /dev/null 2>&1"
        )
        ret = os.system(convert_cmd)
        if ret != 0:
            log(f"❌ FFmpeg Hatası! Dönüş kodu: {ret}")
            log(f"Komut: {convert_cmd}")
        
        if os.path.exists(filepath_mp3):
            os.remove(filepath_mp3)

        if os.path.exists(filepath_wav):
            log(f"✅ Ses dosyası oluşturuldu: {filename_base}.wav")
            return f"{CUSTOM_DIR_NAME}/{filename_base}"
        else:
            log(f"❌ Ses dosyası OLUŞMADI: {filename_base}.wav")
        return None

    except Exception as e:
        log(f"❌ TTS Hatası: {e}")
        return None

def record_audio(filename):
    log("🎤 Dinliyorum...")
    os.makedirs(FULL_RECORD_DIR, exist_ok=True)
    file_path_no_ext = os.path.join(FULL_RECORD_DIR, filename)
    cmd = f"RECORD FILE {file_path_no_ext} wav # 4000 0 s=0.6"
    result = agi_cmd(cmd)
    if "result=-1" in result:
        return None
    wav_path = f"{file_path_no_ext}.wav"
    return wav_path if os.path.exists(wav_path) else None

def speech_to_text(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            data = {'model': 'base', 'language': 'tr', 'response_format': 'json'}
            r = requests.post(WHISPER_URL, files=files, data=data, timeout=60)
        if r.status_code == 200:
            text = r.json().get("text", "").strip()
            if text.lower() in ["altyazı", "altyazılar", "subtitle", "transcription"]:
                return None
            return text
    except Exception as e:
        log(f"❌ Whisper Hatası: {e}")
    return None

def get_bot_response(text):
    try:
        r = requests.post(RASA_URL, json={"sender": "user", "message": text}, timeout=30)
        if r.status_code == 200:
            responses = r.json()
            if responses:
                return responses[0].get("text", "")
    except Exception as e:
        log(f"❌ Rasa Hatası: {e}")
    return "Şu an cevap veremiyorum."

# --- AGI BAŞLANGICI ---
env = {}
while True:
    line = sys.stdin.readline().strip()
    if line == '': break
    if ':' in line:
        key, val = line.split(':', 1)
        env[key] = val.strip()

log("🤖 Bot Başlatıldı (Fix)")
agi_cmd("ANSWER")
time.sleep(0.5)

for i in range(15):
    unique_id = int(time.time())
    wav_file = record_audio(f"rec_{unique_id}")
    if not wav_file: continue
    text = speech_to_text(wav_file)
    if not text or len(text) < 2: continue
    log(f"📝 Algılanan: {text}")
    if any(word in text.lower() for word in ["kapat", "bay bay", "görüşürüz", "sonlandır"]):
        bye_path = text_to_speech("Bizi tercih ettiğiniz için teşekkürler, iyi günler dilerim.")
        if bye_path:
            agi_cmd(f"STREAM FILE {bye_path} \"\"")
        break
    response_text = get_bot_response(text)
    log(f"🤖 Bot: {response_text}")
    audio_response = text_to_speech(response_text)
    if audio_response:
        log(f"🔊 Oynatılıyor (Dosya): {audio_response}")
        agi_cmd(f"STREAM FILE {audio_response} \"\"")
    else:
        log(f"⚠️ Dosya yok, heceleniyor (SAY ALPHA): {response_text}")
        agi_cmd(f"SAY ALPHA \"{response_text}\" \"\"")

log("🛑 Görüşme Sonlandı.")
agi_cmd("HANGUP")
