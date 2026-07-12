#!/bin/bash
# Setup Suricata IDS + Wazuh integration sur Debian Bookworm
# A lancer en root sur la VM cible (Debian, VirtualBox)
# Rien a modifier

set -e

echo "=== Ajout du depot OISF pour Suricata ==="
sudo apt install -y curl gnupg
curl -fsSL https://packages.suricata.io/suricata.pub | sudo gpg --dearmor -o /usr/share/keyrings/suricata.gpg
echo "deb [signed-by=/usr/share/keyrings/suricata.gpg] https://packages.suricata.io/debian/ bookworm main" | sudo tee /etc/apt/sources.list.d/suricata.list

echo "=== Installation de Suricata ==="
sudo apt update
sudo apt install -y suricata

echo "=== Detection auto de l'interface reseau ==="
IFACE=$(ip -o link show | grep -v lo | awk -F': ' '{print $2}' | head -1)
echo "Interface detectee : $IFACE"

echo "=== Configuration Suricata ==="
sudo sed -i "s/^INTERFACE=.*/INTERFACE=$IFACE/" /etc/default/suricata

# Mode IDS et on desactive l'interface en mode af-packet
# On met l'interface auto-detectee pour le mode pcap
sudo sed -i "s/interface: eth0/interface: $IFACE/" /etc/suricata/suricata.yaml
sudo sed -i 's/# pcap:/pcap:/' /etc/suricata/suricata.yaml
sudo sed -i "s/#  interface: eth0/  interface: $IFACE/" /etc/suricata/suricata.yaml
sudo sed -i 's/#  threads: 1/  threads: 1/' /etc/suricata/suricata.yaml

echo "=== Demarrage Suricata ==="
sudo systemctl enable suricata
sudo systemctl restart suricata

echo "=== Integration Wazuh : ajout de eve.json dans ossec.conf ==="
if grep -q "eve.json" /var/ossec/etc/ossec.conf 2>/dev/null; then
    echo "  deja configure, on saute"
else
    sudo sed -i '/<\/ossec_config>/i\
<localfile>\
  <log_format>json<\/log_format>\
  <location>\/var\/log\/suricata\/eve.json<\/location>\
<\/localfile>' /var/ossec/etc/ossec.conf
fi

echo "=== Redemarrage de l'agent Wazuh ==="
sudo systemctl restart wazuh-agent

echo ""
echo "=== Verifications ==="
sleep 3
echo ""
echo "Suricata en cours ?"
sudo systemctl status suricata --no-pager -l | grep Active

echo ""
echo "Wazuh agent en cours ?"
sudo systemctl status wazuh-agent --no-pager -l | grep Active

echo ""
echo "Fichier eve.json existe ?"
ls -la /var/log/suricata/eve.json 2>/dev/null && echo "  OK" || echo "  PAS ENCORE (normal, attend 30s puis relance le script)"

echo ""
echo "=== FINI ==="
echo ""
echo "Test depuis Kali : nmap -sS 192.168.30.4"
echo "Puis sur le manager Wazuh : tail -f /var/ossec/logs/alerts/alerts.json | grep -i suricata"
