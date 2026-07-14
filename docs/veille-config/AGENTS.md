# AGENTS.md — Workspace Veille

Ce dossier est la maison de Veille.

## Memory
- `memory/` : notes quotidiennes
- `MEMORY.md` : mémoire long-terme
- `TOOLS.md` : credentials locales (ne pas pusher en clair)

## Projet actif
- **Wazuh AI Filter** : `wazuh-test/`
- Manager : localhost
- Target : 192.168.30.10 (SSH via `ssh target ...`)

## Raccourcis SSH
ssh target — Target VM
ssh manager — localhost

## Commandes utiles
- Healthcheck : `bash ~/wazuh-test/scripts/lab-healthcheck.sh`
- Campagne : `bash ~/wazuh-test/scripts/lab-campaign.sh <duree>`
- ML API : `curl http://127.0.0.1:9090/...`
