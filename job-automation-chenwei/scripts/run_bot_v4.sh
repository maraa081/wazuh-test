#!/usr/bin/env bash
# =============================================================================
# Auto Job Application - Hu Chenwei
# Lancement du bot LinkedIn (Playwright V4)
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════"
echo "  Auto Job Apply - Hu Chenwei (Linux/WSL)"
echo "════════════════════════════════════════════"

# Check venv
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
    echo "✅ Virtualenv actif"
fi

echo ""
echo "🚀 Lancement du bot Playwright V4..."
echo "   Le bot va ouvrir Chrome"
echo "   Connecte-toi à LinkedIn si nécessaire"
echo ""

cd "$PROJECT_DIR"
python3 scripts/playwright_bot_v4.py

echo ""
echo "════════════════════════════════════════════"
echo "  Terminé ! Logs dans logs/"
echo "════════════════════════════════════════════"
