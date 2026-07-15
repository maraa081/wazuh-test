# Générateur de trafic pour le dataset Wazuh AI Filter

Génère un dataset de trafic multi-classe labellisé pour entraîner un
classifieur d'alertes Wazuh. S'exécute depuis **Kali Linux** (ou toute
machine Linux avec les bons outils) et cible une seule machine de labo
avec un agent Wazuh. La sortie est un fichier CSV avec des fenêtres
temporelles et des labels de classe, conçu pour alimenter le pipeline
de labellisation Wazuh AI Filter.

**ATTENTION :** Cet outil est conçu exclusivement pour des environnements
de labo isolés (VirtualBox, VMware, réseaux air-gapped). Ne jamais
l'exécuter contre une machine qui ne vous appartient pas ou sur un
réseau de production.

## Dépendances

### Paquets système (à installer sur Kali avant la première exécution)

```
sudo apt update
sudo apt install -y nmap hydra hping3 sshpass dnsutils curl openssh-client
```

### Paquets Python (minimaux)

```
pip install -r requirements.txt
```

Seul `pyyaml` est nécessaire ; tout le reste est un outil système standard.

## Configuration

1. Copier le fichier de configuration exemple :

   ```bash
   cp config.yaml.example config.yaml
   ```

2. Éditer `config.yaml` et définir :

   - `target_ip` — l'IP de votre machine cible du labo (IP unique, jamais une plage)
   - `target_ssh_user` / `target_ssh_pass` — un compte de test dédié sur la cible
   - `total_duration_seconds` — durée de chaque session (0 pour pas de limite)
   - `benign_ratio` — proportion de trafic bénin vs malveillant (défaut 0.7)

3. (Optionnel) Créer un compte `testuser` sur la machine cible :

   ```bash
   sudo useradd -m testuser
   sudo passwd testuser
   ```

4. Vérifier que vous pouvez atteindre la cible :

   ```bash
   ping -c 3 <ip_cible>
   ```

## Utilisation

```bash
python main.py --config config.yaml --duration 3600 --output labels.csv
```

- `--duration` : durée totale d'exécution en secondes (défaut 3600 = 1 heure)
- `--output`  : chemin du fichier CSV de labels (les données sont ajoutées)

Arrêter avec Ctrl+C. Le fichier CSV n'est pas corrompu par une interruption.

### Exécution autonome d'un module (debug)

Chaque module peut s'exécuter indépendamment :

```bash
python modules/port_scan.py --target 192.168.1.100 --out test.csv
python modules/benign_ssh.py --target 192.168.1.100 --out test.csv
python modules/bruteforce.py --target 192.168.1.100 --out test.csv
```

## Format de sortie : labels.csv

| Colonne             | Contenu                                          |
|---------------------|--------------------------------------------------|
| timestamp_start_iso | Début UTC du burst de trafic (ISO 8601)          |
| timestamp_end_iso   | Fin UTC du burst de trafic (ISO 8601)            |
| label_class         | Un des 9 labels de classe (voir ci-dessous)      |
| module_name         | Module Python qui a généré l'entrée              |
| tool_used           | Outil système invoqué (nmap, hydra, curl, etc.)  |
| target_ip           | IP cible (toujours la même pour une session)     |
| colonnes suppl.     | Infos spécifiques (type de scan, taille, etc.)   |

### Labels de classe

| Label               | Catégorie    | Description                          |
|---------------------|-------------|--------------------------------------|
| port_scan           | malveillant | Scan Nmap (SYN/complet/agressif)     |
| bruteforce          | malveillant | Tentative SSH par hydra              |
| dos_flood           | malveillant | Burst DOS court (SYN/ICMP/HTTP)      |
| exfiltration        | malveillant | Transfert SCP de gros fichier        |
| benign_web          | bénin       | Requêtes HTTP vers le serveur cible  |
| benign_dns          | bénin       | Requêtes DNS vers domaines courants  |
| benign_icmp         | bénin       | Paquets ping normaux                 |
| benign_filetransfer | bénin       | Transfert SCP de petit fichier       |
| benign_ssh          | bénin       | Connexion SSH légitime + commandes   |

## Architecture

```
main.py (orchestrateur)
  |
  |-- choisit un module (70% bénin / 30% malveillant)
  |-- pause aléatoire entre 5 et 30s
  |-- exécute le module -> enregistre dans labels.csv + logs/
  |
  modules/
  |-- port_scan.py       (nmap -sS / -sT / -A)
  |-- bruteforce.py      (hydra)
  |-- dos_flood.py       (hping3 / curl)
  |-- exfiltration.py    (scp -- gros fichier)
  |-- benign_web.py      (curl)
  |-- benign_dns.py      (dig)
  |-- benign_icmp.py     (ping)
  |-- benign_filetransfer.py (scp -- petit fichier)
  |-- benign_ssh.py      (ssh + commandes)
  |
  utils/
  |-- logger.py          (écriture CSV + gestion des logs)
  |
  logs/
  |-- (sorties stdout/stderr par module)
```

L'orchestrateur ne se soucie pas de ce que font les modules individuellement.
Il ne connaît que la répartition bénin/malveillant et les plages de pause.
Chaque module est autonome et peut être exécuté isolément pour le débogage.

## Comment cela alimente le Wazuh AI Filter

1. Exécuter le générateur de trafic sur Kali (ou la machine qui génère vos attaques).
2. Le trafic généré déclenche des alertes Wazuh sur la machine cible.
3. Le manager Wazuh stocke les alertes dans `/var/ossec/logs/alerts/alerts.json`.
4. Le pipeline Wazuh AI Filter lit ce fichier JSON, croise les timestamps
   des alertes avec labels.csv, et labellise chaque alerte en TP ou FP.
5. Le modèle est entraîné sur le dataset labellisé résultant.

## Notes de sécurité

- Le générateur de trafic ne scanne jamais de plages IP, n'utilise jamais
  --random-targets, et n'envoie jamais de trafic en dehors de l'IP cible configurée.
- Les bursts DOS sont limités à 20 secondes avec des débits bas configurables
  pour éviter de réellement dénier le service à la cible.
- Tous les identifiants sont lus depuis un fichier de config local (gitignoré).
  Utiliser un compte de test jetable sur la cible, jamais de vrais identifiants.
