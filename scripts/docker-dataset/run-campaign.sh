#!/bin/bash
# run-campaign.sh — Orchestrateur de campagne Docker massive
# Usage: sudo bash run-campaign.sh
set -euo pipefail

NET_NAME="simulation_net"
NET_SUBNET="172.20.0.0/16"
NET_GW="172.20.0.1"
CONTAINER_TOTAL=100
IMAGE_NAME="traffic-agent:latest"
CAMPAIGN_DURATION=600
CAMPAIGN_ID="CAMP_DOCKER_$(date +%Y%m%d_%H%M%S)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CAMPAIGN_FILE="${PROJECT_DIR}/data/attack_windows/${CAMPAIGN_ID}.csv"

echo "═══════════════════════════════════════════════════════════════"
echo " DOCKER CAMPAIGN RUNNER — $CAMPAIGN_ID"
echo "═══════════════════════════════════════════════════════════════"
echo "  Réseau:    $NET_NAME ($NET_SUBNET)"
echo "  Conteneurs: $CONTAINER_TOTAL (99 benins + 1 malveillant)"
echo "  Duree:     ${CAMPAIGN_DURATION}s (10 min)"
echo "  Fichier:   $CAMPAIGN_FILE"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERREUR: Lance en root (sudo)"; exit 1; fi

# ─── Etape 1 : Creation du reseau Docker ──────────────────────────
echo "=== Etape 1/7 : Creation du reseau Docker ==="
if docker network inspect "$NET_NAME" >/dev/null 2>&1; then
    echo "  Reseau $NET_NAME existe deja"
else
    docker network create --driver bridge --subnet="$NET_SUBNET" --gateway="$NET_GW" "$NET_NAME"
    echo "  OK Reseau $NET_NAME cree ($NET_SUBNET)"
fi

# ─── Etape 2 : Recuperer l'interface bridge Docker ────────────────
echo ""
echo "=== Etape 2/7 : Detection interface bridge ==="
sleep 2
BRIDGE_IFACE=$(ip -br addr show | grep " $NET_GW/" | awk '{print $1}' 2>/dev/null || echo "")
if [ -z "$BRIDGE_IFACE" ]; then
    BRIDGE_IFACE=$(basename "$(ip route show "$NET_SUBNET" 2>/dev/null | head -1 | awk '{print $3}')" 2>/dev/null || echo "br-unknown")
fi
echo "  Interface bridge detectee: $BRIDGE_IFACE"

# ─── Etape 3 : Config Suricata pour ecouter sur le bridge ─────────
echo ""
echo "=== Etape 3/7 : Configuration Suricata (bridge) ==="
SURICATA_CONF="/etc/suricata/suricata.yaml"
if grep -q "$BRIDGE_IFACE" "$SURICATA_CONF" 2>/dev/null; then
    echo "  $BRIDGE_IFACE deja dans af-packet"
else
    sed -i "/- interface: enp0s8/a\  - interface: $BRIDGE_IFACE" "$SURICATA_CONF"
    echo "  OK $BRIDGE_IFACE ajoute a af-packet"
fi
if grep -q "172.20.0.0" "$SURICATA_CONF" 2>/dev/null; then
    echo "  Docker subnet deja dans HOME_NET"
else
    sed -i 's/HOME_NET: "\[\(.*\)\]"/HOME_NET: "[\1,172.20.0.0\/16]"/' "$SURICATA_CONF"
    echo "  OK 172.20.0.0/16 ajoute a HOME_NET"
fi
systemctl restart suricata 2>/dev/null || true
sleep 2
systemctl is-active suricata >/dev/null && echo "  OK Suricata redemarre" || echo "  Attention: echec restart Suricata"

# ─── Etape 4 : Build de l'image Docker ────────────────────────────
echo ""
echo "=== Etape 4/7 : Build image Docker ==="
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR" 2>&1 | tail -3
echo "  OK Image $IMAGE_NAME construite"

