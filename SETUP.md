# SETUP — Labo Wazuh AI Filter : déploiement des nœuds OpenClaw

> Version : 1.0 — Date : 2026-07-14  
> Architecture validée : **Plan A — Gateway unique (WSL) + 2 Node Hosts (Manager, Target)**  
> Ce fichier est le blueprint unique d'installation. Suivre dans l'ordre.

---

## Table des matières

1. [Présentation de l'architecture](#1-présentation-de-larchitecture)
2. [Prérequis réseau et machines](#2-prérequis-réseau-et-machines)
3. [Sécurité : segmentation et UFW](#3-sécurité--segmentation-et-ufw)
4. [Configuration Windows (Portproxy + Firewall)](#4-configuration-windows-portproxy--firewall)
5. [Installation du Manager (Ubuntu 24.04 — 192.168.30.3)](#5-installation-du-manager-ubuntu-2404--192168303)
6. [Installation de la Target (Ubuntu 22.04 — 192.168.30.10)](#6-installation-de-la-target-ubuntu-2204--1921683010)
7. [Acceptation des nœuds sur le Gateway](#7-acceptation-des-nœuds-sur-le-gateway)
8. [Tests de validation (Ping/Pong)](#8-tests-de-validation-pingpong)
9. [Orchestration : usage quotidien](#9-orchestration--usage-quotidien)
10. [Scripts d'automatisation](#10-scripts-dautomatisation)
11. [Dépannage](#11-dépannage)
12. [Checklist de validation finale](#12-checklist-de-validation-finale)

---

## 1. Présentation de l'architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                   WSL2 (Windows 11) — Gateway Principal               │
│   IP : 172.31.240.191    Port : 18789    Domaine : guaiguai2.duckdns │
│   Roles : orchrestre les nœuds, heberge le modele IA, interface chat │
│   Acces : Telegram (@Maxime205_bot) + Dashboard web                  │
└──────────────────────────────────────────────────────────────────────┘
          │                          │
          │ Connexion WebSocket     │ Connexion WebSocket
          │ sortante vers           │ sortante vers
          │ 192.168.30.1:18789      │ 192.168.30.1:18789
          ▼                          ▼
┌────────────────────────┐  ┌────────────────────────┐
│  Manager VM             │  │  Target VM              │
│  Ubuntu 24.04           │  │  Ubuntu 22.04           │
│  192.168.30.3           │  │  192.168.30.10          │
│                         │  │                         │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │ Nœud OpenClaw      │  │  │  │ Nœud OpenClaw      │  │
│  │ (service systemd)  │  │  │  │ (service systemd)  │  │
│  └───────────────────┘  │  │  └───────────────────┘  │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │ Wazuh Manager      │  │  │  │ Wazuh Agent        │  │
│  │ (all-in-one)       │  │  │  │ (connect au Mgr)   │  │
│  └───────────────────┘  │  │  └───────────────────┘  │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │ ML Sidecar         │  │  │  │ Suricata IDS       │  │
│  │ (Inference :9090)  │  │  │  │ (ecoute enp0s8)    │  │
│  └───────────────────┘  │  │  └───────────────────┘  │
│  ┌───────────────────┐  │  │  ┌───────────────────┐  │
│  │ OpenSearch :9200   │  │  │  │ Docker             │  │
│  │ Wazuh Indexeur     │  │  │  │ (campagnes IA)     │  │
│  └───────────────────┘  │  │  └───────────────────┘  │
└────────────────────────┘  └────────────────────────┘
          │                          │
          └──────────┬───────────────┘
                     │ Communication directe (LAN 192.168.30.0/24)
                     │ SSH, API REST, Wazuh Agent -> Manager
                     ▼
        ┌────────────────────────┐
        │  ParrotOS (Attaquant)   │
        │  192.168.30.5           │
        │                         │
        │  Envoie le trafic        │
        │  d'attaque vers la      │
        │  Target (visible par    │
        │  Suricata)               │
        └────────────────────────┘
```

### Flux de données

```
[ParrotOS] ──nmap/hydra──► [Target] ──eve.json──► [Agent Wazuh]
                                                       │
                                                       ▼
                                              [Manager Wazuh]
                                                       │
                                              [alerts.json]
                                                       │
                                              [ML Inference:9090]
                                                       │
                                              [Predictions DB]
                                                       │
                                              [Wazuh Dashboard]
```

### Rôles des nœuds OpenClaw

| Machine | Nom du nœud | Rôle | Outils autorisés |
|---------|-------------|------|------------------|
| WSL (Gateway) | — (Gateway) | Orchestrateur central | Tous |
| Manager | `manager-wazuh` | ML inference, API, Wazuh | `system.run`, `system.which` |
| Target | `target-suricata` | Suricata, Docker, Wazuh agent | `system.run`, `system.which` |

---

## 2. Prérequis réseau et machines

### 2.1 Tableau des machines

| Machine | OS | IP LAN (Host-Only) | IP NAT | Accès internet |
|---------|----|--------------------|--------|----------------|
| **WSL** (Gateway) | Ubuntu 22.04 (WSL2) | — | 172.31.240.191 | Oui |
| **Manager** | Ubuntu 24.04 | 192.168.30.3 | 10.0.2.x | Oui (via NAT) |
| **Target** | Ubuntu 22.04 | 192.168.30.10 | 10.0.2.x | Oui (via NAT) |
| **ParrotOS** | Parrot OS | 192.168.30.5 | 10.0.2.x | Oui (via NAT) |

### 2.2 Inventaire des services déjà installés

#### Manager (192.168.30.3)
| Service | Statut | Port | Credentials |
|---------|--------|------|-------------|
| Wazuh Manager | ✅ Installé | 55000 | `wazuh-wui` / `tpuKUfY7Auj2kd9yeRBwgiNjHH+mmNso` |
| OpenSearch | ✅ Installé | 9200 | `admin` / `YFrxHHO*3QK2y6l6JceItXgQ8zO6Jbwn` |
| Wazuh Dashboard | ✅ Installé | 443 | — |
| Python 3 + pip | ✅ Installé | — | — |
| XGBoost | ✅ Installé | — | — |
| ML Sidecar | ⬜ À déployer | 9090 | Voir section 5 |
| OpenClaw Node | ⬜ À installer | — | Voir section 5 |

#### Target (192.168.30.10)
| Service | Statut | Port | Notes |
|---------|--------|------|-------|
| Wazuh Agent | ✅ Installé | 1514/udp | Connecté au Manager |
| Suricata | ✅ Installé | — | Règles ET + custom |
| Docker | ✅ Installé | — | Pour campagnes |
| Python 3 | ✅ Installé | — | — |
| OpenClaw Node | ⬜ À installer | — | Voir section 6 |

---

## 3. Sécurité : segmentation et UFW

### 3.1 Principes

```
┌────────────────────────────────────────────────────┐
│ Règle d'or :                                        │
│ ParrotOS (attaquant) = NON CONFIANCE                │
│   → Peut envoyer du trafic réseau (attaques)        │
│   → NE PEUT PAS accéder aux interfaces de gestion   │
│                                                     │
│ Manager + Target = CONFIANCE PARTIELLE               │
│   → Communication SSH et API entre elles            │
│   → Accès limité à l'infrastructure OpenClaw        │
└────────────────────────────────────────────────────┘
```

### 3.2 Règles UFW — Manager (192.168.30.3)

Appliquer DANS L'ORDRE :

```bash
# Se connecter au Manager
ssh vboxuser@192.168.30.3

# 1. Réinitialiser et configurer les règles par défaut
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. SSH — uniquement depuis Target et Windows Host
sudo ufw allow from 192.168.30.10 to any port 22 proto tcp comment 'SSH depuis Target'
sudo ufw allow from 192.168.30.1 to any port 22 proto tcp comment 'SSH depuis Windows Host'

# 3. ML Inference API — accessible depuis la Target uniquement
sudo ufw allow from 192.168.30.10 to any port 9090 proto tcp comment 'API ML pour Target'

# 4. Wazuh API — locale uniquement (dashboard sur la même machine)
sudo ufw allow from 127.0.0.1 to any port 55000 proto tcp comment 'Wazuh API locale'
sudo ufw allow from 192.168.30.10 to any port 55000 proto tcp comment 'Wazuh API Target'

# 5. OpenSearch — local uniquement
sudo ufw allow from 127.0.0.1 to any port 9200 proto tcp comment 'OpenSearch local'

# 6. Wazuh Dashboard — local uniquement
sudo ufw allow from 127.0.0.1 to any port 443 proto tcp comment 'Dashboard local'

# 7. (Optionnel) Ports Wazuh pour l'agent Target
sudo ufw allow 1514/udp comment 'Wazuh Agent -> Manager'

# Activer
sudo ufw --force enable
sudo ufw status numbered
```

**Résultat** : ParrotOS (192.168.30.5) ne peut RIEN atteindre sur le Manager.

### 3.3 Règles UFW — Target (192.168.30.10)

```bash
# Se connecter à la Target
ssh vboxuser@192.168.30.10

# 1. Réinitialiser
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. SSH — Manager et Windows uniquement
sudo ufw allow from 192.168.30.3 to any port 22 proto tcp comment 'SSH depuis Manager'
sudo ufw allow from 192.168.30.1 to any port 22 proto tcp comment 'SSH depuis Windows Host'

# 3. Wazuh Agent outbound (sortant déjà autorisé par default allow outgoing)

# Activer
sudo ufw --force enable
sudo ufw status numbered
```

**Suricata** capture les paquets via `af-packet`, qui travaille au niveau noyau,
**avant** les règles iptables/UFW. Les attaques de ParrotOS sont donc bien
visibles par Suricata, même si UFW bloque les connexions entrantes vers les
ports de gestion.

### 3.4 Vérification du blocage de ParrotOS

```bash
# Depuis ParrotOS, tenter :
ssh vboxuser@192.168.30.3    # → REFUSED (timeout)
ssh vboxuser@192.168.30.10   # → REFUSED (timeout)
curl http://192.168.30.3:9090   # → REFUSED
curl http://192.168.30.3:55000  # → REFUSED

# Ce n'est PAS un bug — c'est la sécurité qui fonctionne !
# ParrotOS envoie toujours du trafic réseau que Suricata capte.
```

---

## 4. Configuration Windows (Portproxy + Firewall)

### 4.1 Vérifier l'IP WSL actuelle

```bash
# Dans WSL :
ip addr show eth0 | grep inet
# Résultat attendu : inet 172.31.240.191/20 ...
```

**⚠️ Note critique** : L'IP du WSL2 CHANGE à chaque reboot de Windows.
Après un reboot, répéter les étapes 4.2 et 4.3 avec la nouvelle IP.

### 4.2 Portproxy (PowerShell Admin)

```powershell
# PowerShell en mode Administrateur

# Ajouter le portproxy
netsh interface portproxy add v4tov4 `
  listenport=18789 listenaddress=0.0.0.0 `
  connectaddress=172.31.240.191 connectport=18789

# Vérifier
netsh interface portproxy show all
```

### 4.3 Firewall Windows — Filtrage par IP

```powershell
# PowerShell en mode Administrateur

# 1. Autoriser les IP de confiance
netsh advfirewall firewall add rule name="OpenClaw-Manager" `
  dir=in action=allow protocol=TCP localport=18789 remoteip=192.168.30.3

netsh advfirewall firewall add rule name="OpenClaw-Target" `
  dir=in action=allow protocol=TCP localport=18789 remoteip=192.168.30.10

# 2. Bloquer toutes les autres IP (y compris ParrotOS)
netsh advfirewall firewall add rule name="OpenClaw-Deny-Others" `
  dir=in action=block protocol=TCP localport=18789

# 3. Vérifier
netsh advfirewall firewall show rule name="OpenClaw-*"
```

**Résultat** : Seuls le Manager et la Target peuvent utiliser le portproxy
pour se connecter au Gateway WSL. ParrotOS est bloqué au niveau Windows.

### 4.4 Test de base (avant installation des nœuds)

```powershell
# PowerShell (pas besoin d'admin pour ça)
Test-NetConnection -ComputerName 192.168.30.1 -Port 18789
```

### 4.5 Après reboot Windows

```bash
# 1. Dans WSL : trouver la nouvelle IP
ip addr show eth0 | grep inet

# 2. PowerShell Admin : mettre à jour
netsh interface portproxy set v4tov4 `
  listenport=18789 listenaddress=0.0.0.0 `
  connectaddress=NOUVELLE_IP connectport=18789
```

---

## 5. Installation du Manager (Ubuntu 24.04 — 192.168.30.3)

### 5.1 Installer OpenClaw

```bash
# Dans un terminal SSH sur le Manager
ssh vboxuser@192.168.30.3

# Installer OpenClaw
curl -sL https://openclaw.ai/install.sh | bash

# Vérifier
openclaw --version
# Résultat attendu : OpenClaw 2026.6.5 (ou version récente)
```

### 5.2 Configurer le nœud

```bash
# Récupérer le token Gateway depuis WSL
# (à faire dans un autre terminal, garder le token pour plus tard)

# Configurer le token dans l'environnement
# NE PAS mettre le token en clair dans l'historique bash
read -s -p "Token Gateway : " GW_TOKEN
export OPENCLAW_GATEWAY_TOKEN="$GW_TOKEN"

# Lancer en mode foreground pour tester la connexion
openclaw node run --host 192.168.30.1 --port 18789 --display-name "manager-wazuh"
```

**Ne pas fermer le terminal** — laisser tourner le nœud en foreground
le temps de l'approuver (section 7). Ensuite on installe le service.

### 5.3 Déployer le ML Sidecar

```bash
# Cloner le repo (ou copier depuis le Gateway si pas d'internet)
git clone https://github.com/maraa081/wazuh-test.git /home/vboxuser/wazuh-test

# Créer le dossier du sidecar
sudo mkdir -p /opt/wazuh-ml

# Copier les fichiers
sudo cp /home/vboxuser/wazuh-test/scripts/inference_service.py /opt/wazuh-ml/
sudo cp /home/vboxuser/wazuh-test/scripts/api_service.py /opt/wazuh-ml/
sudo cp /home/vboxuser/wazuh-test/models/xgb_model.json /opt/wazuh-ml/
sudo cp /home/vboxuser/wazuh-test/models/xgb_model_metrics.json /opt/wazuh-ml/

# Permissions
sudo chmod 755 /opt/wazuh-ml/
sudo chmod 644 /opt/wazuh-ml/*.json
sudo chmod 755 /opt/wazuh-ml/*.py

# Base de données SQLite
sudo touch /tmp/predictions.db
sudo chmod 666 /tmp/predictions.db

# Installer les dépendances Python si pas déjà fait
sudo pip3 install xgboost fastapi uvicorn --break-system-packages
```

### 5.4 Créer les services systemd du ML Sidecar

```bash
# Service d'inférence
sudo tee /etc/systemd/system/wazuh-inference.service << 'EOF'
[Unit]
Description=Wazuh ML Inference Service
After=network.target
Wants=wazuh-manager.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/inference_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Service API
sudo tee /etc/systemd/system/wazuh-api.service << 'EOF'
[Unit]
Description=Wazuh ML API Service
After=network.target wazuh-inference.service
Wants=wazuh-inference.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wazuh-ml
ExecStart=/usr/bin/python3 /opt/wazuh-ml/api_service.py --db /tmp/predictions.db --port 9090 --host 127.0.0.1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable wazuh-inference wazuh-api
sudo systemctl start wazuh-inference

# Attendre 5 secondes
sleep 5

# Vérifier l'inférence
sudo journalctl -u wazuh-inference -n 20 --no-pager

# Puis démarrer l'API
sudo systemctl start wazuh-api
sudo journalctl -u wazuh-api -n 20 --no-pager
```

### 5.5 Installer le service systemd du nœud OpenClaw

```bash
# Arrêter le nœud foreground (Ctrl+C) puis :
openclaw node install \
  --host 192.168.30.1 \
  --port 18789 \
  --display-name "manager-wazuh"

# Démarrer le service
openclaw node start
openclaw node status
```

### 5.6 Vérifications finales Manager

```bash
# Nœud OpenClaw
openclaw node status
# → doit afficher "running"

# ML Inference
curl -s http://127.0.0.1:9090/predictions/recent
# → doit répondre (liste vide ou prédictions)

# Wazuh Manager
sudo systemctl status wazuh-manager
# → doit être running

# UFW
sudo ufw status numbered
# → doit montrer les règles restrictives
```

---

## 6. Installation de la Target (Ubuntu 22.04 — 192.168.30.10)

### 6.1 Installer OpenClaw

```bash
ssh vboxuser@192.168.30.10

curl -sL https://openclaw.ai/install.sh | bash
openclaw --version
```

### 6.2 Configurer le nœud (test foreground)

```bash
read -s -p "Token Gateway : " GW_TOKEN
export OPENCLAW_GATEWAY_TOKEN="$GW_TOKEN"

openclaw node run --host 192.168.30.1 --port 18789 --display-name "target-suricata"
```

### 6.3 Installer le service systemd

```bash
# Ctrl+C pour arrêter le foreground, puis :
openclaw node install \
  --host 192.168.30.1 \
  --port 18789 \
  --display-name "target-suricata"

openclaw node start
openclaw node status
```

### 6.4 Vérifier Suricata et Docker

```bash
# Suricata
sudo suricata -T -c /etc/suricata/suricata.yaml
# → doit afficher "suricata: running"

# Docker
sudo docker ps
# → doit fonctionner (liste vide si pas de conteneurs)

# Wazuh Agent
sudo systemctl status wazuh-agent
# → doit être connected au Manager
```

### 6.5 Vérifications finales Target

```bash
openclaw node status
# → "running"

sudo ufw status numbered
# → SSH bloqué pour tout sauf Manager et Windows
```

---

## 7. Acceptation des nœuds sur le Gateway

### 7.1 Sur le Gateway WSL

```bash
# Lister les requêtes en attente
openclaw devices list

# Exemple de sortie :
# Pending device pairing requests:
#   req_abc123   manager-wazuh (192.168.30.3)
#   req_def456   target-suricata (192.168.30.10)

# Approuver chaque nœud
openclaw devices approve req_abc123
openclaw devices approve req_def456
```

### 7.2 Vérifier les nœuds connectés

```bash
openclaw nodes list
openclaw nodes list --connected
openclaw nodes status
```

**Résultat attendu** :

```
Node              ID                  Status       Last Connect
manager-wazuh     <id>               Paired       just now
target-suricata   <id>               Paired       just now
```

### 7.3 (Optionnel) Auto-approve pour le futur

Si tu veux que les nœuds du labo soient automatiquement approuvés
(évite de devoir approuver manuellement après un redéploiement) :

```bash
# Éditer la config OpenClaw
openclaw config set 'gateway.nodes.pairing.autoApproveCidrs' '["192.168.30.0/24"]'

# Redémarrer le Gateway
openclaw gateway restart
```

---

## 8. Tests de validation (Ping/Pong)

### 8.1 Test 1 : Connexion basique (echo)

```bash
# Depuis le Gateway WSL, tester le Manager :
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"echo PONG_MANAGER && hostname && uptime -p"}'

# Résultat attendu :
# {
#   "stdout": "PONG_MANAGER\nmanager-wazuh\nup 2 hours, 15 minutes\n",
#   "stderr": "",
#   "exitCode": 0
# }

# Tester la Target :
openclaw nodes invoke --node "target-suricata" \
  --command "system.run" \
  --params '{"command":"echo PONG_TARGET && hostname && uptime -p"}'

# Résultat attendu similaire avec "target-suricata"
```

### 8.2 Test 2 : Check des services spécifiques

```bash
# Manager — vérifier que les services ML tournent
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"systemctl is-active wazuh-inference wazuh-api"}'

# Résultat attendu : "active\nactive"

# Target — vérifier Suricata et Docker
openclaw nodes invoke --node "target-suricata" \
  --command "system.run" \
  --params '{"command":"systemctl is-active suricata && sudo docker info --format \\"{{.ServerVersion}}\\""}'

# Résultat attendu : "active\nXX.XX.XX"
```

### 8.3 Test 3 : Communication Manager ↔ Target

```bash
# Depuis le Gateway, tester le ping entre les VMs via le Manager :
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"ping -c 2 -W 2 192.168.30.10"}'

# Résultat : 0% packet loss

# Via la Target :
openclaw nodes invoke --node "target-suricata" \
  --command "system.run" \
  --params '{"command":"ping -c 2 -W 2 192.168.30.3"}'

# Résultat : 0% packet loss
```

### 8.4 Test 4 : Pipeline ML complet (validation bout en bout)

```bash
# 1. Vérifier que l'API ML répond
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"curl -s http://127.0.0.1:9090/health"}'

# 2. Vérifier le modèle chargé
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"curl -s http://127.0.0.1:9090/model/status"}'

# 3. Vérifier les prédictions récentes
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"curl -s http://127.0.0.1:9090/predictions/recent?limit=5"}'
```

---

## 9. Orchestration : usage quotidien

### 9.1 Depuis le chat OpenClaw (Telegram)

Une fois les nœuds opérationnels, tu peux piloter tout le labo directement
depuis Telegram. Exemples de commandes que l'agent peut exécuter :

```
# Lancer une campagne d'attaque (sur la Target)
exec host=node node=target-suricata command="cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration 600"

# Vérifier que Suricata capte du trafic
exec host=node node=target-suricata command="sudo tail -n 20 /var/log/suricata/fast.log"

# Voir les prédictions de l'IA (sur le Manager)
exec host=node node=manager-wazuh command="curl -s http://127.0.0.1:9090/predictions/recent?limit=5"

# Redémarrer le service ML inference
exec host=node node=manager-wazuh command="sudo systemctl restart wazuh-inference"

# Collecter des alertes fraîches du Manager
exec host=node node=manager-wazuh command="tail -n 100 /var/ossec/logs/alerts/alerts.json"
```

### 9.2 Automatisation via cron OpenClaw

Créer des tâches planifiées :

```bash
# Tous les jours à 8h : vérifier l'état des services
openclaw cron add \
  --name "lab-healthcheck" \
  --schedule '{"kind":"cron","expr":"0 8 * * *","tz":"Europe/Paris"}' \
  --payload '{"kind":"systemEvent","text":"Check lab VMs: exec host=node node=manager command=\"systemctl is-active wazuh-inference wazuh-api\""}'
```

### 9.3 Orchestration multi-nœuds (séquences)

```bash
# Exemple : séquence complète "Campagne -> Collecte -> Inférence"

# 1. Lancer la campagne
echo "=== LANCEMENT CAMPAGNE ==="
openclaw nodes invoke --node "target-suricata" \
  --command "system.run" \
  --params '{"command":"cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration 300 --background"}'

# 2. Attendre
echo "=== ATTENTE 60s ==="
sleep 60

# 3. Vérifier l'état de la campagne
openclaw nodes invoke --node "target-suricata" \
  --command "system.run" \
  --params '{"command":"sudo docker ps --format \\"{{.Names}} {{.Status}}\\" | head -10"}'

# 4. Une fois la campagne finie, collecter les alertes sur le Manager
echo "=== COLLECTE ALERTES ==="
openclaw nodes invoke --node "manager-wazuh" \
  --command "system.run" \
  --params '{"command":"tail -n 500 /var/ossec/logs/alerts/alerts.json > /tmp/recent_alerts.json && wc -l /tmp/recent_alerts.json"}'
```

---

## 10. Scripts d'automatisation

### 10.1 Script : `lab-campaign.sh`

À placer sur le Gateway WSL dans `/home/user/.openclaw/workspace/scripts/` :

```bash
#!/bin/bash
# lab-campaign.sh — Orchestration complète d'une campagne
# Usage : ./lab-campaign.sh <duree_secondes>

DURATION=${1:-300}
NODE_MANAGER="manager-wazuh"
NODE_TARGET="target-suricata"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[$(date +%H:%M:%S)] === CAMPAGNE $TIMESTAMP (${DURATION}s) ==="

# Phase 1 : Préparer la collecte
echo "[1/4] Preparation de la collecte..."
openclaw nodes invoke --node "$NODE_MANAGER" \
  --command "system.run" \
  --params "{\"command\":\"mkdir -p /tmp/campaign_$TIMESTAMP\"}"

# Phase 2 : Lancer la campagne
echo "[2/4] Lancement de la campagne (${DURATION}s)..."
openclaw nodes invoke --node "$NODE_TARGET" \
  --command "system.run" \
  --params "{\"command\":\"cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration $DURATION\"}"

# Phase 3 : Attendre un peu puis collecter
echo "[3/4] Attente et collecte..."
sleep $((DURATION + 30))

ALERTS=$(openclaw nodes invoke --node "$NODE_MANAGER" \
  --command "system.run" \
  --params "{\"command\":\"tail -n 1000 /var/ossec/logs/alerts/alerts.json | wc -l\"}" 2>&1 | grep -oP '"stdout":"\K[^"]+')

echo "Alertes collectees : $ALERTS"

# Phase 4 : Inférence sur les nouvelles alertes
echo "[4/4] Inference ML..."
openclaw nodes invoke --node "$NODE_MANAGER" \
  --command "system.run" \
  --params "{\"command\":\"curl -s http://127.0.0.1:9090/predictions/recent?limit=10\"}"

echo "[$(date +%H:%M:%S)] === CAMPAGNE TERMINEE ==="
```

### 10.2 Script : `lab-healthcheck.sh`

```bash
#!/bin/bash
# lab-healthcheck.sh — Vérification rapide du labo

echo "========== LAB HEALTHCHECK =========="
echo ""

check_node() {
  local name=$1
  local result=$(openclaw nodes invoke --node "$name" \
    --command "system.run" \
    --params '{"command":"hostname && uptime -p && df -h / | tail -1"}' 2>&1)
  local exitcode=$?
  if [ $exitcode -eq 0 ]; then
    echo "[OK] $name — $(echo "$result" | grep -oP '"stdout":"\K[^"]+' | head -1)"
  else
    echo "[FAIL] $name — injoignable"
  fi
}

check_node "manager-wazuh"
check_node "target-suricata"

echo ""
echo "========== END =========="
```

---

## 11. Dépannage

### 11.1 Le nœud ne se connecte pas

```
Symptôme : "openclaw node run" reste bloqué sur "Connecting..."
           ou retourne "connection refused"
```

**Causes et solutions :**

| Cause | Diagnostic | Solution |
|-------|-----------|----------|
| Portproxy Windows cassé | `netsh interface portproxy show all` | Reconfigurer avec la bonne IP WSL |
| IP WSL changée | `ip addr show eth0` dans WSL | Mettre à jour le portproxy |
| Firewall Windows bloque | `netsh advfirewall firewall show rule name="OpenClaw-*"` | Vérifier les règles |
| Token invalide | Regarder les logs du nœud | `export OPENCLAW_GATEWAY_TOKEN="..."` |
| Nœud pas approuvé | `openclaw devices list` sur Gateway | `openclaw devices approve <id>` |

### 11.2 Le service ML ne démarre pas

```bash
# Voir les logs
sudo journalctl -u wazuh-inference -n 50 --no-pager
sudo journalctl -u wazuh-api -n 50 --no-pager

# Vérifier la base SQLite
file /tmp/predictions.db
# → doit dire "SQLite 3.x database"
ls -la /tmp/predictions.db
# → permissions 666

# Tester le modèle
python3 -c "
import json
with open('/opt/wazuh-ml/xgb_model_metrics.json') as f:
    m = json.load(f)
print('Features:', len(m.get('feature_names', [])))
print('ROC AUC:', m.get('roc_auc', 'N/A'))
"
```

### 11.3 Réinitialisation complète d'un nœud

```bash
# Sur la VM
openclaw node stop
openclaw node uninstall
rm -rf ~/.openclaw

# Réinstaller
curl -sL https://openclaw.ai/install.sh | bash
openclaw node install --host 192.168.30.1 --port 18789 --display-name "manager-wazuh"
openclaw node start
```

### 11.4 UFW bloquant Suricata

Si Suricata arrête de voir du trafic après l'activation d'UFW :

```bash
# Vérifier que af-packet fonctionne (capture au niveau noyau)
sudo suricata -T -c /etc/suricata/suricata.yaml

# Suricata avec af-packet capte AVANT iptables,
# donc UFW ne devrait pas bloquer.
# Si problème : vérifier la config af-packet
grep -A5 "af-packet" /etc/suricata/suricata.yaml
```

---

## 12. Checklist de validation finale

### 12.1 Infrastructure réseau
- [ ] Windows portproxy configuré (vérifié : `netsh interface portproxy show all`)
- [ ] Firewall Windows bloque ParrotOS (règles verify : `netsh advfirewall firewall show rule name="OpenClaw-*"`)
- [ ] Manager UFW actif et restrictif
- [ ] Target UFW actif et restrictif
- [ ] ParrotOS ne peut pas SSH/Mgr/API (vérifié avec un test)

### 12.2 Nœud Manager
- [ ] OpenClaw installé (`openclaw --version`)
- [ ] Nœud approuvé (`openclaw nodes list --connected`)
- [ ] Service systemd installé (`openclaw node status` → running)
- [ ] ML Inference service OK (`systemctl is-active wazuh-inference`)
- [ ] ML API service OK (`systemctl is-active wazuh-api`)
- [ ] API répond sur :9090 (`curl http://127.0.0.1:9090/health`)
- [ ] Modèle XGBoost chargé (`curl http://127.0.0.1:9090/model/status`)

### 12.3 Nœud Target
- [ ] OpenClaw installé (`openclaw --version`)
- [ ] Nœud approuvé (`openclaw nodes list --connected`)
- [ ] Service systemd installé (`openclaw node status` → running)
- [ ] Suricata fonctionnel (`sudo suricata -T -c /etc/suricata/suricata.yaml`)
- [ ] Docker fonctionnel (`sudo docker info --format '{{.ServerVersion}}'`)

### 12.4 Tests de communication
- [ ] Ping Gateway → Manager (`openclaw nodes invoke --node "manager-wazuh" ...`)
- [ ] Ping Gateway → Target (`openclaw nodes invoke --node "target-suricata" ...`)
- [ ] Test echo (PONG) des deux nœuds
- [ ] Manager peut joindre Target (ping 192.168.30.10)
- [ ] Target peut joindre Manager (ping 192.168.30.3)
- [ ] Communication API ML depuis la Target (`curl http://192.168.30.3:9090`)

### 12.5 Pipeline complet
- [ ] Le Gateway peut lancer une campagne sur la Target
- [ ] Le Gateway peut collecter des alertes sur le Manager
- [ ] Le Gateway peut interroger l'API ML
- [ ] Script `lab-campaign.sh` s'exécute sans erreur
- [ ] Script `lab-healthcheck.sh` retourne OK pour les deux nœuds

---

## Annexe A : Références

- [OpenClaw Docs — Node Host CLI](/cli/node)
- [OpenClaw Docs — Nodes Management](/cli/nodes)
- [OpenClaw Docs — Exec Tool](/tools/exec)
- [OpenClaw Docs — Remote Access](/gateway/remote)
- [Projet GitHub — wazuh-test](https://github.com/maraa081/wazuh-test)
- [Journal de bord](docs/JOURNAL_DE_BORD.md) — historique des problèmes
- [Plan agents OpenClaw](docs/PLAN_AGENTS_OPENCLAW.md)
- [Charte de développement](docs/DEVELOPMENT_CHARTER.md)

## Annexe B : Fichiers associés dans ce repo

| Fichier | Description |
|---------|-------------|
| `SETUP.md` | **(ce fichier)** Blueprint de déploiement |
| `docs/DEPLOY_OPENCLAW_NODES.md` | Plan détaillé des nœuds (complément technique) |
| `docs/PLAN_AGENTS_OPENCLAW.md` | Plan conceptuel original |
| `docs/JOURNAL_DE_BORD.md` | Post-mortem des problèmes rencontrés |
| `docs/DEVELOPMENT_CHARTER.md` | Charte MLOps |
| `docs/DEPLOYMENT_NOTES.md` | Notes déploiement Suricata |
| `scripts/` | Scripts d'automatisation |
| `service/` | Fichiers systemd du sidecar ML |
