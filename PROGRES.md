# Progres du projet Wazuh AI Filter

Derniere mise a jour : 2026-07-13 01:05

## Infrastructure lab

- **Machine cible (Debian Bookworm)** : vboxuser@192.168.30.4, Wazuh agent installe
- **Kali Linux** : generation des attaques
- **Wazuh manager** : sur "UbuntuWazuh", nom d'hote "vbox"
- **Suricata** : installe sur la cible, ecoute sur `enp0s8` (Host-Only, 192.168.30.4)
  - Depot OISF ajoute, regles ET chargees (51968 regles)
  - Fichier eve.json integre dans ossec.conf de Wazuh
  - Capte les paquets (kernel_packets > 0), **0 alertes detectees**
  - Cause probable : Kali est en NAT (10.0.2.x), le trafic ne passe pas par enp0s8
- **Probleme connu** : Kali a perdu son reseau NAT apres tentative de bascule en Host-Only

## Repo GitHub

maraa081/wazuh-test (public)
- `traffic-generator/` : generateur de trafic multi-classe pour Kali
  - 9 modules (4 malveillants, 5 benignes)
  - main.py orchestre avec ratio 70/30
  - config.yaml.example avec les bons parametres lab
  - setup_suricata_cible.sh (Ubuntu) et setup_suricata_debian.sh (Debian Bookworm)
- `config/` : configuration du pipeline AI
  - config.yaml, attack_mapping.yaml (SSH bruteforce + Nmap)
- `pipeline/` : stubs des 5 etapes (collecte a evaluation)
- `service/` : stubs du wrapper externe (inference + API)

## Prochaines etapes (a faire)

1. Reseau Kali : soit repasser en NAT, soit configurer Host-Only correctement
2. Suricata : verifier que les alertes remontent (eve.json avec "alert")
3. Wazuh : recuperer echantillon d'alertes pour caler les parsers
4. Phase 1 du pipeline : ecrire la librairie partagee + 01_collect_alerts.py
