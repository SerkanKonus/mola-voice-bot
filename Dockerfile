FROM andrius/asterisk:latest

USER root

# Python ve kütüphaneler
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-requests && \
    apt-get clean

# Ses klasörleri
RUN mkdir -p /var/lib/asterisk/sounds/custom && \
    chmod -R 777 /var/lib/asterisk/sounds && \
    chmod -R 777 /var/lib/asterisk/agi-bin

WORKDIR /var/lib/asterisk
