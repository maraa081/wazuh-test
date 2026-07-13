#!/bin/bash
# run-campaign.sh — Orchestrateur de campagne Docker massive
# Usage: sudo bash run-campaign.sh [--no-build] [--duration 600]
set -uo pipefail

NET_NAME="simulation_net"
NET_SUBNET="172.20.0.0/16"
NET_GW="172.20.0.1"
CONTAINER_TOTAL=100
IMAGE_NAME="traffic-agent:latest"
CAMPAIGN_DURATION=600
NO_BUILD=false

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-build) NO_BUILD=true; shift ;;
        --duration) CAMPAIGN_DURATION="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

CAMPAIGN_ID="CAMP_DOCKER_$(date +%Y%m%d_%H%M%S)"
CAMPAIGN_FILE="/tmp/${CAMPAIGN_ID}.csv"

echo "================================================================"
echo " DOCKER CAMPAIGN RUNNER — $CAMPAIGN_ID"
echo "================================================================"
echo "  Reseau:    $NET_NAME ($NET_SUBNET)"
echo "  Containers: $CONTAINER_TOTAL (99 benign + 1 malicious)"
echo "  Duree:     ${CAMPAIGN_DURATION}s"
echo "  Fichier:   $CAMPAIGN_FILE"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERROR: run as root"; exit 1; fi

# --- 1. Reseau Docker ---
echo "--- 1/7: Docker network ---"
docker network inspect "$NET_NAME" >/dev/null 2>&1 && \
    echo "  Network $NET_NAME exists" || \
    { docker network create --driver bridge --subnet="$NET_SUBNET" --gateway="$NET_GW" "$NET_NAME" && \
      echo "  Network $NET_NAME created"; }

# --- 2. Bridge interface ---
echo ""
echo "--- 2/7: Bridge interface ---"
sleep 2
BRIDGE_IFACE=""
BRIDGE_IFACE=$(ip -br addr show | grep " $NET_GW/" 2>/dev/null | awk '{print $1}' || true)
if [ -z "$BRIDGE_IFACE" ]; then
    BRIDGE_IFACE=$(ip route | grep "$NET_SUBNET" 2>/dev/null | awk '{print $3}' || echo "br-unknown")
fi
echo "  Interface: $BRIDGE_IFACE"

# --- 3. Suricata ---
echo ""
echo "--- 3/7: Suricata config ---"
if [ -f /etc/suricata/suricata.yaml ]; then
    grep -q "$BRIDGE_IFACE" /etc/suricata/suricata.yaml 2>/dev/null || \
        sed -i "/- interface: enp0s8/a\  - interface: $BRIDGE_IFACE" /etc/suricata/suricata.yaml
    grep -q "172.20.0.0" /etc/suricata/suricata.yaml 2>/dev/null || \
        sed -i 's/HOME_NET: "\[\(.*\)\]"/HOME_NET: "[\1,172.20.0.0\/16]"/' /etc/suricata/suricata.yaml
    systemctl restart suricata 2>/dev/null || true
    echo "  OK"
else
    echo "  /etc/suricata/suricata.yaml not found, skipping"
fi

# --- 4. Build image ---
echo ""
echo "--- 4/7: Docker image ---"
if [ "$NO_BUILD" = false ]; then
    # Download Dockerfile and profiles.py from repo
    REPO_BASE="https://raw.githubusercontent.com/maraa081/wazuh-test/main/scripts/docker-dataset"
    mkdir -p /tmp/docker-dataset
    curl -sL "$REPO_BASE/Dockerfile" -o /tmp/docker-dataset/Dockerfile
    curl -sL "$REPO_BASE/profiles.py" -o /tmp/docker-dataset/profiles.py
    docker build -t "$IMAGE_NAME" /tmp/docker-dataset 2>&1 | tail -3
    echo "  Image $IMAGE_NAME built"
else
    echo "  Skipping build (--no-build)"
fi

# --- 5. Launch containers ---
echo ""
echo "--- 5/7: Launching $CONTAINER_TOTAL containers ---"
CONTAINER_NAMES=()
START_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  Start: $START_UTC"

# Malicious container (agent-100)
docker run -d --name agent-100 --network "$NET_NAME" --cpus="0.1" --memory="64m" -e PROFILE=malicious "$IMAGE_NAME" >/dev/null
CONTAINER_NAMES+=("agent-100")
echo "  [agent-100] malicious"

# 99 benign containers
PROFILES_BENIGN=("benign_ssh" "benign_dns" "benign_http" "benign_ping")
WEIGHTS=(30 20 30 19)
cid=0
for i in $(seq 1 99); do
    acc=0; sel=0
    for p in 0 1 2 3; do
        acc=$((acc + WEIGHTS[p]))
        [ "$i" -le "$acc" ] && { sel=$p; break; }
    done
    profile="${PROFILES_BENIGN[$sel]}"
    cid=$((cid + 1))
    name=$(printf "agent-%03d" "$cid")
    docker run -d --name "$name" --network "$NET_NAME" --cpus="0.1" --memory="64m" -e "PROFILE=$profile" "$IMAGE_NAME" >/dev/null
    CONTAINER_NAMES+=("$name")
done
echo "  OK - $(docker ps --filter "network=$NET_NAME" -q 2>/dev/null | wc -l) running"

# --- 6. Campaign CSV ---
echo ""
echo "--- 6/7: Campaign file ---"
END_TS=$(($(date +%s) + CAMPAIGN_DURATION))
END_UTC=$(date -u -d "@$END_TS" +"%Y-%m-%dT%H:%M:%SZ")
cat > "$CAMPAIGN_FILE" << CSV
attack_id,start_utc,end_utc,attack_type,container_count
${CAMPAIGN_ID},${START_UTC},${END_UTC},benign_traffic,99
${CAMPAIGN_ID},${START_UTC},${END_UTC},malicious_nmap_hydra,1
CSV
echo "  $CAMPAIGN_FILE"

# --- Wait ---
echo ""
echo "--- Waiting ${CAMPAIGN_DURATION}s ---"
echo "  Ctrl+C to stop early (cleans up)"
STEP=0
while [ $STEP -lt $CAMPAIGN_DURATION ]; do
    running=$(docker ps --filter "network=$NET_NAME" -q 2>/dev/null | wc -l)
    remaining=$((CAMPAIGN_DURATION - STEP))
    echo "  [${remaining}s] Containers running: $running"
    sleep 60
    STEP=$((STEP + 60))
done

# --- 7. Cleanup ---
echo ""
echo "--- 7/7: Cleanup ---"
echo "  Stopping containers..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker stop "$name" 2>/dev/null || true
done
echo "  Removing containers..."
for name in "${CONTAINER_NAMES[@]}"; do
    docker rm "$name" 2>/dev/null || true
done
echo "  Done"

echo ""
echo "================================================================"
echo " CAMPAIGN COMPLETE"
echo "================================================================"
echo "  Campaign CSV: $CAMPAIGN_FILE"
echo "  Copy to project:"
echo "    mkdir -p /path/to/wazuh-test/data/attack_windows/"
echo "    cp $CAMPAIGN_FILE /path/to/wazuh-test/data/attack_windows/"
echo "================================================================"
