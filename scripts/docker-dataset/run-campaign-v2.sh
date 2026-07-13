#!/bin/bash
# run-campaign-v2.sh — Campagne 1h en 3 phases
# Usage: sudo bash run-campaign-v2.sh
set -uo pipefail

NET_NAME="simulation_net"
NET_SUBNET="172.20.0.0/16"
NET_GW="172.20.0.1"
IMAGE_NAME="traffic-agent:latest"
CAMPAIGN_ID="CAMP_V2_$(date +%Y%m%d_%H%M%S)"
CAMPAIGN_FILE="/tmp/${CAMPAIGN_ID}.csv"

SLEEP_BENIGN=600    # 10min
SLEEP_ATTACK=1200   # 20min
SLEEP_FINAL=600     # 10min
TOTAL=2400          # 40 min total

echo "================================================"
echo " CAMPAIGN V2 — 3 phases, 40min"
echo "  Phase 1: 10min benign only (pure FP)"
echo "  Phase 2: 20min benign + malicious (TP+FP)"
echo "  Phase 3: 10min benign only (pure FP)"
echo "================================================"
echo ""

if [ "$(id -u)" -ne 0 ]; then echo "ERROR: run as root"; exit 1; fi

# Network
echo "--- 1/6: Docker network ---"
docker network inspect "$NET_NAME" >/dev/null 2>&1 && \
    echo "  OK exists" || \
    docker network create --driver bridge --subnet="$NET_SUBNET" --gateway="$NET_GW" "$NET_NAME"

# Bridge detection
echo "--- 2/6: Bridge interface ---"
BRIDGE_IFACE=$(ip -br addr show | grep " $NET_GW/" 2>/dev/null | awk '{print $1}' || echo "br-unknown")
echo "  Interface: $BRIDGE_IFACE"

# Suricata config
echo "--- 3/6: Suricata ---"
if [ -f /etc/suricata/suricata.yaml ]; then
    grep -q "$BRIDGE_IFACE" /etc/suricata/suricata.yaml 2>/dev/null || \
        sed -i "/- interface: enp0s8/a\  - interface: $BRIDGE_IFACE" /etc/suricata/suricata.yaml
    grep -q "172.20.0.0" /etc/suricata/suricata.yaml 2>/dev/null || \
        sed -i 's/HOME_NET: "\[\(.*\)\]"/HOME_NET: "[\1,172.20.0.0\/16]"/' /etc/suricata/suricata.yaml
    systemctl restart suricata 2>/dev/null || true
    echo "  OK"
fi

# Build or skip
echo "--- 4/6: Docker image ---"
if ! docker images --format "{{.Repository}}" | grep -q "traffic-agent"; then
    REPO="https://raw.githubusercontent.com/maraa081/wazuh-test/main/scripts/docker-dataset"
    mkdir -p /tmp/docker-dataset
    curl -sL "$REPO/Dockerfile" -o /tmp/docker-dataset/Dockerfile
    curl -sL "$REPO/profiles.py" -o /tmp/docker-dataset/profiles.py
    docker build -t "$IMAGE_NAME" /tmp/docker-dataset 2>&1 | tail -1
fi
echo "  OK"

# --- Helper ---
launch_benign() {
    local count=$1 prefix=$2
    local cid=0
    local PROFILES=("benign_ssh" "benign_dns" "benign_http" "benign_ping")
    local WEIGHTS=(30 20 30 19)
    for i in $(seq 1 $count); do
        acc=0; sel=0
        for p in 0 1 2 3; do
            acc=$((acc + WEIGHTS[p]))
            [ "$i" -le "$acc" ] && { sel=$p; break; }
        done
        cid=$((cid + 1))
        name="${prefix}-$(printf "%03d" "$cid")"
        docker run -d --name "$name" --network "$NET_NAME" --cpus="0.1" --memory="64m" -e "PROFILE=${PROFILES[$sel]}" "$IMAGE_NAME" >/dev/null
        echo -n "."
    done
    echo ""
}

launch_malicious() {
    local name=$1
    docker run -d --name "$name" --network "$NET_NAME" --cpus="0.1" --memory="64m" -e "PROFILE=malicious" "$IMAGE_NAME" >/dev/null
    echo "  malicious: $name"
}

# --- PHASE 1: Benign only (10 min) ---
echo ""
echo "================================================"
echo " PHASE 1 — 10min: BENIGN ONLY (pure FP)"
echo "================================================"
P1_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  Start: $P1_START"
launch_benign 100 "p1"
P1_END=$(date -u -d "@$(($(date +%s) + SLEEP_BENIGN))" +"%Y-%m-%dT%H:%M:%SZ")
echo "  End:   $P1_END"
echo "  Phase 2 starts in ${SLEEP_BENIGN}s..."
sleep $SLEEP_BENIGN

# --- PHASE 2: Benign + Malicious (20 min) ---
echo ""
echo "================================================"
echo " PHASE 2 — 20min: BENIGN + MALICIOUS (TP+FP)"
echo "================================================"
P2_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  Start: $P2_START"
launch_malicious "malicious-v2"
P2_END=$(date -u -d "@$(($(date +%s) + SLEEP_ATTACK))" +"%Y-%m-%dT%H:%M:%SZ")
echo "  End:   $P2_END"
echo "  Phase 3 starts in ${SLEEP_ATTACK}s..."
sleep $SLEEP_ATTACK

# Stop malicious (keep benign running)
echo "  Stopping malicious container..."
docker stop malicious-v2 2>/dev/null || true
docker rm malicious-v2 2>/dev/null || true

# --- PHASE 3: Benign only again (10 min) ---
echo ""
echo "================================================"
echo " PHASE 3 — 10min: BENIGN ONLY (pure FP)"
echo "================================================"
P3_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  Start: $P3_START"
P3_END=$(date -u -d "@$(($(date +%s) + SLEEP_FINAL))" +"%Y-%m-%dT%H:%M:%SZ")
echo "  End:   $P3_END"
echo "  Cleanup in ${SLEEP_FINAL}s..."
sleep $SLEEP_FINAL

# --- Cleanup ---
echo ""
echo "--- Cleanup ---"
for name in $(docker ps -a --filter "network=$NET_NAME" --format "{{.Names}}" 2>/dev/null); do
    docker stop "$name" 2>/dev/null || true
done
docker container prune -f 2>/dev/null || true
echo "  Done"

# --- CSV ---
mkdir -p "$(dirname "$CAMPAIGN_FILE")"
cat > "$CAMPAIGN_FILE" << CSV
attack_id,phase,start_utc,end_utc,attack_type,container_count
${CAMPAIGN_ID},1,${P1_START},${P1_END},benign_only,100
${CAMPAIGN_ID},2,${P2_START},${P2_END},malicious_attack,100
${CAMPAIGN_ID},3,${P3_START},${P3_END},benign_only,100
CSV
echo ""
echo "================================================"
echo " CAMPAIGN COMPLETE"
echo "================================================"
echo "  CSV: $CAMPAIGN_FILE"
cat "$CAMPAIGN_FILE"
echo ""
echo "Phase 1 (FP pure): $P1_START -> $P1_END"
echo "Phase 2 (TP+FP):   $P2_START -> $P2_END"
echo "Phase 3 (FP pure): $P3_START -> $P3_END"
echo "================================================"
