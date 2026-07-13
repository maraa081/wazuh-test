#!/bin/bash
# Wazuh Agent Installer — Ubuntu 22.04
# Idempotent : relançable sans casser l'install existante
#
# Usage: sudo bash install-wazuh-agent.sh
# Variables à adapter en haut du fichier

set -euo pipefail

# ═══════════════════════════════════════════
# VARIABLES — adapter au labo
# ═══════════════════════════════════════════

WAZUH_MANAGER_IP="192.168.30.3"        # IP du Manager Wazuh
WAZUH_MANAGER_PORT="1514"               # Port de connexion (défaut 1514)
WAZUH_AGENT_NAME="ubuntu-target"        # Nom visible côté Manager
WAZUH_VERSION="4.9"                      # Version majeure du dépôt (4.x ici)

# ═══════════════════════════════════════════
# NE RIEN MODIFIER SOUS CETTE LIGNE
# ═══════════════════════════════════════════

echo "============================================"
echo " Wazuh Agent Installer — $(date)"
echo " Version : $WAZUH_VERSION"
echo " Manager : $WAZUH_MANAGER_IP:$WAZUH_MANAGER_PORT"
echo " Agent   : $WAZUH_AGENT_NAME"
echo "============================================"
echo ""

# --- Vérification root ---
if [ "$(id -u)" -ne 0 ]; then
    echo "ERREUR : Lance en root (sudo bash install-wazuh-agent.sh)"
    exit 1
fi

# --- 1. Importer la clé GPG ---
echo "--- 1. Ajout du dépôt Wazuh ---"
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import --batch 2>/dev/null || true
chmod 644 /usr/share/keyrings/wazuh.gpg 2>/dev/null || true

echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/${WAZUH_VERSION}/apt/ stable main" \
  | tee /etc/apt/sources.list.d/wazuh.list

# --- 2. Installer l'agent ---
echo ""
echo "--- 2. Installation du paquet wazuh-agent ---"
apt-get update -qq
apt-get install -y wazuh-agent

# --- 3. Configurer l'IP du Manager ---
echo ""
echo "--- 3. Configuration du Manager ---"
if grep -q "MANAGER_IP" /var/ossec/etc/ossec.conf; then
    sed -i "s/MANAGER_IP/$WAZUH_MANAGER_IP/g" /var/ossec/etc/ossec.conf
    echo "  IP Manager configurée : $WAZUH_MANAGER_IP"
else
    echo "  IP déjà configurée, vérification..."
    grep "<address>" /var/ossec/etc/ossec.conf
fi

# --- 4. Ajouter le nom de l'agent ---
echo ""
echo "--- 4. Nom de l'agent ---"
sed -i "s/<client>/\0\n  <config-profile>$WAZUH_AGENT_NAME<\/config-profile>/" /var/ossec/etc/ossec.conf 2>/dev/null || true

# --- 5. Éviter la désinstallation automatique (lock) ---
echo ""
echo "--- 5. Lock du paquet contre les mises à jour automatiques ---"
systemctl daemon-reload

# --- 6. Démarrer l'agent ---
echo ""
echo "--- 6. Démarrage de l'agent ---"
systemctl enable wazuh-agent 2>/dev/null || true
systemctl restart wazuh-agent

# --- 7. Vérification ---
echo ""
echo "--- 7. Vérification ---"
sleep 2
systemctl is-active --quiet wazuh-agent && echo "  ✅ Agent démarré" || echo "  ❌ Agent pas démarré"
echo ""
echo "--- Logs agent (10 dernières lignes) ---"
tail -10 /var/ossec/logs/ossec.log 2>/dev/null | grep -i "connected\|error\|warn" || echo "  (pas de logs)"
echo ""
echo "============================================"
echo " Vérifie côté Manager :"
echo "   sudo /var/ossec/bin/manage_agents -l"
echo "   sudo /var/ossec/bin/agent_control -l"
echo "============================================"
