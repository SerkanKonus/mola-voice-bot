FROM andrius/asterisk:latest

USER root

# 1. Sistem paketlerini kur (Hatalı paket çıkarıldı, alternatifler eklendi)
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-requests \
    asterisk-core-sounds-en-wav asterisk-core-sounds-en-gsm && \
    apt-get clean

# 2. Python kütüphanelerini kur (edge-tts ve requests)
# Yeni Debian sürümlerinde --break-system-packages gereklidir
RUN pip3 install --no-cache-dir --break-system-packages requests edge-tts

# 3. Klasör ve izin ayarları
RUN mkdir -p /var/lib/asterisk/sounds/custom && \
    chmod -R 777 /var/lib/asterisk/sounds && \
    chmod -R 777 /var/lib/asterisk/agi-bin

WORKDIR /var/lib/asterisk
