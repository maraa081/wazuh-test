#!/bin/bash
# Setup Suricata IDS + Wazuh integration sur la machine cible
# A lancer en root sur la VM cible (Ubuntu, VirtualBox)
# Rien a modifier, tout est automatique

set -e

echo "=== Installation de Suricata ==="
sudo apt update
sudo apt install suricata -y

echo "=== Detection auto de l'interface reseau ==="
IFACE=$(ip -o link show | grep -v lo | awk -F': ' '{print $2}' | head -1)
echo "Interface detectee : $IFACE"

echo "=== Configuration Suricata ==="
sudo sed -i "s/^INTERFACE=.*/INTERFACE=$IFACE/" /etc/default/suricata

# Mode IDS (pas IPS), on ne bloque rien
sudo sed -i 's/^# af-packet:/af-packet:/' /etc/suricata/suricata.yaml

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

echo "=== Verifications ==="
sleep 2
echo ""
echo "1. Suricata en cours ?"
sudo systemctl status suricata --no-pager -l | grep Active

echo ""
echo "2. Wazuh agent en cours ?"
sudo systemctl status wazuh-agent --no-pager -l | grep Active

echo ""
echo "3. Fichier eve.json existe ?"
ls -la /var/log/suricata/eve.json 2>/dev/null && echo "  OK" || echo "  PAS ENCORE (normal, attend 30s)"

echo ""
echo "=== FINI ==="
echo ""
echo "Pour verifier que tout marche :"
echo "  1. Depuis Kali : nmap -sS 192.168.30.4"
echo "  2. Sur le manager Wazuh : tail -f /var/ossec/logs/alerts/alerts.json | grep -i suricata"
echo "  (ou regarde depuis le dashboard Wazuh)"
