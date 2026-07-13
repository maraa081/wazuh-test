#!/bin/bash
# run-campaign.sh — Orchestrateur de campagne Docker massive
# Usage: sudo bash run-campaign.sh
#
# Crée un réseau Docker bridge (simulation_net, 172.20.0.0/16),
# lance 99 conteneurs bénins + 1 malveillant, attend 10 min, nettoie.
# Configure Suricata pour écouter sur l'interface du bridge.

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────
NET_NAME="simulation_net"
NET_SUBNET="172.20.0.0/16"
NET_GW="172.20.0.1"
CONTAINER_COUNT=100
IMAGE_NAME="traffic-agent:latest"
CAMPAIGN_DURATION=600  # 10 minutes en secondes
CAMPAIGN_ID="CAMP_DOCKER_$(date +%Y%m%d_%H%M%S)"

# Fichier de sortie (relatif à la racine du projet)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CAMPAIGN_FILE="${PROJECT_DIR}/data/attack_windows/${CAMPAIGN_ID}.csv"

echo "═══════════════════════════════════════════════════════════════"
echo " DOCKER CAMPAIGN RUNNER — $CAMPAIGN_ID"
echo "═══════════════════════════════════════════════════════════════"
echo "  Réseau:    $NET_NAME ($NET_SUBNET)"
echo "  Conteneurs: $CONTAINER_COUNT (99 bénins + 1 malveillant)"
echo "  Durée:     ${CAMPAIGN_DURATION}s (10 min)"
echo "  Fichier:   $CAMPAIGN_FILE"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Lance en root (sudo)"
    exit 1
fi

# ─── Étape 1 : Création du réseau Docker ──────────────────────────
echo "═══ Étape 1/7 : Création du réseau Docker ═══"
if docker network inspect "$NET_NAME" >/dev/null 2>&1; then
    echo "  Réseau $NET_NAME existe déjà"
else
    docker network create \
        --driver bridge \
        --subnet="$NET_SUBNET" \
        --gateway="$NET_GW" \
        "$NET_NAME"
    echo "  ✅ Réseau $NET_NAME créé ($NET_SUBNET)"
fi

# ─── Étape 2 : Récupérer l'interface bridge Docker ────────────────
echo ""
echo "═══ Étape 2/7 : Détection interface bridge ═══"
# Attendre que Docker crée l'interface
sleep 2
BRIDGE_IFACE=$(docker network inspect "$NET_NAME" --format '{{.Options | toJSON}}' 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('com.docker.network.bridge.name','br-' + json.load(sys.stdin).get('com.docker.network.bridge.name','')))" 2>/dev/null || echo "")
# Fallback: find the bridge by subnet
if [ -z "$BRIDGE_IFACE" ]; then
    BRIDGE_IFACE=$(ip -br addr show | grep "$NET_GW" | awk '{print $1}' 2>/dev/null || echo "")
fi
if [ -z "$BRIDGE_IFACE" ]; then
    # Last resort: find Docker bridge with 172.20.0.1
    BRIDGE_IFACE=$(ip addr show to 172.20.0.1/16 | grep -E "^[0-9]" | awk '{print $2}' | tr -d ':' || echo "br-unknown")
fi
echo "  Interface bridge détectée: $BRIDGE_IFACE"

# ─── Étape 3 : Config Suricata pour écouter sur le bridge ─────────
echo ""
echo "═══ Étape 3/7 : Configuration Suricata (bridge) ═══"
SURICATA_CONF="/etc/suricata/suricata.yaml"
# Ajouter l'interface bridge dans af-packet si pas déjà présente
if grep -q "$BRIDGE_IFACE" "$SURICATA_CONF" 2>/dev/null; then
    echo "  $BRIDGE_IFACE déjà dans af-packet"
else
    # Insérer après la ligne "- interface: enp0s8"
    sed -i "/- interface: enp0s8/a\  - interface: $BRIDGE_IFACE" "$SURICATA_CONF"
    echo "  ✅ $BRIDGE_IFACE ajouté à af-packet"
fi

# Home_NET doit inclure le Docker subnet
if grep -q "172.20.0.0" "$SURICATA_CONF" 2>/dev/null; then
    echo "  Docker subnet déjà dans HOME_NET"
else
    sed -i 's/HOME_NET: "\[\(.*\)\]"/HOME_NET: "[\1,172.20.0.0\/16]"/' "$SURICATA_CONF"
    echo "  ✅ 172.20.0.0/16 ajouté à HOME_NET"
fi

systemctl restart suricata
sleep 2
systemctl is-active suricata >/dev/null && echo "  ✅ Suricata redémarré" || echo "  ⚠️  Échec restart Suricata"

