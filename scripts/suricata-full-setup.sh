#!/bin/bash
# suricata-full-setup.sh — Configure Suricata + Wazuh pour détection de scans Nmap
# Usage: sudo bash suricata-full-setup.sh
set -euo pipefail

WAZUH_MANAGER_IP="192.168.30.3"
HOSTNAME=$(hostname)

echo "================================================================"
echo " SURICATA + WAZUH FULL SETUP — $(date)"
echo "================================================================"

if [ "$(id -u)" -ne 0 ]; then echo "❌ Lance en root"; exit 1; fi

# ──────────────────────────────────────────────
# 1) Replace custom rules with aggressive Nmap detection rules
# ──────────────────────────────────────────────
echo ""
echo "--- 1. Installation des règles Nmap agressives ---"

cat > /var/lib/suricata/rules/local.rules << 'RULES'
# Nmap detection — LOW threshold (trigger on 3+ SYN packets)
alert tcp any any -> any any (msg:"ET SCAN NMAP SYN scan -sS"; flags:S; flow:stateless; threshold: type both, track by_src, seconds 30, count 3; classtype:network-scan; sid:1000001; rev:2;)

# Nmap OS fingerprint (window=1024, seq=0)
alert tcp any any -> any any (msg:"ET SCAN NMAP OS fingerprint"; flags:S; window:1024; classtype:attempted-recon; sid:1000002; rev:2;)

# Nmap connect scan -sT
alert tcp any any -> any any (msg:"ET SCAN NMAP TCP connect -sT"; flags:A; flow:to_client; threshold: type both, track by_src, seconds 30, count 3; classtype:network-scan; sid:1000003; rev:2;)

# Port scan detected by portscan module (bridge event)
alert tcp any any -> any any (msg:"ET SCAN Port scan detected"; flags:S; threshold: type both, track by_src, seconds 10, count 5; classtype:network-scan; sid:1000004; rev:2;)

# Nmap ping sweep
alert icmp any any -> any any (msg:"ET SCAN NMAP ping sweep"; icmp_id:0; threshold: type both, track by_src, seconds 30, count 3; classtype:network-scan; sid:1000005; rev:2;)

# Nmap version scan (-sV)
alert tcp any any -> any any (msg:"ET SCAN NMAP -sV version"; flags:PA; flow:to_server; threshold: type both, track by_src, seconds 30, count 3; classtype:network-scan; sid:1000006; rev:2;)
RULES

chown suricata:suricata /var/lib/suricata/rules/local.rules
echo "  ✅ 6 règles Nmap installées (seuil: 3 paquets)"

# ──────────────────────────────────────────────
# 2) Add portscan events to eve-log types
# ──────────────────────────────────────────────
echo ""
echo "--- 2. Ajout portscan aux types eve-log ---"
# Check if portscan type already exists
if grep -q "portscan" /etc/suricata/suricata.yaml; then
    echo "  portscan déjà dans les types"
else
    # Add portscan type after the types section (before anomaly)
    sed -i '/types:/,/^  [a-z]/{
        /^- anomaly:/i\        - portscan
    }' /etc/suricata/suricata.yaml 2>/dev/null || true
    echo "  ✅ portscan ajouté aux types eve-log"
fi

# ──────────────────────────────────────────────
# 3) Aggressive portscan module config
# ──────────────────────────────────────────────
echo ""
echo "--- 3. Configuration agressive du portscan module ---"
# Remove existing portscan section and add aggressive one
sed -i '/^portscan:/,/^[a-z#]/d' /etc/suricata/suricata.yaml 2>/dev/null || true
cat >> /etc/suricata/suricata.yaml << 'EOF'

# Port scan detection - aggressive
portscan:
  protocols: tcp udp icmp
  scan-type: all
  scan-lookup: 20
  scan-threshold: 100
  detect-new-scans: yes
  log-gen: yes
  log-ip: yes
EOF
echo "  ✅ Portscan module: scan-lookup=20, scan-threshold=100ms"

# ──────────────────────────────────────────────
# 4) Vérifier la promiscuité sur enp0s8
# ──────────────────────────────────────────────
echo ""
echo "--- 4. Promiscuité enp0s8 ---"
ip link set enp0s8 promisc on 2>/dev/null || true
promisc=$(ip -br link show enp0s8 | grep -o "PROMISC" || echo "OFF")
echo "  enp0s8: $promisc"

# ──────────────────────────────────────────────
# 5) Add eve.json to Wazuh agent
# ──────────────────────────────────────────────
echo ""
echo "--- 5. Configuration Wazuh agent (eve.json) ---"
OSSEC_CONF="/var/ossec/etc/ossec.conf"
if [ -f "$OSSEC_CONF" ]; then
    # Check if suricata logfile is already configured
    if grep -q "eve.json" "$OSSEC_CONF"; then
        echo "  eve.json déjà configuré dans ossec.conf"
    else
        # Add before </ossec_config>
        sed -i '/<\/ossec_config>/i\
  <localfile>\
    <log_format>json</log_format>\
    <location>/var/log/suricata/eve.json</location>\
  </localfile>' "$OSSEC_CONF"
        echo "  ✅ eve.json ajouté à ossec.conf"
    fi

    # Restart Wazuh agent
    systemctl restart wazuh-agent 2>/dev/null || systemctl restart wazuh-agent
    echo "  ✅ Wazuh agent restarté"
else
    echo "  ❌ ossec.conf pas trouvé — Wazuh agent pas installé ?"
fi

# ──────────────────────────────────────────────
# 6) Test config & restart Suricata
# ──────────────────────────────────────────────
echo ""
echo "--- 6. Test config Suricata ---"
suricata -T -c /etc/suricata/suricata.yaml -v 2>&1 | tail -5

echo ""
echo "--- 7. Redémarrage Suricata ---"
systemctl restart suricata
sleep 2
systemctl is-active suricata >/dev/null && echo "  ✅ Suricata running" || echo "  ❌ Échec"

# ──────────────────────────────────────────────
# 8) Final report
# ──────────────────────────────────────────────
echo ""
echo "================================================================"
echo " SETUP TERMINÉ"
echo "================================================================"
echo ""
echo "1️⃣  Depuis ParrotOS, LANCE :"
echo "   nmap -sS -p 22,80 192.168.30.10"
echo "   nmap -sV -p 22,80 192.168.30.10"
echo "   nmap -T4 -p- 192.168.30.10"
echo ""
echo "2️⃣  Sur la cible, VÉRIFIE :"
echo "   tail -f /var/log/suricata/fast.log"
echo "   (les alertes apparaissent en live)"
echo ""
echo "3️⃣  Vérifie Wazuh côté Manager :"
echo "   sudo grep -i suricata /var/ossec/logs/alerts/alerts.json | tail -5"
echo ""
echo "================================================================"
