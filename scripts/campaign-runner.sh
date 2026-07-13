#!/bin/bash
# campaign-runner.sh — Génère des attaques + trafic bénin pour le dataset
# Usage: sudo bash campaign-runner.sh
# À lancer depuis ParrotOS

set -euo pipefail

TARGET="192.168.30.10"
CAMPAIGN_ID="CAMP$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="/tmp/wazuh-campaign-$CAMPAIGN_ID"
mkdir -p "$OUTPUT_DIR"

echo "================================================================"
echo " CAMPAIGN RUNNER — $CAMPAIGN_ID"
echo " Cible: $TARGET"
echo " Durée: 10 minutes"
echo "================================================================"
echo ""

# --- 1. Vérification des outils ---
echo "=== 1. Vérification outils ==="
for cmd in nmap hydra ssh ping curl dig hping3; do
    if command -v $cmd &>/dev/null; then
        echo "  ✅ $cmd trouvé"
    else
        echo "  ⚠️  $cmd manquant"
    fi
done

# --- 2. Fichier de campagne ---
CSV="$OUTPUT_DIR/campaign_$CAMPAIGN_ID.csv"
echo "attack_id,start_utc,end_utc,attack_type,target_ip,target_port,tool" > "$CSV"
echo "  → $CSV"

# Helper function to log a campaign entry
log_attack() {
    local type="$1" tool="$2" port="$3"
    local start="$4" end="$5"
    echo "$CAMPAIGN_ID,$start,$end,$type,$TARGET,$port,$tool" >> "$CSV"
}

# --- 3. Lancement des attaques ---
echo ""
echo "=== 2. Génération du trafic (10 minutes) ==="
echo ""

START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
END_TIME=$(date -u -d "+10 minutes" +"%Y-%m-%dT%H:%M:%SZ")

echo "  Début: $START_TIME"
echo "  Fin:   $END_TIME"

# --- Vague 1: Trafic bénin (toutes les 30s) ---
echo ""
echo "--- Trafic bénin ---"

# SSH connexion normale (toutes les 60s)
for i in 1 2 3 4 5; do
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 vboxuser@$TARGET "echo 'benign ssh $i'" 2>/dev/null || true
    sleep 2
done &
BG_PID=$!

# DNS queries (toutes les 10s)
for i in 1 2 3 4 5 6 7 8 9 10; do
    dig +short google.com @8.8.8.8 >/dev/null 2>&1 || true
    dig +short github.com @8.8.8.8 >/dev/null 2>&1 || true
    sleep 10
done &
BG_PID2=$!

# Pings (toutes les 5s)
(
for i in $(seq 1 60); do
    ping -c 1 -W 2 $TARGET >/dev/null 2>&1 || true
    sleep 5
done
) &
BG_PID3=$!

# --- Vague 2: Attaques ---
echo ""
echo "--- Attaques ---"

# Attaque 1: Nmap SYN scan (t=30s)
sleep 30
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 nmap -sS (t=30s)"
nmap -sS -p 22,80,443,3306,8080 -T4 $TARGET -oN "$OUTPUT_DIR/nmap_syn.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "nmap_syn_scan" "nmap" "22,80,443" "$TS" "$TE"

# Attaque 2: Nmap OS fingerprint (t=120s)
sleep 90
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 nmap -O (OS fingerprint, t=120s)"
nmap -O -T4 $TARGET -oN "$OUTPUT_DIR/nmap_os.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "nmap_os_fingerprint" "nmap" "22,80" "$TS" "$TE"

# Attaque 3: Nmap -sV version scan (t=180s)
sleep 30
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 nmap -sV (version, t=180s)"
nmap -sV -p 22,80 -T4 $TARGET -oN "$OUTPUT_DIR/nmap_sv.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "nmap_service_scan" "nmap" "22,80" "$TS" "$TE"

# Attaque 4: SSH bruteforce hydra (t=240s)
sleep 30
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 hydra bruteforce (t=240s)"
hydra -l root -p admin123 ssh://$TARGET -t 2 -o "$OUTPUT_DIR/hydra.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "ssh_bruteforce" "hydra" "22" "$TS" "$TE"

# Attaque 5: Nmap full port scan -p- (t=330s)
sleep 60
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 nmap -p- (full scan, t=330s)"
nmap -p 1-1000 -T4 $TARGET -oN "$OUTPUT_DIR/nmap_full.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "nmap_full_scan" "nmap" "1-1000" "$TS" "$TE"

# Attaque 6: Nmap aggressive -A (t=420s)
sleep 60
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "  🔴 nmap -A (aggressive, t=420s)"
nmap -A -T4 $TARGET -oN "$OUTPUT_DIR/nmap_aggressive.txt" 2>/dev/null
TE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
log_attack "nmap_aggressive" "nmap" "22,80" "$TS" "$TE"

# Fin: laisser le trafic bénin finir
sleep 30

echo ""
echo "================================================================"
echo " CAMPAGNE TERMINÉE"
echo "================================================================"
echo ""
echo "  Fichier campagne: $CSV"
echo "  Logs: $OUTPUT_DIR/"
echo ""
echo "Envoyer à la cible:"
echo "  scp $CSV vboxuser@$TARGET:~/"
echo "  scp $OUTPUT_DIR/*.txt vboxuser@$TARGET:~/campaign_logs/"
echo ""
echo "Puis sur la cible (Ubuntu CibleWazuh):"
echo "  Copier le CSV dans /home/user/.openclaw/workspace/wazuh-test/data/attack_windows/"
echo "  Lancer: python3 pipeline/01_collect_alerts.py"
echo "================================================================"