# ─── Étape 4 : Build de l'image Docker ────────────────────────────
echo ""
echo "═══ Étape 4/7 : Build image Docker ═══"
DOCKER_DIR="$SCRIPT_DIR"
docker build -t "$IMAGE_NAME" "$DOCKER_DIR" 2>&1 | tail -3
echo "  ✅ Image $IMAGE_NAME construite"

# ─── Étape 5 : Lancement des conteneurs ──────────────────────────
echo ""
echo "═══ Étape 5/7 : Lancement des $CONTAINER_COUNT conteneurs ═══"

declare -a CONTAINER_NAMES=()
START_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  Début: $START_UTC"

# Un conteneur malveillant (agent-100)
docker run -d \
    --name "agent-100" \
    --network "$NET_NAME" \
    --cpus="0.1" \
    --memory="64m" \
    -e "PROFILE=malicious" \
    "$IMAGE_NAME" >/dev/null
CONTAINER_NAMES+=("agent-100")
echo "  🔴  agent-100   → malicious"

# 99 conteneurs bénins
profile_cycle=0
PROFILES_BENIGN=("benign_ssh" "benign_dns" "benign_http" "benign_ping")
PROFILES_WEIGHT=(30 20 30 19)  # Doit totaliser 99

profile_idx=0
for i in $(seq 1 99); do
    # Avancer dans le cycle des profils selon les poids
    while [ $i -gt "${PROFILES_WEIGHT[$profile_idx]}" ]; do
        i=$((i - PROFILES_WEIGHT[profile_idx]))
        profile_idx=$((profile_idx + 1))
        if [ $profile_idx -ge ${#PROFILES_WEIGHT[@]} ]; then
            profile_idx=0
        fi
    done
    profile="${PROFILES_BENIGN[$profile_idx]}"

    name=$(printf "agent-%03d" "$i")
    docker run -d \
        --name "$name" \
        --network "$NET_NAME" \
        --cpus="0.1" \
        --memory="64m" \
        -e "PROFILE=$profile" \
        "$IMAGE_NAME" >/dev/null
    CONTAINER_NAMES+=("$name")
done

echo "  ✅ $CONTAINER_COUNT conteneurs lancés"
echo "     (99 bénins, 1 malveillant)"

# ─── Étape 6 : Écrire le CSV de campagne ──────────────────────────
echo ""
echo "═══ Étape 6/7 : Génération du fichier de campagne ═══"
mkdir -p "$(dirname "$CAMPAIGN_FILE")"
END_UTC=$(date -d "+${CAMPAIGN_DURATION} seconds" -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$CAMPAIGN_FILE" << CSV
attack_id,start_utc,end_utc,attack_type,container_count,target_subnet
${CAMPAIGN_ID},${START_UTC},${END_UTC},benign_traffic,99,aLL
${CAMPAIGN_ID},${START_UTC},${END_UTC},malicious_nmap_hydra,1,172.20.0.0/16+192.168.30.0/24
CSV
echo "  ✅ $CAMPAIGN_FILE"
echo "  Contenu:"
cat "$CAMPAIGN_FILE"

# ─── Attente + Stats ──────────────────────────────────────────────
echo ""
echo "═══ Attente ${CAMPAIGN_DURATION}s (10 minutes) ═══"
echo "  Ctrl+C pour arrêter proprement (nettoie quand même)"
echo ""

for elapsed in $(seq 0 60 $CAMPAIGN_DURATION); do
    remaining=$((CAMPAIGN_DURATION - elapsed))
    running=$(docker ps --filter "network=$NET_NAME" -q 2>/dev/null | wc -l)
    echo "  [${remaining}s restantes] Conteneurs actifs: $running"
    sleep 60
done

echo ""

# ─── Étape 7 : Cleanup ────────────────────────────────────────────
echo "═══ Étape 7/7 : Nettoyage ═══"
echo "  Arrêt des conteneurs..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker stop "$name" 2>/dev/null || true
done

echo "  Suppression des conteneurs..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker rm "$name" 2>/dev/null || true
done

# Ne pas supprimer le réseau ni l'image pour les campagnes futures
echo "  ✅ Nettoyage terminé"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " CAMPAGNE TERMINÉE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Fichier campagne:  $CAMPAIGN_FILE"
echo "  Réseau conservé:   $NET_NAME (pour prochaine campagne)"
echo "  Image conservée:   $IMAGE_NAME"
echo ""
echo "  Prochaine étape sur le Manager:"
echo "  python3 pipeline/01_collect_alerts.py --campaign $CAMPAIGN_ID"
echo ""
echo "  Puis copier le CSV dans le dataset:"
echo "  cp $CAMPAIGN_FILE data/attack_windows/"
echo "═══════════════════════════════════════════════════════════════"
