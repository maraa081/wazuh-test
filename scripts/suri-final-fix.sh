#!/bin/bash
# suri-final-fix.sh — Réparation finale + test
# Usage: sudo bash suri-final-fix.sh

echo "=========================================="
echo " SURICATA FINAL FIX — $(date)"
echo "=========================================="

# 1 — S'assurer que local.rules est au bon endroit
echo ""
echo "--- 1. Copie local.rules dans le bon dossier ---"
if [ -f /etc/suricata/rules/local.rules ]; then
    cp /etc/suricata/rules/local.rules /var/lib/suricata/rules/local.rules
    chown suricata:suricata /var/lib/suricata/rules/local.rules
    chmod 644 /var/lib/suricata/rules/local.rules
    echo "  ✅ local.rules copié dans /var/lib/suricata/rules/"
fi

# 2 — Supprimer la copie du mauvais chemin si elle existe
echo ""
echo "--- 2. Nettoyage des doublons rule-files ---"
# Vérifier si local.rules apparaît 2 fois
COUNT=$(grep -c "local.rules" /etc/suricata/suricata.yaml || true)
if [ "$COUNT" -gt 1 ]; then
    # Garder seulement la première occurrence
    sed -i '/^  - local.rules/,//{2,/{/!{/^  - local.rules/d}}' /etc/suricata/suricata.yaml 2>/dev/null || true
    echo "  ✅ Doublon supprimé"
fi

# 3 — Redémarrer Suricata
echo ""
echo "--- 3. Redémarrage Suricata ---"
systemctl restart suricata
sleep 2
systemctl is-active suricata >/dev/null && echo "  ✅ OK" || echo "  ❌ Échec"

# 4 — Vérifier qu'il n'y a pas d'erreur
echo ""
echo "--- 4. Logs récents ---"
journalctl -u suricata --since "30 sec ago" --no-pager 2>/dev/null | grep -E "rules|error|fail|local|success" | tail -5 || echo "  (rien)"

echo ""
echo "=========================================="
echo " SURICATA REDÉMARRÉ — PRÊT POUR LE TEST"
echo "=========================================="
echo ""
echo "Depuis ParrotOS, LANCE :"
echo "  nmap -sS -p 22,80 192.168.30.10"
echo ""
echo "Ensuite vérifie avec :"
echo "  curl -sL https://raw.githubusercontent.com/maraa081/wazuh-test/main/scripts/suri-test.sh | sudo bash"
echo "=========================================="
