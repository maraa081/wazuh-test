# SETUP — Labo Wazuh AI Filter : Gateway Manager + SSH Target

> Version : 2.0 — Date : 2026-07-14  
> Architecture validee : **Option X — 1 Gateway (Manager) + Cles SSH (Target)**  
> Ce fichier est le blueprint unique d'installation. Suivre dans l'ordre.

---

## Table des matieres

1. [Presentation de l'architecture](#1-presentation-de-larchitecture)
2. [Prerequis machines](#2-prerequis-machines)
3. [Securite : UFW et regles de pare-feu](#3-securite--ufw-et-regles-de-pare-feu)
4. [Cle SSH : Manager -> Target](#4-cle-ssh--manager---target)
5. [Installation de la Gateway OpenClaw (Manager)](#5-installation-de-la-gateway-openclaw-manager)
6. [Migration du bot Telegram @Maxime205_bot](#6-migration-du-bot-telegram-maxime205_bot)
7. [Deploiement du ML Sidecar](#7-deploiement-du-ml-sidecar)
8. [Tests de validation (Ping/Pong)](#8-tests-de-validation-pingpong)
9. [Orchestration SSH : lancer des commandes sur la Target](#9-orchestration-ssh--lancer-des-commandes-sur-la-target)
10. [Usage quotidien](#10-usage-quotidien)
11. [Scripts d'automatisation](#11-scripts-dautomatisation)
12. [Depannage](#12-depannage)
13. [Checklist de validation finale](#13-checklist-de-validation-finale)

---

## 1. Presentation de l'architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      AVANT (ANCIENNE ARCHI)                          │
│                                                                      │
│   WSL (Gateway) ──portproxy── Windows ──ws──► Manager (Node)        │
│                    ↑ changements d'IP                                │
│                    ↑ portproxy fragile                               │
│                    ↑ dependance WSL                                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      APRES (NOUVELLE ARCHI)                          │
│                                                                      │
│   ┌─────────────────────────────────────────┐                       │
│   │  Manager VM (Ubuntu 24.04)              │                       │
│   │  192.168.30.3                           │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  Gateway OpenClaw               │    │                       │
│   │  │  Port 18789 (bind: lan)         │    │                       │
│   │  │  Control UI : http://...3:18789 │    │                       │
│   │  │  Bot Telegram @Maxime205_bot    │    │                       │
│   │  │  Pipeline IA + inference        │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  Wazuh Manager (all-in-one)     │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  ML Sidecar (Inference :9090)   │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   └─────────────────────────────────────────┘                       │
│            │                                                        │
│            │ SSH (cles) vers la Target                              │
│            │ commandes : campagne, docker, suricata, logs           │
│            ▼                                                        │
│   ┌─────────────────────────────────────────┐                       │
│   │  Target VM (Ubuntu 22.04)               │                       │
│   │  192.168.30.10                          │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  Suricata IDS (af-packet)      │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  Docker (campagnes d'attaque)   │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   │                                         │                       │
│   │  ┌─────────────────────────────────┐    │                       │
│   │  │  Wazuh Agent (-> Manager)       │    │                       │
│   │  └─────────────────────────────────┘    │                       │
│   └─────────────────────────────────────────┘                       │
│                                                                      │
│   ┌──────────────────┐                                               │
│   │  ParrotOS         │  Attaquant sur le meme reseau               │
│   │  192.168.30.5     │  -> UFW le bloque de TOUT                   │
│   └──────────────────┘                                               │
└──────────────────────────────────────────────────────────────────────┘
```

### Flux de donnees

```
[Telegram] ──DM──► [Manager Gateway] ─exec/SSH──► [Target]
                         │                              │
                         │                        [Suricata] ←── [ParrotOS]
                         │                              │
                         │                        [Wazuh Agent]
                         ▼                              │
                    [Wazuh Manager] ◄───────────────────┘
                         │
                    [alerts.json]
                         │
                    [ML Inference :9090]
                         │
                    [Predictions DB]
                         │
                    [Wazuh Dashboard]
```

### Ce qui change concretement

| Avant (WSL) | Apres (Manager) | Gain |
|------------|----------------|------|
| Gateway sur WSL (IP variable) | Gateway sur Manager (IP fixe) | Plus de portproxy |
| Node Host sur Manager | Gateway complet sur Manager | Plus de connexion WS |
| Node Host sur Target | SSH uniquement | Plus de second node |
| Portproxy Windows fragile | UFW + IP fixe | Stable au reboot |
| 3 machines impliquees (WSL + 2 VMs) | 2 machines (Manager + Target) | Simplification radicale |

---

## 2. Prerequis machines

### 2.1 Adressage

| Machine | OS | IP Host-Only | Reseau |
|---------|----|-------------|--------|
| **Manager** (Gateway) | Ubuntu 24.04 | 192.168.30.3 | 192.168.30.0/24 |
| **Target** (SSH) | Ubuntu 22.04 | 192.168.30.10 | 192.168.30.0/24 |
| **Windows** (admin) | Windows 11 | 192.168.30.1 | 192.168.30.0/24 |
| **ParrotOS** (attaquant) | Parrot OS | 192.168.30.5 | 192.168.30.0/24 |

### 2.2 Inventaire Manager (192.168.30.3)

| Service | Statut | Port | Notes |
|---------|--------|------|-------|
| Wazuh Manager | Deja installe | 55000 | All-in-one |
| OpenSearch | Deja installe | 9200 | Indexeur Wazuh |
| Wazuh Dashboard | Deja installe | 443 | Interface Wazuh |
| Python 3 + pip3 | Deja installe | — | A verifier |
| XGBoost | A installer | — | `pip3 install xgboost --break-system-packages` |
| FastAPI + Uvicorn | A installer | — | Pour l'API ML |
| ML Sidecar | A deployer | 9090 | Inference + API |
| **OpenClaw Gateway** | **A installer** | **18789** | **NOUVEAU** |

### 2.3 Inventaire Target (192.168.30.10)

| Service | Statut | Port | Notes |
|---------|--------|------|-------|
| Wazuh Agent | Deja installe | 1514/udp | Connecte au Manager |
| Suricata | Deja installe | — | Regles ET + custom |
| Docker | Deja installe | — | Pour campagnes |
| Python 3 | Deja installe | — | — |
| **SSH serveur** | **Deja installe** | **22** | **Pour le Manager** |
| **Cle publique Manager** | **A ajouter** | — | **NOUVEAU** |

### 2.4 Flux reseau autorises (apres installation complete)

```
De Windows (192.168.30.1) :
  -> Manager:22 (SSH admin)
  -> Manager:18789 (Control UI OpenClaw)

Du Manager (192.168.30.3) :
  -> Target:22 (SSH pour commandes)
  -> Internet (NAT) pour apt/pip/openclaw.ai

De la Target (192.168.30.10) :
  -> Manager:55000 (Wazuh Agent -> Manager)
  -> Internet (NAT)

De ParrotOS (192.168.30.5) :
  -> RIEN (UFW bloque tout)
  -> Note : Suricata capte quand meme le trafic reseau via af-packet
```

---

## 3. Securite : UFW et regles de pare-feu

### 3.1 Manager — Regles UFW

```bash
# Se connecter au Manager
ssh vboxuser@192.168.30.3

# Reinitialiser
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# --- SSH ---
# Admin depuis Windows
sudo ufw allow from 192.168.30.1 to any port 22 proto tcp comment 'SSH depuis Windows'
# SSH depuis la Target (pour debug, maintenance)
sudo ufw allow from 192.168.30.10 to any port 22 proto tcp comment 'SSH depuis Target'

# --- OpenClaw Control UI ---
# Accessible UNIQUEMENT depuis Windows (Maraa)
sudo ufw allow from 192.168.30.1 to any port 18789 proto tcp comment 'OpenClaw UI depuis Windows'

# --- ML API ---
sudo ufw allow from 192.168.30.10 to any port 9090 proto tcp comment 'API ML depuis Target'
sudo ufw allow from 127.0.0.1 to any port 9090 proto tcp comment 'API ML locale'

# --- Wazuh API ---
sudo ufw allow from 192.168.30.10 to any port 55000 proto tcp comment 'Wazuh API depuis Target'
sudo ufw allow from 127.0.0.1 to any port 55000 proto tcp comment 'Wazuh API locale'

# --- Wazuh Agent (entrant depuis la Target) ---
sudo ufw allow from 192.168.30.10 to any port 1514 proto udp comment 'Wazuh Agent UDP'
sudo ufw allow from 192.168.30.10 to any port 1515 proto tcp comment 'Wazuh Agent TCP'

# --- OpenSearch (local uniquement) ---
sudo ufw allow from 127.0.0.1 to any port 9200 proto tcp comment 'OpenSearch local'

# --- Dashboard Wazuh (local uniquement) ---
sudo ufw allow from 127.0.0.1 to any port 443 proto tcp comment 'Dashboard local'

# --- Activer ---
sudo ufw --force enable
sudo ufw status numbered
```

**Resultat :** ParrotOS (192.168.30.5) est bloque de TOUS les ports.
Seuls Windows (192.168.30.1) et la Target (192.168.30.10) sont autorises.

### 3.2 Target — Regles UFW

```bash
# Se connecter a la Target
ssh vboxuser@192.168.30.10

sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# --- SSH uniquement depuis le Manager ---
sudo ufw allow from 192.168.30.3 to any port 22 proto tcp comment 'SSH depuis Manager'
# (Windows peut aussi etre autorise pour debug)
sudo ufw allow from 192.168.30.1 to any port 22 proto tcp comment 'SSH depuis Windows'

# --- Wazuh Agent sortant vers le Manager ---
# (deja autorise par default allow outgoing)

# --- Activer ---
sudo ufw --force enable
sudo ufw status numbered
```

**Note Suricata :** UFW travaille au niveau iptables (layer 3/4). Suricata
capte via `af-packet` au niveau noyau (layer 2). Meme si UFW bloque tout,
Suricata voit les paquets de ParrotOS arriver sur l'interface.

### 3.3 Verification du blocage

```bash
# Depuis ParrotOS (192.168.30.5) — TOUT DOIT ECHOUER :
ssh vboxuser@192.168.30.3       # -> timeout
ssh vboxuser@192.168.30.10      # -> timeout
curl http://192.168.30.3:18789  # -> refused
curl http://192.168.30.3:9090   # -> refused
```

```bash
# Depuis Windows (192.168.30.1) — TOUT DOIT MARCHER :
ssh vboxuser@192.168.30.3       # -> OK (SSH)
http://192.168.30.3:18789       # -> OK (OpenClaw UI)
```

---

## 4. Cle SSH : Manager -> Target

### 4.1 Generer la paire de cles sur le Manager

```bash
# Sur le Manager
ssh vboxuser@192.168.30.3

# Generer une cle ED25519 (plus rapide et aussi sure que RSA)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "manager-gateway@wazuh-lab"

# Verifier
ls -la ~/.ssh/
# -> id_ed25519 (cle privee)
# -> id_ed25519.pub (cle publique)
```

### 4.2 Deployer la cle publique sur la Target

```bash
# Methode 1 : ssh-copy-id (necessite le mot de passe une fois)
ssh-copy-id vboxuser@192.168.30.10

# Methode 2 : manuelle (si ssh-copy-id pas disponible)
# Sur le Manager :
cat ~/.ssh/id_ed25519.pub
# Copier la sortie, puis sur la Target :
echo "<cle_publique>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 4.3 Tester la connexion SSH sans mot de passe

```bash
# Sur le Manager
ssh vboxuser@192.168.30.10 "hostname && uptime"

# Resultat attendu :
# target-vm
# up 2 hours, 30 minutes
```

### 4.4 Configurer SSH pour la simplicite

Ajouter dans `~/.ssh/config` sur le Manager :

```bash
cat >> ~/.ssh/config << 'EOF'

Host target
    HostName 192.168.30.10
    User vboxuser
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
EOF
```

Desormais, le Manager peut faire `ssh target <commande>` au lieu de
`ssh vboxuser@192.168.30.10 <commande>`.

### 4.5 Tester les commandes sudo a distance

```bash
# Tester sudo sans mot de passe
ssh target "sudo whoami"
# -> doit afficher "root"

# Si ca demande un mot de passe, configurer sudoers sur la Target :
ssh target "echo 'vboxuser ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/vboxuser"
```

---

## 5. Installation de la Gateway OpenClaw (Manager)

### 5.1 Installer OpenClaw

```bash
# Sur le Manager
ssh vboxuser@192.168.30.3

curl -sL https://openclaw.ai/install.sh | bash
openclaw --version
```

### 5.2 Configurer la Gateway

```bash
# Lancer la configuration guidee (repondre aux questions)
openclaw configure

# Questions et reponses attendues :
# - Modle par defaut : deepseek/deepseek-v4-flash (ou celui utilise)
# - Provider : deepseek
# - Cle API DeepSeek : <ta_cle>
# - Gateway port : 18789 (laisser par defaut)
# - Gateway bind : LAN (pour le dashboard)
# - Gateway auth mode : token (choisir)
# - Token : laisser OpenClaw en generer un (ou mettre le tien)
# - Channel Telegram : oui
#   -> Bot token : <token_de_@Maxime205_bot>
#   -> DM policy : pairing
```

**Alternative : configuration manuelle**

Si tu preferes configurer le fichier directement :

```bash
# Editer la config
nano ~/.openclaw/openclaw.json
```

Contenu attendu :

```json
{
  "gateway": {
    "port": 18789,
    "bind": "lan",
    "auth": {
      "mode": "token",
      "token": "***"
    }
  },
  "providers": {
    "deepseek": {
      "apiKey": "***"
    }
  },
  "channels": {
    "telegram": {
      "accounts": {
        "default": {
          "botToken": "***"
        }
      }
    }
  },
  "agents": {
    "defaults": {
      "model": "deepseek/deepseek-v4-flash"
    }
  },
  "tools": {
    "elevated": {
      "enabled": true
    }
  }
}
```

### 5.3 Installer le service systemd

```bash
# Installer la Gateway comme service systemd
openclaw gateway install

# Demarrer
openclaw gateway start

# Verifier
openclaw gateway status
# -> doit afficher "running"
```

### 5.4 Configurer le control UI (basePath optionnel)

Si le dashboard doit etre accessible via un sous-chemin (ex: /lab/) :

```bash
openclaw config set gateway.controlUi.basePath "/"
# ou rien = racine
```

### 5.5 (Optionnel) Auto-pairing pour le dashboard

```bash
# Pour eviter le pairing a chaque connexion au dashboard
openclaw config set gateway.controlUi.allowInsecureAuth true
```

---

## 6. Migration du bot Telegram @Maxime205_bot

### 6.1 Recuperer le token Telegram

Le token du bot @Maxime205_bot est stocke dans la config OpenClaw du WSL.

**Methode 1 :** Depuis le fichier de config WSL :

```bash
# Dans le WSL
cat ~/.openclaw/openclaw.json | grep -A2 telegram
# Copier le botToken (format : "123456:ABCdef...")
```

**Methode 2 :** Depuis BotFather (Telegram) :

```bash
# Ouvrir Telegram, DM @BotFather
# Commande : /mybots
# Selectionner @Maxime205_bot
# -> API Token
```

### 6.2 Configurer le token sur le Manager

Si tu n'as pas configure Telegram pendant `openclaw configure` :

```bash
openclaw config set 'channels.telegram.accounts.default.botToken' "***"
# OU utiliser la commande channels
openclaw channels login --channel telegram
# Coller le token quand demande
```

### 6.3 Redemarrer la Gateway

```bash
openclaw gateway restart
openclaw channels status --probe
# -> Telegram doit etre "connected"
```

### 6.4 Tester le bot

Envoyer un message a @Maxime205_bot sur Telegram :
```
/ping
```

### 6.5 (Important) Que faire de l'ancienne instance WSL ?

Une fois la migration confirmee, arreter l'ancienne Gateway WSL :

```bash
# Sur le WSL — NE PAS FAIRE TANT QUE LE MANAGER N'EST PAS VALIDE
openclaw gateway stop
openclaw gateway uninstall
```

**Mais garder les donnees WSL accessibles** au cas ou (session history,
fichiers de config) :

```bash
# Option : faire un backup avant de supprimer
tar czf ~/backup_openclaw_wsl.tar.gz ~/.openclaw/
```

---

## 7. Deploiement du ML Sidecar

### 7.1 Installer les dependances Python

```bash
# Sur le Manager
sudo apt install python3-pip -y

# Installer les paquets ML
sudo pip3 install xgboost fastapi uvicorn \
  --break-system-packages \
  --ignore-installed typing-extensions
```

### 7.2 Deployer les fichiers

```bash
# Cloner le repo
git clone https://github.com/maraa081/wazuh-test.git /home/vboxuser/wazuh-test

# Creer le dossier du sidecar
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

# Base de donnees
sudo touch /tmp/predictions.db
sudo chmod 666 /tmp/predictions.db
```

### 7.3 Creer les services systemd

```bash
# Service d'inference
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

# Activer
sudo systemctl daemon-reload
sudo systemctl enable wazuh-inference wazuh-api
sudo systemctl start wazuh-inference
sleep 5
sudo systemctl start wazuh-api
```

### 7.4 Verifier le ML

```bash
# Services
systemctl is-active wazuh-inference wazuh-api
# -> active active

# API Health
curl -s http://127.0.0.1:9090/health
# -> {"status":"ok"}

# Modele charge
curl -s http://127.0.0.1:9090/model/status
# -> {"model_loaded":true,...}

# Predictions
curl -s http://127.0.0.1:9090/predictions/recent?limit=3
# -> [...] (liste vide ou predictions)
```

---

## 8. Tests de validation (Ping/Pong)

### 8.1 Test 1 : La Gateway OpenClaw repond

Depuis Telegram, envoyer au bot @Maxime205_bot :
```
/ping
```
→ Reponse attendue : `Pong!` ou message de bienvenue.

### 8.2 Test 2 : Le Control UI est accessible

Depuis le navigateur Windows :
```
http://192.168.30.3:18789
```
→ La page d'accueil OpenClaw doit s'afficher.

### 8.3 Test 3 : SSH vers la Target

Depuis le chat Telegram, demander a l'agent :
```
exec command="ssh target hostname"
```
→ L'agent doit repondre avec `target-vm` ou le hostname de la Target.

### 8.4 Test 4 : Pipeline ML

```
exec command="curl -s http://127.0.0.1:9090/health"
```
→ L'agent doit repondre avec le status JSON de l'API ML.

### 8.5 Test 5 : Campagne complete (SSH + ML)

```
exec command="ssh target 'echo PONG_TARGET && hostname && uptime -p'"
```
→ L'agent doit afficher PONG_TARGET, le hostname, et l'uptime.

---

## 9. Orchestration SSH : lancer des commandes sur la Target

### 9.1 Principe

Depuis le chat Telegram (ou le dashboard WebChat), l'agent OpenClaw
execute des commandes sur la Target en utilisant `exec` avec SSH :

```
exec command="ssh target <commande>"
```

L'agent a acces a la cle SSH configuree en section 4. Il peut donc
lancer n'importe quelle commande sur la Target.

### 9.2 Commandes usuelles

```bash
# Verifier Suricata
exec command="ssh target 'sudo suricata -T -c /etc/suricata/suricata.yaml'"

# Voir les alertes Suricata
exec command="ssh target 'sudo tail -n 20 /var/log/suricata/fast.log'"

# Lister les conteneurs Docker
exec command="ssh target 'sudo docker ps -a --format \"table {{.Names}}\t{{.Status}}\"'"

# Lancer une campagne d'attaque (600 secondes)
exec command="ssh target 'cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration 600'"

# Verifier l'agent Wazuh
exec command="ssh target 'sudo systemctl status wazuh-agent | head -5'"

# Collecter les logs eve.json
exec command="ssh target 'sudo tail -n 100 /var/log/suricata/eve.json | python3 -m json.tool'"
```

### 9.3 Sequences orchestrees

**Sequence type : Campagne + Collecte + Inference :**

```
1. Lance la campagne sur la Target
   exec command="ssh target 'cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration 300'"

2. Attends la fin de la campagne (ou quelques minutes)
   (l'agent attend ou tu dis "continue")

3. Collecte les alertes Wazuh sur le Manager
   exec command="mkdir -p /tmp/campaign_$(date +%Y%m%d) && cp /var/ossec/logs/alerts/alerts.json /tmp/campaign_$(date +%Y%m%d)/alerts_snapshot.json && wc -l /tmp/campaign_$(date +%Y%m%d)/alerts_snapshot.json"

4. Verifie les predictions ML
   exec command="curl -s http://127.0.0.1:9090/predictions/recent?limit=5"
```

### 9.4 Securite SSH

La cle privee est stockee dans `~/.ssh/id_ed25519` sur le Manager.
L'agent OpenClaw peut y acceder via `exec` (shell). Il n'y a pas de
risque d'exfiltration puisque l'agent n'a pas acces aux outils
d'envoi de fichiers a l'exterieur.

Pour renforcer la securite, on peut restreindre les commandes SSH
dans `authorized_keys` sur la Target :

```
# Sur la Target, dans ~/.ssh/authorized_keys
command="/home/vboxuser/ssh-gate.sh" ssh-ed25519 AAA...
```

Mais dans un contexte de labo, ce n'est pas necessaire.

---

## 10. Usage quotidien

### 10.1 Depuis Telegram

Exemples de choses que tu peux demander a @Maxime205_bot :

```
@veille lance une campagne de 5 minutes sur la Target
```

```
@veille verifie que Suricata tourne bien
```

```
@veille collecte les dernieres alertes et donne moi le statut du modele IA
```

```
@veille redemarre l'API ML
```

### 10.2 Depuis le Control UI (dashboard web)

`http://192.168.30.3:18789` → WebChat integre.
Tu peux discuter avec l'agent depuis le navigateur Windows,
avec du rendu riche (tableaux, graphiques).

### 10.3 Automatisation cron

```bash
# Creer une tache planifiee : verification matinale
openclaw cron add \
  --name "lab-daily-check" \
  --schedule '{"kind":"cron","expr":"0 8 * * *","tz":"Europe/Paris"}' \
  --payload '{"kind":"systemEvent","text":"Executer healthcheck du labo Wazuh : verifier Manager, Target, ML inference"}'
```

---

## 11. Scripts d'automatisation

### 11.1 Script : `lab-campaign.sh`

A placer sur le Manager dans `/home/vboxuser/scripts/` :

```bash
#!/bin/bash
# lab-campaign.sh — Orchestration campagne via SSH
# Usage : ./lab-campaign.sh <duree_secondes>

DURATION=${1:-300}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARGET_SCRIPT="/home/vboxuser/wazuh-test/traffic-generator/main.py"

echo "[$(date +%H:%M:%S)] === CAMPAGNE $TIMESTAMP (${DURATION}s) ==="

# Phase 1 : Verifier que la Target est joignable
echo "[1/4] Verification de la Target..."
ssh target "hostname" || { echo "[FAIL] Target injoignable"; exit 1; }
echo "[OK] Target connectee"

# Phase 2 : Lancer la campagne
echo "[2/4] Lancement de la campagne (${DURATION}s)..."
ssh target "cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --duration $DURATION"
echo "[OK] Campagne terminee"

# Phase 3 : Collecter les alertes
echo "[3/4] Collecte des alertes..."
mkdir -p /tmp/campaign_$TIMESTAMP
cp /var/ossec/logs/alerts/alerts.json /tmp/campaign_$TIMESTAMP/alerts_snapshot.json
ALERTS=$(wc -l < /tmp/campaign_$TIMESTAMP/alerts_snapshot.json)
echo "[OK] $ALERTS alertes collectees"

# Phase 4 : Verifier les predictions
echo "[4/4] Verification du pipeline ML..."
curl -s http://127.0.0.1:9090/health
echo ""
echo "[OK] ML API fonctionnelle"

echo ""
echo "=== CAMPAGNE TERMINEE ==="
echo "Alertes : $ALERTS"
echo "Dossier : /tmp/campaign_$TIMESTAMP"
```

### 11.2 Script : `lab-healthcheck.sh`

```bash
#!/bin/bash
# lab-healthcheck.sh — Etat du labo en un coup d'oeil

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
PASS=0
FAIL=0

check() {
  if [ $2 -eq 0 ]; then
    echo -e "  ${GREEN}[OK]${NC} $1"
    PASS=$((PASS+1))
  else
    echo -e "  ${RED}[FAIL]${NC} $1"
    FAIL=$((FAIL+1))
  fi
}

echo "========================================="
echo "   LAB HEALTHCHECK — $(date '+%Y-%m-%d %H:%M')"
echo "========================================="
echo ""

# --- Gateway OpenClaw ---
echo "[Gateway]"
systemctl is-active openclaw-gateway >/dev/null 2>&1
check "Service Gateway" $?
curl -s -o /dev/null -w "" http://127.0.0.1:18789/ 2>/dev/null
check "Port 18789 repond" $?

# --- SSH Target ---
echo "[Target (SSH)]"
ssh -o ConnectTimeout=3 target "hostname" >/dev/null 2>&1
check "SSH joignable" $?

ssh target "sudo systemctl is-active suricata" >/dev/null 2>&1
check "Suricata actif" $?

ssh target "sudo docker info >/dev/null 2>&1"
check "Docker fonctionnel" $?

# --- ML Sidecar ---
echo "[ML Pipeline]"
systemctl is-active wazuh-inference >/dev/null 2>&1
check "Inference Service" $?
systemctl is-active wazuh-api >/dev/null 2>&1
check "API Service" $?

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9090/health 2>/dev/null)
[ "$HEALTH" = "200" ]
check "API ML (HTTP $HEALTH)" $?

# --- Securite ---
echo "[Securite]"
sudo ufw status | grep -q "active"
check "UFW actif" $?
sudo ufw status | grep -q "192.168.30.1.*18789"
check "Regle UI Windows OK" $?

# --- Bilan ---
echo ""
echo "========================================="
echo "   $PASS OK / $FAIL FAIL"
echo "========================================="
exit $FAIL
```

---

## 12. Depannage

### 12.1 La Gateway ne demarre pas

```bash
# Verifier les logs
journalctl -u openclaw-gateway -n 50 --no-pager

# Verifier le port
ss -tlnp | grep 18789

# Verifier la config
openclaw config validate
```

### 12.2 Pas de connexion Telegram

```bash
# Verifier le statut du channel
openclaw channels status --probe

# Si token invalide :
openclaw config get channels.telegram.accounts.default.botToken
# Recuperer un nouveau token depuis @BotFather
openclaw config set channels.telegram.accounts.default.botToken "nouveau_token"
openclaw gateway restart
```

### 12.3 SSH vers la Target ne marche pas

```bash
# Depuis le Manager, tester :
ssh -v target "hostname" 2>&1 | tail -20
# Si "Permission denied" : verifier authorized_keys sur Target
# Si "Connection refused" : verifier UFW sur Target (sudo ufw status)
# Si "Host key mismatch" : ssh-keygen -R 192.168.30.10
```

### 12.4 Le bot ne repond plus apres migration

```bash
# 1. Verifier que l'ancienne instance WSL est bien arretee
#    (sinon les deux Gateways se battent pour le bot Telegram)

# 2. Forcer la reconnexion Telegram
openclaw gateway restart
sleep 5
openclaw channels status --probe

# 3. Envoyer /start a @Maxime205_bot
```

### 12.5 UFW bloque tout (meme Windows)

Si tu t'es verrouille :

```bash
# Depuis la console VirtualBox (ouverture directe)
sudo ufw disable
# Puis corriger les regles
sudo ufw --force reset
# Re-appliquer les bonnes regles
```

### 12.6 Le modele ML ne charge pas

```bash
# Verifier les fichiers
ls -la /opt/wazuh-ml/xgb_model.json
python3 -c "
import json
with open('/opt/wazuh-ml/xgb_model_metrics.json') as f:
    m = json.load(f)
print('Features:', len(m.get('feature_names', [])))
print('ROC AUC:', m.get('roc_auc', 'N/A'))
"

# Redemarrer le service
sudo systemctl restart wazuh-inference
sleep 3
sudo systemctl restart wazuh-api
journalctl -u wazuh-inference -n 30 --no-pager
```

---

## 13. Checklist de validation finale

### 13.1 Infrastructure
- [ ] Manager UFW actif et restrictif
- [ ] Target UFW actif et restrictif
- [ ] ParrotOS bloque (verifie : ssh depuis ParrotOS echoue)
- [ ] Windows peut acceder a Manager:18789
- [ ] Manager peut SSH sans mot de passe sur Target

### 13.2 Gateway OpenClaw
- [ ] Gateway installee et running (`openclaw gateway status`)
- [ ] Bot Telegram @Maxime205_bot connecte
- [ ] Control UI accessible depuis Windows (`http://192.168.30.3:18789`)
- [ ] `/ping` sur Telegram repond

### 13.3 SSH Target
- [ ] `ssh target hostname` retourne le bon hostname
- [ ] `ssh target 'sudo whoami'` retourne "root"
- [ ] `ssh target 'sudo docker ps'` fonctionne
- [ ] `ssh target 'sudo suricata -T -c /etc/suricata/suricata.yaml'` OK

### 13.4 ML Pipeline
- [ ] wazuh-inference actif
- [ ] wazuh-api actif
- [ ] `curl http://127.0.0.1:9090/health` retourne 200
- [ ] Modele charge (`/model/status` → model_loaded: true)
- [ ] Predictions accessibles (`/predictions/recent`)

### 13.5 Tests finaux
- [ ] Demander a l'agent : "execute hostname sur la Target" → OK
- [ ] Demander a l'agent : "quel est le statut du pipeline ML ?" → OK
- [ ] Demander a l'agent : "lance une campagne de 60 secondes" → OK
- [ ] Script `lab-healthcheck.sh` : tout vert

---

## Annexe A : References

- [OpenClaw Docs — Gateway Setup](/start/getting-started)
- [OpenClaw Docs — Configuration reference](/gateway/configuration-reference)
- [OpenClaw Docs — Telegram channel](/channels/telegram)
- [OpenClaw Docs — Control UI](/web/control-ui)
- [Projet GitHub — wazuh-test](https://github.com/maraa081/wazuh-test)
- [Journal de bord](docs/JOURNAL_DE_BORD.md)
- [Ancien plan agents OpenClaw](docs/PLAN_AGENTS_OPENCLAW.md)
- [Charte de developpement](docs/DEVELOPMENT_CHARTER.md)

## Annexe B : Architecture des repertoires

```
Manager (~/.openclaw/)
├── openclaw.json         # Configuration Gateway
├── node.json             # (inutilise dans cette archi)
├── sessions/             # Historique des conversations
└── agents/
    └── main/
        └── agent/
            └── auth-profiles.json

Manager (/opt/wazuh-ml/)
├── inference_service.py  # Service d'inference ML
├── api_service.py        # API REST :9090
├── xgb_model.json        # Modele entraine
└── xgb_model_metrics.json # Metriques + features

Manager (~/.ssh/)
├── id_ed25519            # Cle privee (Manager -> Target)
├── id_ed25519.pub        # Cle publique
└── config                # Alias "target"

Target (~/.ssh/)
└── authorized_keys       # Contient la cle publique du Manager
```

## Annexe C : Comparaison des architectures

| Criteres | Ancienne (WSL + Nodes) | Nouvelle (Manager + SSH) |
|----------|----------------------|------------------------|
| Nombre de machines | 3 (WSL + 2 VMs) | 2 (Manager + Target) |
| Portproxy Windows | Oui (fragile) | NON (plus de dependance) |
| IP variable WSL | Oui (reboot = casse) | NON (IP fixe) |
| Compte Telegram | 1 bot | 1 bot (identique) |
| Orchestration | Nodes natifs | SSH (tres stable) |
| Complexite reseau | Haute | Faible |
| Dashboard | WSL via proxy | Direct 192.168.30.3:18789 |
| Securite ParrotOS | Portproxy a filtrer | UFW + loopback partiel |
