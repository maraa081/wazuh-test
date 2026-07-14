# Journal de bord — Projet Wazuh AI Filter

## Résumé des difficultés rencontrées

Ce document recense l'ensemble des problèmes, bugs et difficultés
rencontrées pendant le développement du projet, de l'installation de
Suricata jusqu'au déploiement du sidecar ML.

---

## 1. Problèmes réseau VirtualBox

### 1.1 Kali en NAT, Suricata sur Host-Only

**Date :** 2026-07-13 (session initiale)

**Situation :** Kali était en NAT (10.0.2.x), Suricata était configuré pour
écouter sur enp0s8 (Host-Only, 192.168.30.x). Les paquets Nmap arrivaient
sur enp0s3 (NAT) mais Suricata regardait enp0s8.

**Solution :** Ajouter `- interface: enp0s3` dans la section af-packet de
suricata.yaml. Ensuite Suricata voyait les paquets des deux interfaces.

**Piège :** Pendant des heures on a cru que Suricata ne détectait rien
à cause des règles, alors que le problème était purement réseau.

### 1.2 Kali a perdu son réseau NAT

**Date :** 2026-07-13 (début de session)

**Situation :** Après avoir tenté de basculer Kali en Host-Only, le réseau
NAT a été perdu. Kali n'avait plus d'accès à Internet ni à la cible.

**Solution :** Maraa a reconfiguré Kali avec les deux réseaux (NAT + Host-Only)
dans VirtualBox. Le trafic vers la cible passe par le NAT.

### 1.3 Impossibilité d'accéder aux VMs depuis WSL

**Date :** Permanent

**Situation :** OpenClaw tourne sur WSL2 (172.31.240.x). Les VMs sont sur
VirtualBox Host-Only (192.168.30.x). Pas de routage entre les deux réseaux.

**Conséquence :** Impossible d'exécuter des scripts directement sur les VMs.
Tout doit passer par l'utilisateur qui copie-colle les commandes.

---

## 2. Problèmes d'installation et configuration Suricata

### 2.1 Suricata ne détectait aucun scan Nmap

**Date :** 2026-07-13 (toute la session)

**Causes cumulées (7 problèmes identifiés) :**

| # | Problème | Cause |
|---|----------|-------|
| 1 | Mauvaise interface | Suricata écoutait sur `eth0` (inexistant) ou enp0s3 au lieu de enp0s8 |
| 2 | Règles custom au mauvais endroit | `local.rules` créé dans `/etc/suricata/rules/` mais `default-rule-path` pointe vers `/var/lib/suricata/rules/` |
| 3 | HOME_NET pas aligné | Configuré sur `[10.0.0.0/8]` (NAT) mais interface de capture en 192.168.30.0/24 |
| 4 | Seuils trop élevés | `threshold: count 10` pour les règles Nmap → besoin de 10 SYN packets pour déclencher, mais un petit scan n'en génère que 2-3 |
| 5 | Module portscan pas configuré | Section `portscan:` absente de suricata.yaml |
| 6 | Promiscuité OFF | Sur interface bridgée, pas détecté automatiquement |
| 7 | Doublon local.rules | `- local.rules` listé deux fois dans rule-files |

**Solution finale :**
- Interface : `enp0s8`
- HOME_NET : `[192.168.30.0/24]`
- Seuils : `count 3` au lieu de `count 10`
- Portscan : `scan-lookup: 20, scan-threshold: 100`
- Promiscuité : `ip link set enp0s8 promisc on`
- Règles custom dans `/var/lib/suricata/rules/local.rules`

**Piège vicieux :** Suricata rapportait `51979 rules loaded, 0 errors` alors
que les règles custom étaient **silencieusement ignorées** (mauvais dossier).
Pas d'erreur, pas de warning. Zéro alerte.

### 2.2 Le module portscan ne générait pas d'events dans eve.json

**Date :** 2026-07-13

**Situation :** Le module `portscan` était configuré mais ne produisait
aucun event `event_type: "portscan"` dans eve.json. Les types présents
étaient uniquement `dhcp, flow, stats`.

**Cause :** `portscan` n'était pas listé dans les `types:` de la section
`eve-log`. Seul `alert` était présent.

**Solution :** Ajouter `- portscan` dans la section `types:` de `eve-log`.

### 2.3 Les règles scan existaient mais ne s'activaient pas

**Date :** 2026-07-13