# ─── Etape 5 : Lancement des conteneurs ──────────────────────────
echo ""
echo "=== Etape 5/7 : Lancement des $CONTAINER_TOTAL conteneurs ==="

declare -a CONTAINER_NAMES=()
CURRENT_TIME=$(date +%s)
START_UTC=$(date -u -d "@$CURRENT_TIME" +"%Y-%m-%dT%H:%M:%SZ")
echo "  Debut: $START_UTC"

# Un conteneur malveillant (agent-100)
docker run -d \
    --name "agent-100" \
    --network "$NET_NAME" \
    --cpus="0.1" \
    --memory="64m" \
    -e "PROFILE=malicious" \
    "$IMAGE_NAME" >/dev/null
CONTAINER_NAMES+=("agent-100")
echo "  agent-100 -> malicious"

# 99 conteneurs benins avec index propre
PROFILES_BENIGN=("benign_ssh" "benign_dns" "benign_http" "benign_ping")
PROFILES_WEIGHT=(30 20 30 19)

cid=0
for i in $(seq 1 99); do
    # Accumulateur: on determine le profil en accumulant les poids
    acc=0
    selected=0
    for p in "${!PROFILES_WEIGHT[@]}"; do
        acc=$((acc + PROFILES_WEIGHT[p]))
        if [ "$i" -le "$acc" ]; then
            selected=$p
            break
        fi
    done
    profile="${PROFILES_BENIGN[$selected]}"
    cid=$((cid + 1))
    name=$(printf "agent-%03d" "$cid")
    docker run -d \
        --name "$name" \
        --network "$NET_NAME" \
        --cpus="0.1" \
        --memory="64m" \
        -e "PROFILE=$profile" \
        "$IMAGE_NAME" >/dev/null
    CONTAINER_NAMES+=("$name")
done

echo "  OK $CONTAINER_TOTAL conteneurs lances (99 benins, 1 malveillant)"

# ─── Etape 6 : Ecrire le CSV de campagne ──────────────────────────
echo ""
echo "=== Etape 6/7 : Generation du fichier de campagne ==="
mkdir -p "$(dirname "$CAMPAIGN_FILE")"
END_UTC=$(date -u -d "@$((CURRENT_TIME + CAMPAIGN_DURATION))" +"%Y-%m-%dT%H:%M:%SZ")

cat > "$CAMPAIGN_FILE" << CSV
attack_id,start_utc,end_utc,attack_type,container_count,target_subnet
${CAMPAIGN_ID},${START_UTC},${END_UTC},benign_traffic,99,all
${CAMPAIGN_ID},${START_UTC},${END_UTC},malicious_nmap_hydra,1,172.20.0.0/16+192.168.30.0/24
CSV
echo "  OK $CAMPAIGN_FILE"
cat "$CAMPAIGN_FILE"

# ─── Attente + Stats ──────────────────────────────────────────────
echo ""
echo "=== Attente ${CAMPAIGN_DURATION}s (10 minutes) ==="
echo "  Ctrl+C pour arreter"

for elapsed in $(seq 0 60 $CAMPAIGN_DURATION); do
    remaining=$((CAMPAIGN_DURATION - elapsed))
    running=$(docker ps --filter "network=$NET_NAME" -q 2>/dev/null | wc -l)
    echo "  [${remaining}s] Actifs: $running"
    sleep 60
done

echo ""

# ─── Etape 7 : Cleanup ────────────────────────────────────────────
echo "=== Etape 7/7 : Nettoyage ==="
echo "  Arret des conteneurs..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker stop "$name" 2>/dev/null || true
done
echo "  Suppression des conteneurs..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker rm "$name" 2>/dev/null || true
done

echo "  OK Nettoyage termine"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " CAMPAGNE TERMINEE"
echo "═══════════════════════════════════════════════════════════════"
echo "  Fichier: $CAMPAIGN_FILE"
echo "  Reseau conserve: $NET_NAME"
echo "  Image conservee: $IMAGE_NAME"
echo "  Prochaine: pipeline/01_collect_alerts.py"
echo "═══════════════════════════════════════════════════════════════"
