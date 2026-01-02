#!/usr/bin/env python3
import sys
import os
import requests
import time
import uuid
import asyncio
import edge_tts
import re
from gtts import gTTS

# --- AYARLAR ---
#WHISPER_URL = "http://127.0.0.1:9000/asr"
WHISPER_URL = "http://127.0.0.1:8000/v1/audio/transcriptions"
RASA_URL = "http://127.0.0.1:5005/webhooks/rest/webhook"
# Asterisk'in ses dosyalarını aradığı ana dizin
BASE_SOUNDS_DIR = "/var/lib/asterisk/sounds"
# Bizim dosyaları koyduğumuz alt klasör
CUSTOM_DIR_NAME = "custom"
FULL_RECORD_DIR = os.path.join(BASE_SOUNDS_DIR, CUSTOM_DIR_NAME)

def log(msg):
    sys.stderr.write(f"[BOT] {msg}\n")
    sys.stderr.flush()

def agi_cmd(cmd):
    sys.stdout.write(cmd + "\n")
    sys.stdout.flush()
    result = sys.stdin.readline().strip()
    return result

def text_to_speech(text):
    if not text: return None
    
    # 1. RADİKAL TEMİZLİK: Sadece harfleri ve boşlukları bırakır
    # Nokta, virgül, soru işareti, ünlem ne varsa süpürür
    clean_text = re.sub(r'[^\w\s]', '', text) 
    
    log(f"🗣️ Temiz Metin Okunuyor: {clean_text}") # Logdan kontrol et

    filename_base = f"tts_{uuid.uuid4().hex[:6]}"
    filepath_mp3 = os.path.join(FULL_RECORD_DIR, f"{filename_base}.mp3")
    filepath_wav = os.path.join(FULL_RECORD_DIR, f"{filename_base}.wav")

    async def generate():
        # RATE +20%: Kelime arası boşlukları iyice daraltır
        # PITCH -3Hz: Sesi daha doğal ve oturaklı yapar
        communicate = edge_tts.Communicate(
            clean_text, 
            "tr-TR-EmelNeural", 
            rate="+20%", 
            pitch="-3Hz"
        )
        await communicate.save(filepath_mp3)

    import asyncio
    asyncio.run(generate())

    # 2. FFmpeg Optimizasyonu (Kritik)
    # 'window=0' ve 'stop_duration=0' ile sessizliği hiç affetmiyoruz
    convert_cmd = (
        f"ffmpeg -i {filepath_mp3} -ar 8000 -ac 1 "
        f"-af \"silenceremove=start_threshold=-55dB:start_duration=0:stop_threshold=-55dB:stop_duration=0:window=0,atempo=1.02,volume=1.5\" "
        f"-y {filepath_wav} > /dev/null 2>&1"
    )
    os.system(convert_cmd)
    
    if os.path.exists(filepath_mp3): os.remove(filepath_mp3)
    return f"{CUSTOM_DIR_NAME}/{filename_base}"

def record_audio(filename):
    log("🎤 Dinliyorum... (Konuşun)")
    os.makedirs(FULL_RECORD_DIR, exist_ok=True)
    
    # Kayıt için tam yol veriyoruz (Asterisk kayıtta tam yolu sever)
    file_path_no_ext = os.path.join(FULL_RECORD_DIR, filename)
    
    # 5 saniye bekle, 2 saniye sessizlikte kes
    cmd = f"RECORD FILE {file_path_no_ext} wav # 4000 0 s=0.2"
    result = agi_cmd(cmd)
    
    if "result=-1" in result:
        return None

    wav_path = f"{file_path_no_ext}.wav"
    if os.path.exists(wav_path):
        return wav_path
    return None

def speech_to_text(filepath):
    log(f"🔊 Whisper'a gönderiliyor (Faster)...")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            # Faster-Whisper OpenAI API formatı ister:
            # model="base" (veya ne kurduysan), file=dosya
            files = {
                'file': ('audio.wav', f, 'audio/wav')
            }
            data = {
                'model': 'base',
                'language': 'tr',
                'response_format': 'json'
            }
            
            # Post isteği
            r = requests.post(WHISPER_URL, files=files, data=data, timeout=10)
            
        if r.status_code == 200:
            return r.json().get("text", "").strip()
        else:
            log(f"❌ Whisper HTTP Hata: {r.status_code} - {r.text}")
            return None
            
    except Exception as e:
        log(f"❌ Whisper Hatası: {e}")
    return None

def get_bot_response(text):
    log(f"🧠 Rasa'ya soruluyor: {text}")
    try:
        r = requests.post(RASA_URL, json={"sender": "user", "message": text}, timeout=10)
        if r.status_code == 200:
            responses = r.json()
            if responses:
                return responses[0].get("text", "")
    except Exception as e:
        log(f"❌ Rasa Hatası: {e}")
    return "Şu an cevap veremiyorum."

# --- ANA DÖNGÜ ---
env = {}
while True:
    line = sys.stdin.readline().strip()
    if line == '': break
    if ':' in line:
        key, val = line.split(':', 1)
        env[key] = val.strip()

log("🤖 Bot Başlatıldı (Google TTS - Final Fix)")
agi_cmd("ANSWER")
time.sleep(0.3)

for i in range(10): 
    unique_id = int(time.time())
    
    # 1. Kayıt
    wav_file = record_audio(f"rec_{unique_id}")
    if not wav_file:
        continue

    # 2. STT
    text = speech_to_text(wav_file)
    if not text or len(text) < 2:
        log("Ses anlaşılamadı.")
        continue
    
    log(f"📝 Algılanan: {text}")

    if any(word in text.lower() for word in ["kapat", "bay", "görüşürüz"]):
        bye_path = text_to_speech("Görüşmek üzere.")
        if bye_path:
            agi_cmd(f"STREAM FILE {bye_path} \"\"")
        break

    # 3. NLU
    response_text = get_bot_response(text)
    log(f"🤖 Cevap: {response_text}")

    # 4. TTS (Oynatma)
    audio_response = text_to_speech(response_text)
    
    if audio_response:
        # Dosya varsa çal
        agi_cmd("EXEC Progress")
        agi_cmd(f"STREAM FILE {audio_response} \"\"")
    else:
        # Dosya yoksa harf harf oku (Sadece hata durumunda)
        agi_cmd(f"SAY ALPHA \"{response_text}\" \"\"")

log("🛑 Bitti.")
agi_cmd("HANGUP")