**Situation :** 654 règles scan/Nmap dans suricata.rules, mais aucune ne
déclenchait. Les règles portscan dans ET Open sont des règles HTTP/app-layer,
pas des règles de scan SYN pures.

**Solution :** Ajouter des règles custom qui matchent les SYN packets avec
`flow:stateless;`. Les règles ET officielles ne détectent pas les SYN scans
bruts.

---

## 3. Problèmes Wazuh

### 3.1 L'agent Wazuh ne remontait pas les alertes d'auth SSH

**Date :** 2026-07-13

**Situation :** Sur l'ancienne cible Debian, les tentatives SSH (hydra)
étaient visibles dans `journalctl` mais pas dans le Wazuh Manager.

**Cause :** L'agent lisait `journald` via `<log_format>journald</log_format>`,
mais les logs SSH (`auth.log`) n'étaient pas dans syslog. Debian Bookworm
utilise journald par défaut, pas rsyslog.

**Solution :** L'agent avait déjà `<log_format>journald</log_format>` dans
ossec.conf, il lisait bien les logs SSH. Le problème était ailleurs :
hydra ne générait pas assez de tentatives pour déclencher les règles Wazuh
(règle 5710 : besoin de X tentatives en Y secondes).

### 3.2 L'API Wazuh retournait 404 sur /security/alerts

**Date :** 2026-07-13 (nuit)

**Situation :** Le collecteur `01_collect_alerts.py` tentait d'utiliser
l'API Wazuh sur le port 55000. Les endpoints `/security/alerts` et
`/alerts` retournaient tous les deux 404.

**Cause :** Dans Wazuh 4.14.6-1, l'endpoint pour les alertes est accessible
via l'API OpenSearch (port 9200), pas via l'API Wazuh (port 55000). Mais
le Manager était en All-in-One, l'indexeur OpenSearch était configuré.

**Solution :** Lire directement le fichier `/var/ossec/logs/alerts/alerts.json`
en local, plutôt que de passer par l'API REST.

### 3.3 Wazuh-wui API password non trouvé

**Date :** 2026-07-13 (nuit)

**Situation :** Impossible d'authentifier l'API Wazuh. Les credentials
étaient stockés dans un fichier tar (`wazuh-install-files.tar`) créé
pendant l'installation.

**Solution :** Extraire le tar :
```bash
sudo tar xvf /home/vboxuser/wazuh-install-files.tar -C /tmp/
sudo cat /tmp/wazuh-install-files/wazuh-passwords.txt
```

---

## 4. Problèmes Docker

### 4.1 Boucle de nommage des conteneurs

**Date :** 2026-07-13 (soir)

**Situation :** Le script `run-campaign.sh` modifiait la variable de boucle
`$i` à l'intérieur de la logique d'attribution des profils. Cela détruisait
l'incrémentation de la boucle principale, provoquant des collisions de noms
(agent-001 en boucle).

**Solution :** Utiliser une variable d'index séparée `cid` qui s'incrémente
à chaque passage, sans toucher à la variable de boucle `$i`.

### 4.2 Date de fin UTC non portable

**Date :** 2026-07-13 (soir)

**Situation :** La commande `date -d "+600 seconds"` échouait selon les
environnements.

**Solution :** Utiliser le timestamp Epoch :
```bash
END_UTC=$(date -u -d "@$(($(date +%s) + CAMPAIGN_DURATION))" +"%Y-%m-%dT%H:%M:%SZ")
```

### 4.3 Connexions SSH inter-conteneurs

**Date :** 2026-07-13 (soir)

**Situation :** Les conteneurs bénins tentaient du SSH vers d'autres
conteneurs. L'image Alpine n'a pas de serveur SSH. Résultat : des flots
de "Connection Refused" (TCP RST) massifs, qui ressemblent à un scan
réseau pour l'IA.

**Solution :** Modifier `benign_ssh` pour ne cibler QUE le Wazuh Manager
(192.168.30.3), qui a un service SSH actif.

---

## 5. Problèmes du pipeline ML

### 5.1 Scripts avec caractères Unicode sur les VMs

**Date :** 2026-07-13/14 (nocturne)

**Situation :** Tous les scripts Python avec des caractères Unicode
(═, →, —, ➔, ✔, ❌) plantaient avec l'erreur :
```
UnicodeEncodeError: 'latin-1' codec can't encode character
```
sur les VMs Ubuntu (serveur en locale latin-1).

**Solution :** Convertir tous les scripts en ASCII strict :
```bash
c = open(f).read().encode('ascii', 'replace').decode('ascii')
```

