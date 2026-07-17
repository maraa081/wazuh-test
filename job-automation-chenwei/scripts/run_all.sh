#!/usr/bin/env bash
# =============================================================================
# Auto Job Application - Hu Chenwei
# Lancement des bots pour LinkedIn, Indeed et Welcome to the Jungle
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$PROJECT_DIR/venv"
BOTS_DIR="$PROJECT_DIR/bots"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"
DATE_TAG=$(date '+%Y-%m-%d_%H-%M')

mkdir -p "$LOG_DIR" "$DATA_DIR"

echo "════════════════════════════════════════════"
echo "  🔧 AUTO JOB APPLY - Hu Chenwei"
echo "  📅 $DATE_TAG"
echo "════════════════════════════════════════════"

usage() {
    echo "Usage: $0 [linkedin|indeed|wtj|all]"
    echo ""
    echo "  linkedin   → Lancer le bot LinkedIn (GodsScion)"
    echo "  indeed     → Lancer le bot Indeed (Camoufox)"
    echo "  wtj        → Lancer le bot Welcome to the Jungle"
    echo "  all        → Lancer les 3 bots (recommandé en arrière-plan)"
    echo "  setup      → Configurer l'environnement (installer dépendances)"
    exit 1
}

check_venv() {
    if [ ! -f "$VENV/bin/activate" ]; then
        echo "❌ Environnement virtuel introuvable !"
        echo "   Lance d'abord : $0 setup"
        exit 1
    fi
}

run_linkedin() {
    echo ""
    echo "─── LinkedIn Bot ───"
    check_venv
    source "$VENV/bin/activate"
    
    # Vérifier si les credentials sont configurés
    if grep -q 'username = ""' "$BOTS_DIR/linkedin/secrets.py"; then
        echo "⚠️  LinkedIn credentials non configurés !"
        echo "   Édite : $BOTS_DIR/linkedin/secrets.py"
        return 1
    fi
    
    cd "$PROJECT_DIR/../../godsScion_bot"
    
    # Copier les configs personnalisées
    cp "$BOTS_DIR/linkedin/personals.py" config/personals.py
    cp "$BOTS_DIR/linkedin/secrets.py" config/secrets.py
    cp "$BOTS_DIR/linkedin/search.py" config/search.py
    cp "$BOTS_DIR/linkedin/questions.py" config/questions.py
    cp "$BOTS_DIR/linkedin/settings.py" config/settings.py
    cp "$BOTS_DIR/linkedin/resume.py" config/resume.py
    
    echo "✅ Config LinkedIn chargée"
    echo "🚀 Lancement bot LinkedIn (Xvfb + headless)..."
    
    # Démarrer Xvfb si pas déjà lancé
    if ! pgrep -x Xvfb > /dev/null; then
        Xvfb :99 -screen 0 1920x1080x24 -nolisten unix &
        sleep 1
    fi
    
    cd "$PROJECT_DIR/../../godsScion_bot"
    
    # Copier les configs personnalisées
    cp "$BOTS_DIR/linkedin/personals.py" config/personals.py
    cp "$BOTS_DIR/linkedin/secrets.py" config/secrets.py
    cp "$BOTS_DIR/linkedin/search.py" config/search.py
    cp "$BOTS_DIR/linkedin/questions.py" config/questions.py
    cp "$BOTS_DIR/linkedin/settings.py" config/settings.py
    cp "$BOTS_DIR/linkedin/resume.py" config/resume.py
    
    DISPLAY=:99 python3 runAiBot.py 2>&1 | tee "$LOG_DIR/linkedin_$DATE_TAG.log"
    
    cd "$PROJECT_DIR"
    
    cd "$PROJECT_DIR"
}

run_indeed() {
    echo ""
    echo "─── Indeed Bot (Camoufox) ───"
    check_venv
    source "$VENV/bin/activate"
    
    cd "$PROJECT_DIR/../../indeed_bot"
    
    cp "$BOTS_DIR/indeed/config.yaml" config.yaml
    
    echo "🚀 Lancement du bot Indeed..."
    echo "   👉 Assure-toi que le compte Indeed de Chenwei a :"
    echo "      - Un CV uploadé sur son profil"
    echo "      - Nom, prénom, adresse, téléphone remplis"
    echo ""
    python3 indeed_bot.py 2>&1 | tee "$LOG_DIR/indeed_$DATE_TAG.log"
    
    cd "$PROJECT_DIR"
}

run_wtj() {
    echo ""
    echo "─── Welcome to the Jungle Bot ───"
    echo "❌  BOT CASSÉ : Le site WTJ a été redesigné le 27/04/2026"
    echo "    Le bot autoApply ne fonctionne plus depuis cette date."
    echo ""
    echo "   Solution : postuler manuellement via :"
    echo "   https://www.welcometothejungle.com/fr/me/applications"
    echo "   Les credentials sont configurés dans bots/wtj/configuration.yml"
    echo ""
}

setup_env() {
    echo ""
    echo "─── Installation de l'environnement ───"
    
    # Vérifier Chrome
    if ! command -v google-chrome-stable &>/dev/null; then
        echo "📦 Installation de Google Chrome..."
        wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        sudo dpkg -i /tmp/chrome.deb || sudo apt-get install -f -y -qq
    fi
    echo "✅ Chrome : $(google-chrome-stable --version)"
    
    # Créer le venv
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    
    # Installer dépendances LinkedIn bot
    pip install -q undetected-chromedriver pyautogui setuptools openai flask flask-cors pandas pyyaml
    
    # Installer dépendances Indeed bot
    pip install -q camoufox
    
    echo "✅ Environnement installé"
    echo ""
    echo "⚠️  ÉTAPE MANUELLE REQUISE :"
    echo "   Configure les credentials dans :"
    echo "   - bots/linkedin/secrets.py   (LinkedIn)"
    echo "   - bots/wtj/configuration.yml (WTJ)"
    echo "   - bots/indeed/ n'a pas besoin de credentials (navigateur déjà connecté)"
    echo ""
}

case "${1:-help}" in
    linkedin)
        run_linkedin
        ;;
    indeed)
        run_indeed
        ;;
    wtj)
        run_wtj
        ;;
    all)
        echo "🚀 Lancement de tous les bots (arrière-plan)..."
        nohup "$0" linkedin > "$LOG_DIR/linkedin_bg.log" 2>&1 &
        echo "  ✅ LinkedIn démarré (PID: $!)"
        nohup "$0" indeed > "$LOG_DIR/indeed_bg.log" 2>&1 &
        echo "  ✅ Indeed démarré (PID: $!)"
        nohup "$0" wtj > "$LOG_DIR/wtj_bg.log" 2>&1 &
        echo "  ✅ WTJ démarré (PID: $!)"
        echo ""
        echo "📋 Logs : $LOG_DIR/"
        ;;
    setup)
        setup_env
        ;;
    *)
        usage
        ;;
esac
