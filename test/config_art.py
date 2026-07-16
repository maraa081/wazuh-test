"""
Configuration du systeme de candidature automatique - VERSION GRATUITE
Profil : Hu Chenwei - Graphiste / Illustratrice / Brand Designer
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CV_DIR = BASE_DIR / "cv_templates"

for directory in [DATA_DIR, LOGS_DIR, CV_DIR]:
    directory.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI_ADAPTATION = bool(OPENAI_API_KEY)

if not OPENAI_API_KEY:
    print("Mode GRATUIT : adaptation basique du CV")
else:
    print("Mode IA : adaptation intelligente activee")

SEARCH_PROFILES = {
    "graphiste_branding": {
        "keywords": "alternance graphiste graphisme design graphique illustrateur illustration branding identite visuelle direction artistique PAO edition creation studio creatif design visuel communication visuelle packaging maquettiste affichiste arts appliques multimedia creation numerique typographie affiche print digital webdesign motion",
        "location": "Paris",
        "exclude_keywords": ["CDI", "CDD", "freelance", "benevole", "vendeur", "commercial", "comptable", "ingenieur", "informatique", "technicien"],
        "min_salary": 0,
        "max_pages_per_site": 10,
        "target_keywords": ["graphisme", "design graphique", "branding", "identite visuelle", "illustration", "creation", "PAO", "edition", "packaging", "affiche", "print", "digital", "direction artistique", "typographie", "mise en page", "Photoshop", "InDesign", "Illustrator", "Procreate", "ZBrush", "studio", "agence"]
    },
    "illustratrice": {
        "keywords": "alternance illustrateur illustratrice illustration dessinateur dessin peinture arts graphiques creation visuelle artiste edition presse animation storytelling",
        "location": "Paris",
        "exclude_keywords": ["CDI", "CDD", "freelance"],
        "min_salary": 0,
        "max_pages_per_site": 8,
        "target_keywords": ["illustration", "dessin", "peinture", "edition", "narration", "visuel", "sculpture", "animation", "storyboard", "concept art", "aquarelle"]
    },
    "art_creatif": {
        "keywords": "alternance creation studio creatif agence design atelier beaux arts galerie exposition direction artistique artistique art visuel mediation culturelle production artistique",
        "location": "Paris",
        "exclude_keywords": ["CDI", "CDD", "freelance"],
        "min_salary": 0,
        "max_pages_per_site": 5,
        "target_keywords": ["creation", "art", "artistique", "studio", "atelier", "galerie", "exposition", "sculpture", "contemporain", "culturel", "production"]
    }
}

DEFAULT_PROFILE = "graphiste_branding"

CV_ADAPTATION_CONFIG = {
    "use_ai": USE_AI_ADAPTATION,
    "basic_adaptation": {
        "emphasize_matching_keywords": True,
        "reorder_skills": True,
        "adapt_title": True,
        "max_keywords_to_emphasize": 5,
        "synonyms": {}
    }
}

SITES_CONFIG = {
    "indeed": {"enabled": True, "base_url": "https://fr.indeed.com/jobs", "priority": 1, "delay_between_requests": (2, 5)},
    "linkedin": {"enabled": True, "base_url": "https://www.linkedin.com/jobs/search/", "priority": 2, "delay_between_requests": (3, 7)},
    "welcome_to_the_jungle": {"enabled": True, "base_url": "https://www.welcometothejungle.com/fr/jobs", "priority": 3, "delay_between_requests": (2, 4)}
}

APPLICATION_CONFIG = {
    "delay_between_applications": {"min": 30, "max": 120, "variation": 0.2},
    "daily_limits": {"max_applications_per_day": 25, "max_applications_per_hour": 5, "pause_after_applications": 5, "pause_duration": 300},
    "quality_filters": {"min_description_length": 100, "exclude_companies": [], "require_salary": False, "max_application_age_days": 14}
}

CV_CONFIG = {
    "base_template_path": CV_DIR / "cv_base.txt",
    "adaptable_sections": {"title": True, "skills": True, "experience_descriptions": True, "keywords_integration": True},
    "adaptation_rules": {"keep_structure": True, "max_keywords_per_section": 5, "synonym_replacement": True, "preserve_achievements": True}
}

DATABASE_CONFIG = {"path": DATA_DIR / "jobs.db", "backup_frequency": "daily", "cleanup_old_jobs_days": 90, "export_formats": ["csv", "excel"]}

LOGGING_CONFIG = {"level": "INFO", "file_path": LOGS_DIR / "job_automation.log", "max_file_size_mb": 10, "backup_count": 5, "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}

SELENIUM_CONFIG = {"headless": False, "window_size": (1920, 1080), "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "implicit_wait": 10, "page_load_timeout": 30, "download_dir": DATA_DIR / "downloads"}

def get_profile_config(profile_name=None):
    if profile_name is None:
        profile_name = DEFAULT_PROFILE
    return SEARCH_PROFILES.get(profile_name, SEARCH_PROFILES[DEFAULT_PROFILE])

def validate_config():
    errors = []
    if not CV_CONFIG["base_template_path"].exists():
        errors.append("Template CV manquant: " + str(CV_CONFIG["base_template_path"]))
    if not SEARCH_PROFILES:
        errors.append("Aucun profil de recherche defini")
    if errors:
        print("Erreurs de configuration:")
        for e in errors:
            print("  - " + e)
        return False
    print("Configuration valide")
    if not USE_AI_ADAPTATION:
        print("Mode adaptation basique (gratuit) active")
    else:
        print("Mode adaptation IA active")
    return True

def extract_keywords_basic(job_title, job_description, profile_keywords):
    text = (job_title + " " + job_description).lower()
    found = []
    for kw in profile_keywords:
        if kw.lower() in text:
            found.append(kw)
    return found[:10]

def adapt_cv_basic(base_cv, keywords, profile_config):
    adapted = base_cv
    kw_lower = [k.lower() for k in keywords]
    if any(k in " ".join(kw_lower) for k in ["graphiste", "graphisme", "design graphique"]):
        adapted = adapted.replace("Graphiste & Illustratrice", "Graphiste & Brand Designer")
    elif any(k in " ".join(kw_lower) for k in ["illustrat", "dessin"]):
        adapted = adapted.replace("Graphiste & Illustratrice", "Illustratrice & Artiste Visuelle")
    if keywords:
        adapted += "\n\nCOMPETENCES RECHERCHEES POUR CE POSTE\n" + ", ".join(keywords[:8])
    return adapted