**Leçon :** Ne JAMAIS utiliser de caractères non-ASCII dans les scripts.
Utiliser `====` au lieu de `════`, `->` au lieu de `→`.

### 5.2 Cache CDN GitHub pas à jour

**Date :** Permanent

**Situation :** Les commandes `curl -sL https://raw.githubusercontent.com/...`
retournaient systématiquement une version périmée des fichiers. Le cache
CDN de GitHub peut prendre plusieurs minutes (parfois > 1h) à se rafraîchir.

**Conséquence :** Les scripts pushés étaient invisibles pendant 15-30 min.
On a perdu un temps considérable à debugger des bugs déjà corrigés.

**Solution :** Créer les fichiers avec `cat << 'EOF' >` directement sur
la VM, ou cloner le repo en local et copier les fichiers.

### 5.3 Encodage du dataset labellisé

**Date :** 2026-07-13 (nuit)

**Situation :** Le script `02_label_dataset.py` produisait 0 TP car les
timestamps du CSV de campagne (format `+0200`) n'étaient pas parsés
correctement. La fonction `parse_iso` ne gérait pas le format sans deux-points.

**Solution :** Normaliser les timestamps avant parsing :
```python
s = s.strip().replace("Z","+00:00")
if "+" in s[10:] and ":" not in s[s.index("+")+1:]:
    s = s[:s.index("+")] + "+00:00"
```

### 5.4 Le modèle prédit toujours FP (conf=0.000)

**Date :** 2026-07-14 (nocturne)

**Situation :** Le modèle XGBoost chargé avec `load_model()` prédit
systématiquement FP avec une confiance de 0.000 pour toutes les alertes,
même celles clairement identifiées comme des scans.

**Causes identifiées :**

1. **Buffer de fréquence vide au démarrage :** Au lancement de l'inférence,
   le buffer était vide. Les features temporlles (`count_rule_1min`) étaient
   à 0 pour les premières milliers d'alertes → le modèle voyait "0 alertes
   en 1 minute" → classait tout en FP.

2. **Buffer incomplet (Suricata only) :** Le buffer était pré-populé depuis
   la base SQLite, qui ne contient que les prédictions Suricata. Mais
   l'entraînement utilisait toutes les alertes (sudo, PAM, SSH...) pour
   calculer les fréquences. Les features fréquence étaient différentes
   entre entraînement et inférence.

3. **Seuil du modèle trop élevé :** Le modèle ne prédit TP que quand
   `count_rule_1min > 150` (rafale massive). Une alerte normale avec
   `count_rule_1min = 5` est correctement prédite FP. Ce n'est pas un
   bug mais un comportement volontaire : le SIEM doit filtrer le bruit
   et ne signaler que les rafales.

4. **Rotation du fichier alerts.json par Wazuh :** Quand Wazuh rotate
   le fichier, le handle de fichier devient invalide → `I/O operation on
   closed file`. Pour l'instant pas encore totalement résolu.

