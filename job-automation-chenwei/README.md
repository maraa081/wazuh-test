# 🤖 Auto Job Apply - Hu Chenwei

**Profil :** Graphiste / Illustratrice / Brand Designer
**Localisation :** Paris (Île-de-France)
**Type :** Alternance
**Plateformes :** LinkedIn ✅ Indeed ✅ Welcome to the Jungle ✅

## Architecture

```
wazuh-test/job-automation-chenwei/
├── bots/
│   ├── linkedin/         ← Config du bot LinkedIn (GodsScion)
│   │   ├── personals.py  ··· Infos personnelles
│   │   ├── secrets.py    ··· 🔑 Credentials + API key
│   │   ├── search.py     ··· Mots-clés, localisation, filtres
│   │   ├── questions.py  ··· Réponses aux questions type
│   │   ├── settings.py   ··· Comportement du bot
│   │   └── resume.py     ··· Infos CV
│   ├── indeed/           ← Config du bot Indeed
│   │   └── config.yaml
│   └── wtj/              ← Config du bot WelcomeToTheJungle
│       └── configuration.yml
├── scripts/
│   └── run_all.sh        ← Lanceur principal
├── config/
├── cv_templates/
├── data/                 ← Base de données SQLite + exports
├── logs/                 ← Logs de chaque exécution
├── venv/                 ← Environnement virtuel Python
└── README.md
```

## Bots utilisés

| Plateforme | Repo | Stack | Fiabilité |
|-----------|------|-------|-----------|
| **LinkedIn** | [GodsScion/Auto_job_applier_linkedIn](https://github.com/GodsScion/Auto_job_applier_linkedIn) | Python + Selenium | ⭐⭐⭐⭐⭐ Très actif, 100+ jobs/h |
| **Indeed** | [indeed_bot](https://github.com/?/indeed_bot) | Python + Camoufox | ⭐⭐⭐⭐ Bypasse Cloudflare |
| **WTJ** | [autoApply](https://github.com/?/autoApply) | Python + Selenium | ⭐⭐ Site modifié le 27/04/2026 |

## Installation

### Prérequis

- WSL2 avec Ubuntu
- Google Chrome (déjà installé)
- Python 3.14+ (déjà installé)

### Setup

```bash
cd ~/workspace/wazuh-test/job-automation-chenwei
source venv/bin/activate
```

### 🔑 Configuration obligatoire

Édite ces fichiers avec les vraies informations :

1. **`bots/linkedin/secrets.py`** → Email et mot de passe LinkedIn de Chenwei
2. **`bots/linkedin/personals.py`** → Son téléphone
3. **`bots/linkedin/questions.py`** → Son portfolio, LinkedIn URL
4. **`bots/wtj/configuration.yml`** → Email et mot de passe WTJ

### ⚙️ Configuration optionnelle

- `bots/linkedin/secrets.py` : `use_AI = True` + clé DeepSeek/OpenAI pour adapter le CV automatiquement par annonce
- `bots/linkedin/search.py` : mots-clés, localisation, filtres

## Utilisation

```bash
# Lancer LinkedIn uniquement
./scripts/run_all.sh linkedin

# Lancer Indeed uniquement
./scripts/run_all.sh indeed

# Lancer WTJ uniquement
./scripts/run_all.sh wtj

# Lancer les 3 en arrière-plan
./scripts/run_all.sh all
```

Les logs sont sauvegardés dans `logs/` horodatés.

## État des bots

### ✅ LinkedIn (GodsScion)
- 👍 Supporte Easy Apply avec questions custom
- 👍 AI resume tailoring (si clé API fournie)
- 👍 Dashboard web (http://localhost:5000)
- 👍 Undetected Chromedriver
- ⚠️ Nécessite un compte LinkedIn valide

### ✅ Indeed (Camoufox)
- 👍 Camoufox bypass Cloudflare
- 👍 Support Indeed.fr
- ⚠️ Nécessite un compte Indeed avec CV uploadé

### ⚠️ Welcome to the Jungle (autoApply)
- ❌ Redesign du site le 27/04/2026 = bot KO
- Le code est conservé mais nécessite une mise à jour
- Solution alternative : postuler manuellement via le site

## Recommandation

1. ⚡ **Commence par LinkedIn** — c'est le plus fiable et le plus efficace
2. 🔄 **Indeed** en complément (bon support)
3. 🐌 **WTJ** à faire manuellement si le bot ne fonctionne plus
