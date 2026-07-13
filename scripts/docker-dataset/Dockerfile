# Base légère pour 100 conteneurs
FROM alpine:latest

# Installation des outils (taille finale ~120 Mo)
RUN apk add --no-cache \
    python3 \
    nmap \
    nmap-scripts \
    hydra \
    curl \
    openssh-client \
    sshpass \
    iputils \
    bind-tools \
    bash

# Script de profil
COPY profiles.py /profiles.py
RUN chmod +x /profiles.py

ENTRYPOINT ["python3", "/profiles.py"]
