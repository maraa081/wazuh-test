# Suricata + Wazuh AI Filter — Notes de déploiement

## Résumé du problème

L'installation de Suricata sur la cible a échoué en boucle pendant des heures
parce que plusieurs causes s'accumulaient. Chaque fix en révélait une nouvelle.
Voici l'ordre réel des causes, de la plus évidente à la plus cachée.

## Causes identifiées (dans l'ordre de résolution)

### 1. Mauvaise interface de capture
**Symptôme :** 0 alertes, Suricata voit du trafic (flows) mais rien ne déclenche.
**Cause :** Suricata écoutait sur `eth0` (inexistant) ou `enp0s3` (NAT), mais le
trafic des attaquants arrive sur `enp0s8` (Bridged, 192.168.30.x).
**Solution :** Configurer `af-packet → interface: enp0s8` dans suricata.yaml.

### 2. Fichier de règles local.rules au mauvais endroit
**Symptôme :** Les règles custom ne s'appliquent pas, 0 alertes des règles
pourtant créées.
**Cause :** `default-rule-path` pointe vers `/var/lib/suricata/rules/` mais
local.rules était créé dans `/etc/suricata/rules/`. Suricata ne le voyait pas.
**Solution :** Copier local.rules dans `/var/lib/suricata/rules/`.

### 3. HOME_NET pas aligné avec le réseau réel
**Symptôme :** Les règles utilisant `$HOME_NET` ne matchent pas.
**Cause :** HOME_NET configuré sur `[10.0.0.0/8]` (NAT) alors que l'interface
de capture est en 192.168.30.0/24 (Bridged). Les règles `$EXTERNAL_NET ->
$HOME_NET` ne voyaient pas le trafic destiné à 192.168.30.10.
**Solution :** HOME_NET doit être le sous-réseau de l'interface de capture :
`[192.168.30.0/24]`.

### 4. Seuils trop élevés dans les règles
**Symptôme :** Les règles Nmap avec `threshold: count 10` ne déclenchaient pas
sur un simple `nmap -sS -p 22,80`.
**Cause :** Un scan rapide sur 2 ports ne génère que 2-3 paquets SYN. La règle
en demandait 10.
**Solution :** Abaisser le threshold à `count 3` pour capturer les scans légers.

### 5. Portscan module paramètres par défaut trop laxistes
**Symptôme :** Le module portscan (événements `event_type: "portscan"`)
ne déclenchait rien.
**Cause :** `scan-lookup: 100` et `scan-threshold: 500` = besoin de 100 paquets
en 500ms. Trop pour un scan rapide.
**Solution :** Passer à `scan-lookup: 20`, `scan-threshold: 100`.

### 6. Mode promiscuité OFF
**Symptôme :** manque de paquets visibles.
**Cause :** Sur interface Bridgée, pas toujours automatique.
**Solution :** `ip link set enp0s8 promisc on`.

### 7. Doublon local.rules dans rule-files
**Symptôme :** Avertissement au démarrage, comportement imprévisible.
**Cause :** Le script fix avait ajouté une deuxième entrée `- local.rules`.
**Solution :** Nettoyer les doublons dans la section rule-files.

## Le vrai « piège »

Le **piège principal** qui a fait durer le debug : Suricata rapportait
`51979 rules successfully loaded` avec 0 erreurs, alors que les règles
n'étaient PAS chargées. Il chargeait juste les règles ET (suricata.rules),
ignorait silencieusement local.rules (mauvais path), et les règles ET
n'ont pas de règles scan Nmap déclenchables en l'état. Résultat : aucun
message d'erreur, juste 0 alertes.

## Procédure de vérification rapide pour l'avenir

Si un nouveau déploiement Suricata ne détecte rien :

1. `suricata -T -c /etc/suricata/suricata.yaml` → test config
2. Vérifier que les règles custom sont dans le bon `default-rule-path`
3. Vérifier HOME_NET correspond au réseau de l'interface de capture
4. Vérifier que l'interface af-packet est la bonne
5. Vérifier `ip link show <interface>` pour PROMISC
6. Vérifier les thresholds des règles (trop élevés = pas déclenchées)
7. `tail -f /var/log/suricata/fast.log` pendant un test nmap
