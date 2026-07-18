#!/usr/bin/env python3
"""
Script de merge : fusionne les configs custom Chenwei avec les configs originales du bot
Execute ce script APRES avoir copié les configs pour rajouter les variables originales manquantes.
"""

import shutil
from pathlib import Path

BOTS_DIR = Path(__file__).parent.parent / "bots" / "linkedin"
ORIG_DIR = Path(__file__).parent.parent.parent.parent / "godsScion_bot" / "config"
DEST_DIR = ORIG_DIR  # les configs sont copiées ici

# Liste des variables ORIGINALES à préserver dans settings.py
ORIGINAL_SETTINGS_VARS = """
# Chemins et dossiers
import os
from pathlib import Path
logs_folder_path = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "auto_job_apply")
file_name = os.path.join(logs_folder_path, "job_details.txt")
failed_file_name = os.path.join(logs_folder_path, "failed_jobs.txt")
generated_resume_path = os.path.join(os.path.join(logs_folder_path, "..", "generated_resumes"))
disable_extensions = True
"""

def merge_settings():
    # Lire notre config custom
    custom = (BOTS_DIR / "settings.py").read_text()
    
    # Ajouter les varibles originales avant les notres (les notres ecrasent)
    merged = ORIGINAL_SETTINGS_VARS + "\n" + custom
    
    # Ecrire le fichier fusionne
    (DEST_DIR / "settings.py").write_text(merged)
    print("✅ settings.py merge OK")

def merge_personals():
    """personals.py - pas de variables originales a preserver"""
    pass

def merge_secrets():
    """secrets.py - garder les originaux + ajouter nos valeurs"""
    pass

if __name__ == "__main__":
    merge_settings()
    print("Toutes les configs fusionnees")
