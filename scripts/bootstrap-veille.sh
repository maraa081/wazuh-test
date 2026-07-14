#!/bin/bash
# bootstrap-veille.sh — Configure OpenClaw sur le Manager avec l'identite Veille
# Usage : bash bootstrap-veille.sh
# Execute SUR LE MANAGER (UbuntuWazuh)

set -e

echo "=== Bootstrapping Veille sur le Manager ==="

WORKSPACE="$HOME/.openclaw/workspace"
REPO_DIR="$HOME/wazuh-test"
CONFIG_DIR="$REPO_DIR/docs/veille-config"

# 1. Cloner le repo si pas fait
if [ ! -d "$REPO_DIR" ]; then
    echo "[1/5] Clonage du repo..."
    git clone https://github.com/maraa081/wazuh-test.git "$REPO_DIR"
else
    echo "[1/5] Mise a jour du repo..."
    cd "$REPO_DIR" && git pull
fi

# 2. Creer le workspace
echo "[2/5] Configuration du workspace..."
mkdir -p "$WORKSPACE"

# 3. Copier les fichiers d'identite
echo "[3/5] Installation des fichiers Veille..."
cp "$CONFIG_DIR/SOUL.md" "$WORKSPACE/SOUL.md"
cp "$CONFIG_DIR/AGENTS.md" "$WORKSPACE/AGENTS.md"
cp "$CONFIG_DIR/IDENTITY.md" "$WORKSPACE/IDENTITY.md"
cp "$CONFIG_DIR/USER.md" "$WORKSPACE/USER.md"
cp "$CONFIG_DIR/MEMORY.md" "$WORKSPACE/MEMORY.md"
cp "$CONFIG_DIR/TOOLS.md" "$WORKSPACE/TOOLS.md"

# 4. Configurer le workspace dans la config OpenClaw
echo "[4/5] Mise a jour de la config OpenClaw..."
# Verifier si la config existe
if [ -f "$HOME/.openclaw/openclaw.json" ]; then
    # Utiliser python pour editer le JSON
    python3 -c "
import json, os
config_path = os.path.expanduser('~/.openclaw/openclaw.json')
with open(config_path) as f:
    config = json.load(f)
if 'agents' not in config:
    config['agents'] = {}
if 'defaults' not in config['agents']:
    config['agents']['defaults'] = {}
config['agents']['defaults']['workspace'] = '$WORKSPACE'
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
print('Workspace updated')
"
fi

# 5. Copier les scripts
echo "[5/5] Installation des scripts..."
mkdir -p "$WORKSPACE/scripts"
cp "$REPO_DIR/scripts/lab-campaign.sh" "$WORKSPACE/scripts/"
cp "$REPO_DIR/scripts/lab-healthcheck.sh" "$WORKSPACE/scripts/"
chmod +x "$WORKSPACE/scripts/"*.sh

echo ""
echo "=== Bootstrap termine ==="
echo "Redemarrage du Gateway recommande : openclaw gateway restart"
echo "Ensuite : parle a Veille dans le dashboard ou Telegram"