**Solutions appliquées (dans inference_service.py) :**
- Buffer pré-populé depuis `alerts.json` (toutes les alertes, pas juste Suricata)
- Ajout de toutes les alertes au buffer en temps réel (Suricata + non-Suricata)
- Ajout au buffer APRES le calcul des features (pas avant, pour éviter
  l'auto-comptage)
- Le buffer.append dans extract() désactivé (doublon)

**Solution restante :** Gérer la rotation du fichier alerts.json en
fermant/réouvrant le fichier à chaque cycle.

---

## 6. Problèmes FastAPI

### 6.1 Décorateur dupliqué

**Date :** 2026-07-14 (nocturne)

**Situation :** L'API plantait au démarrage avec :
```
TypeError: unsupported operand type(s) for @: 'function' and 'function'
```

**Cause :** La fonction `get_recent()` a été remplacée par inline code,
mais une ligne `@app.get("/predictions/{alert_id}")` est restée dupliquée.

**Solution :** Supprimer la ligne dupliquée.

### 6.2 Paramètre Query FastAPI non sérialisable

**Date :** 2026-07-14 (nocturne)

**Situation :** `get_recent()` appelait `get_predictions(limit=limit, ...)`
en passant `limit` (un objet `Query` de FastAPI) comme paramètre. Celui-ci
était utilisé en SQLite, provoquant :
```
sqlite3.ProgrammingError: Error binding parameter 1: type 'Query' is not supported
```

**Solution 1 (temporaire) :** `get_recent(limit: int = 50)` sans `Query`.

**Solution 2 (propre) :** Utiliser `int(limit)` avant de passer à SQLite.

**Leçon :** Ne JAMAIS utiliser `Query(...)` comme type de paramètre dans
une fonction appelée par une autre fonction. Réserver `Query` uniquement
pour les endpoints exposés.

---

## 7. Problèmes d'environnement

### 7.1 apt install python3-pip vs pip3

**Date :** 2026-07-14 (nocturne)

**Situation :** Sur Ubuntu 24.04 (Manager), `pip3` n'était pas installé.
La commande `sudo pip3 install` échouait.

**Solution :** `sudo apt install python3-pip -y`

### 7.2 Conflits de paquets system vs pip

**Date :** 2026-07-14 (nocturne)

**Situation :** `pip3 install xgboost` échouait avec :
```
ERROR: Cannot uninstall typing_extensions 4.10.0, RECORD file not found.
```
car `typing-extensions` était installé par le paquet system Debian.

**Solution :** `sudo pip3 install xgboost --break-system-packages --ignore-installed typing-extensions`

### 7.3 Permission SQLite

**Date :** 2026-07-14 (nocturne)

**Situation :** L'inférence écrivait dans `/tmp/predictions.db` mais le
processus n'avait pas les droits. `attempt to write a readonly database`.

**Solution :** `chmod 666 /tmp/predictions.db`

### 7.4 Modèle sauvegardé avec feature_names vide

**Date :** 2026-07-14 (nocturne)

**Situation :** Le fichier `xgb_model.json` contient `"feature_names":[]`
(vide). Le modèle a été sauvegardé par `model.save_model()` qui n'inclut
pas les noms de features. Les prédictions se font par position.

**Solution :** Les feature_names sont stockées séparément dans
`xgb_model_metrics.json` et l'ordre du tableau numpy doit correspondre
exactement.

---

## Chronologie

| Date | Heure | Événement |
|------|-------|-----------|
| 2026-07-13 | 16:50 | Début de session, reprise projet Wazuh |
| 2026-07-13 | ~17:00 | Découverte : Suricata sur enp0s8 mais Kali en NAT |
| 2026-07-13 | ~18:00 | Fix réseau Suricata (enp0s3 + enp0s8) |
| 2026-07-13 | ~19:00 | Agent Wazuh sur nouvelle cible Ubuntu 22.04 |
| 2026-07-13 | ~19:15 | Suricata PPA installé, config HOME_NET corrigée |
| 2026-07-13 | ~19:30 | Règles Nmap custom + détection fonctionnelle |
| 2026-07-13 | ~20:00 | Campagne Docker V1 (100 conteneurs, 10 min) |
| 2026-07-13 | ~21:00 | Dataset collecté (41 221 alertes) |
| 2026-07-13 | ~21:30 | Labellisation V2 (9473 TP / 31748 FP) |
| 2026-07-13 | ~22:30 | Feature engineering (50 features) |
| 2026-07-13 | ~23:00 | XGBoost entraîné (98.5% recall, 0.999 ROC AUC) |
| 2026-07-13 | ~23:30 | Sidecar inference — premiers tests |
| 2026-07-14 | 00:15 | Déploiement sur le Manager |
| 2026-07-14 | 01:00 | Debug modèle (buffer vide → pré-population) |
| 2026-07-14 | 01:30 | Fix API + buffer + modèle |
| 2026-07-14 | 02:00 | Dernier bug : rotation alerts.json |
| 2026-07-14 | 02:09 | Arrêt — rédaction du journal |

---

## Leçons retenues

1. **Toujours vérifier le réseau en premier** (interface, NAT, promisc)
2. **Suricata peut dire "rules loaded" sans avoir chargé les règles** 
   (mauvais chemin = silence radio)
3. **Le buffer de fréquence doit être identique entre entraînement et inférence**
4. **Pas de caractères Unicode dans les scripts** (latin-1 sur les serveurs)
5. **Ne pas faire confiance au cache CDN GitHub** (créer les fichiers localement)
6. **Toujours caster les types avant SQLite** (surtout les Query FastAPI)
7. **Pré-populer le buffer au démarrage** (jamais de cold start)
8. **Tester la rotation de fichier** (Wazuh rotate alerts.json)
9. **Documenter les credentials** dans un endroit sûr (wazuh-install-files.tar)
10. **Ne jamais modifier les fichiers Wazuh** (Update-Proof)
