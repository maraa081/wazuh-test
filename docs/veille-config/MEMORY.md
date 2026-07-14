# MEMORY.md — Veille

## Infrastructure labo
- Manager (Ubuntu 24.04) : 192.168.30.3 — Gateway OpenClaw + ML + Wazuh
- Target (Ubuntu 22.04) : 192.168.30.10 — Suricata + Docker + Wazuh Agent
- ParrotOS (attaquant) : 192.168.30.5
- Acces SSH Manager -> Target via cle ED25519 (alias "target")

## Services Manager
- OpenClaw Gateway : port 18789 (Control UI : /openclaw/)
- ML Inference : wazuh-inference.service
- ML API : wazuh-api.service (port 9090)
- Wazuh Manager : all-in-one

## Securite
- UFW actif sur Manager et Target
- ParrotOS bloque de tous les ports
- Control UI accessible uniquement depuis Windows (192.168.30.1)

## Wazuh credentials
- API Wazuh : wazuh-wui / tpuKUfY7Auj2kd9yeRBwgiNjHH+mmNso
- OpenSearch : admin / YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn

## Charte de dev
- ASCII strict dans les scripts (pas d'Unicode)
- Types castes avant SQL
- Buffer de frequence consomme TOUT le flux d'alertes
- Cold start : pre-populer le buffer depuis SQLite

## Git
- wazuh-test : maraa081/wazuh-test (public)
