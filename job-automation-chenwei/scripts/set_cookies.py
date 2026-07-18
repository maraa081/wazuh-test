"""
Script d'injection des cookies LinkedIn
À exécuter avant de lancer le bot, pour éviter la MFA
"""

import pickle
import os
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Les cookies LinkedIn (collés depuis la console Chrome)
COOKIES_RAW = """bcookie="v=2&648b7826-8f81-40a5-84b2-6c734802dc31";
li_theme=light;
li_theme_set=app;
li_g_recent_logout=v=1&true;
JSESSIONID=ajax:2666055431697547744;
li_gc=MTswOzE3ODQzMzM1MTI7MjswMjHB0V4ooz9W0+QSR50YH9taNTmFHkMErTVNCtGiC2R/fg==;
li_alerts=e30=;
li_mc=MTsyMTsxNzg0MzM0MTY2OzI7MDIx9yTjK7MQJoHGdh/qPHTClLej38IUrlFZVzClxwxB13s="""

# Dossier de profil Chrome à créer
PROFILE_DIR = os.path.expanduser("~/.auto-job-apply-profile-linkedin")
PROFILE_DIR_PATH = Path(PROFILE_DIR)

def parse_cookies(raw):
    """Parse les cookies du format console Chrome"""
    cookies = []
    for line in raw.strip().split(";\n"):
        line = line.strip().rstrip(";")
        if "=" in line:
            name, value = line.split("=", 1)
            # Enlever les guillemets autour de la valeur
            value = value.strip('"')
            cookies.append({
                'name': name.strip(),
                'value': value,
                'domain': '.linkedin.com',
                'path': '/',
                'secure': True,
                'httpOnly': name in ('JSESSIONID', 'li_at'),
            })
    return cookies

def save_cookies_to_profile():
    """Crée un profil Chrome avec les cookies LinkedIn"""
    print("🔧 Création du profil Chrome avec cookies LinkedIn...")
    
    PROFILE_DIR_PATH.mkdir(parents=True, exist_ok=True)
    
    # Démarrer Chrome avec le profil
    options = Options()
    options.add_argument(f'--user-data-dir={PROFILE_DIR}')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Utiliser undetected_chromedriver si disponible
    try:
        import undetected_chromedriver as uc
        driver = uc.Chrome(options=options, version_main=150)
    except:
        driver = webdriver.Chrome(options=options)
    
    try:
        # Aller sur LinkedIn
        driver.get("https://www.linkedin.com")
        
        # Injecter les cookies
        parsed = parse_cookies(COOKIES_RAW)
        for cookie in parsed:
            try:
                driver.add_cookie(cookie)
                print(f"  ✅ Cookie: {cookie['name']}")
            except Exception as e:
                print(f"  ⚠️ Cookie {cookie['name']}: {e}")
        
        # Vérifier
        driver.get("https://www.linkedin.com/feed")
        import time
        time.sleep(3)
        
        if 'feed' in driver.current_url:
            print("\n✅✅✅ SESSION LINKEDIN VALIDE ! Le bot peut maintenant se connecter sans MFA")
        else:
            print(f"\n⚠️ Page actuelle: {driver.current_url}")
            print("   Les cookies peuvent être expirés")
            
        # Sauvegarder aussi les cookies dans un fichier pickle
        cookies_file = PROFILE_DIR_PATH / "linkedin_cookies.pkl"
        with open(cookies_file, 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        print(f"📁 Cookies sauvegardés: {cookies_file}")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    save_cookies_to_profile()
