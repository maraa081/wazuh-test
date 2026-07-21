"""
Playwright LinkedIn Easy Apply Bot V4 - Hu Chenwei
APPROCHE FINALE: Playwright lance Chrome directement avec le profile utilisateur
Pas de remote debugging, pas de fight avec Chrome startup.
Playwright ouvre Chrome avec les donnees utilisateur existantes.
"""
import os, sys, time, json, random
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

# Import configs
sys.path.insert(0, str(Path(__file__).parent.parent / "bots" / "linkedin"))
try:
    from personals import *
    from secrets import *
    from search import *
    from questions import *
except:
    pass

LOG_DIR = Path(__file__).parent / "logs"
DATA_DIR = Path(__file__).parent / "data"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        clean = msg.encode("ascii", "replace").decode()
    except:
        clean = str(msg)
    line = f"[{ts}] {clean}"
    try: print(line, flush=True)
    except: pass
    try:
        (LOG_DIR / "playwright_bot.log").open("a", encoding="utf-8").write(f"[{ts}] {msg}\n")
    except:
        pass

# Module-level defaults (fallback si les imports config echouent)
_PORTFOLIO = "https://github.com/maraa081/wazuh-test/tree/main/test"
_LINKEDIN_URL = "https://www.linkedin.com/in/chenwei-h-9223b3422/"
_PHONE = "+33678352974"
_EMAIL = "via0000413@gmail.com"
_MOTIVATION = "Artiste et designer visuelle formee aux Beaux-Arts de Shanghai, Nantes et Besancon. Je recherche une alternance en design graphique, illustration ou branding a partir de septembre 2026. Je maîtrise Photoshop, Illustrator, InDesign, Procreate, ZBrush."
_ANSWERS = {
    "portfolio|site|lien web": _PORTFOLIO,
    "linkedin": _LINKEDIN_URL,
    "telephone|phone|mobile": _PHONE,
    "email|courriel": _EMAIL,
    "motivation|lettre|pourquoi": _MOTIVATION,
    "salaire|pretention": "A discuter selon la grille de l'ecole",
    "disponible|disponibilite|commencer": "A partir de septembre 2026",
    "experience|parcours|formation": "Formation Beaux-Arts Shanghai, Nantes, Besancon. Projets identite visuelle Yuffee, exposition Shanghai, collaboration Artgogo x Brother China",
    "logiciel|adobe|competence": "Photoshop, Illustrator, InDesign, Procreate, ZBrush, Figma",
    "langue": "Chinois (maternel), Francais (B2), Anglais (intermediaire)",
    "visa|sponsor|autorisation": "Non - Titre de sejour valide",
    "rythme|alternance": "3j entreprise / 2j ecole",
    "annee|years": "2",
    "souhaitez|poste|role": "Graphiste / Illustratrice en alternance",
}

def answer_question(question_text):
    q = question_text.lower()
    for keywords, answer in _ANSWERS.items():
        if any(w in q for w in keywords.split("|")):
            return answer
    return None

def handle_easy_apply(page):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    for step in range(10):
        time.sleep(random.uniform(1.5, 3))
        
        # Fill text inputs
        try:
            inputs = page.locator("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea")
            count = inputs.count()
            for i in range(count):
                inp = inputs.nth(i)
                try:
                    if inp.get_attribute("value"): continue
                except: continue
                ph = (inp.get_attribute("placeholder") or "").strip()
                aria = (inp.get_attribute("aria-label") or "").strip()
                name = (inp.get_attribute("name") or "").strip()
                txt = f"{ph} {aria} {name}"
                answer = answer_question(txt)
                if answer:
                    try: inp.fill(answer); log(f"    Rempli: {txt[:20]}...")
                    except: pass
        except: pass
        
        # Handle radio
        try:
            for r in page.locator("input[type=radio], input[type=checkbox]").all():
                if r.is_checked(): continue
                lt = (r.evaluate("el => document.querySelector('label[for=\"' + el.id + '\"]')?.textContent || ''") or "").lower()
                if any(w in lt for w in ["oui", "yes", "agree", "accept"]):
                    try: r.check(); log(f"    Check: {lt[:20]}...")
                    except: pass
        except: pass
        
        # Click submit
        try:
            for sel in ["button:has-text('Suivant')", "button:has-text('Next')", "button:has-text('Submit')", "button:has-text('Examiner')", "button:has-text('Review')", "button:has-text('Envoyer')", "button:has-text('Postuler')", "button:has-text('Apply')"]:
                btn = page.locator(sel).first
                if btn.is_visible():
                    t = btn.text_content() or ""
                    btn.click()
                    log(f"    Bouton: {t[:20]}")
                    time.sleep(random.uniform(2, 4))
                    break
            else:
                log(f"    Plus de bouton (step {step+1})")
                break
        except:
            log(f"    Bouton pas trouve (step {step+1})")
            break
        
        # Check success
        try:
            body = page.evaluate("document.body.innerText") or ""
            if "Candidature envoy" in body or "Application sent" in body:
                log("  ✅ CANDIDATURE ENVOYEE!")
                try:
                    d = page.locator("button[aria-label=Dismiss], button:has-text('Done'), button:has-text('Termine')").first
                    if d.is_visible(): d.click(); time.sleep(1)
                except: pass
                return True
        except: pass
    
    return False

def main():
    from playwright.sync_api import sync_playwright
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log("=" * 50)
    log("  LinkedIn Easy Apply Bot V4 - Hu Chenwei")
    log("  Playwright + Chrome natif + profil utilisateur")
    log("=" * 50)
    
        # Get config vars (module-level globals from imports)
    cf_username = globals().get("username", "chen771216000@gmail.com")
    cf_password = globals().get("password", "1216413@Huchenyang")
    cf_terms = globals().get("search_terms", ["alternance graphiste", "alternance graphisme", "alternance illustrateur", "alternance branding"])
    cf_location = globals().get("search_location", "Paris, France")
    
    # Get the user data path
    user_data_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
    if not os.path.exists(user_data_dir):
        user_data_dir = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Google", "Chrome", "User Data")
    
    log(f"User data: {user_data_dir}")
    
    with sync_playwright() as p:
        # Launch Chrome with user data dir directly
        # This preserves all cookies and sessions (including LinkedIn login)
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            channel="chrome",
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            # Check LinkedIn login
            log("Checking LinkedIn login status...")
            page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=15000)
            time.sleep(2)
            
            url = page.url.lower()
            log(f"URL: {url[:80]}")
            
            if "login" in url or "checkpoint" in url:
                log("⚠️ PAS CONNECTE A LINKEDIN")
                log("Le bot va essayer de se connecter avec les credentials...")
                
                page.goto("https://www.linkedin.com/login", wait_until="load", timeout=15000)
                time.sleep(2)
                
                # Fill login via JS
                filled = page.evaluate("""({u, p}) => {
                    let email = false, pass = false;
                    document.querySelectorAll('input').forEach(inp => {
                        const ph = (inp.placeholder || '').toLowerCase();
                        const type = (inp.type || '').toLowerCase();
                        if (!email && (ph.includes('email') || ph.includes('phone') || type === 'email' || type === 'text')) {
                            const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            s.call(inp, u);
                            inp.dispatchEvent(new Event('input', {bubbles:true}));
                            inp.dispatchEvent(new Event('change', {bubbles:true}));
                            email = true;
                        }
                        if (!pass && (ph.includes('password') || type === 'password')) {
                            const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                            s.call(inp, p);
                            inp.dispatchEvent(new Event('input', {bubbles:true}));
                            inp.dispatchEvent(new Event('change', {bubbles:true}));
                            pass = true;
                        }
                    });
                    return {email, pass};
                }""", {"u": cf_username, 
                       "p": cf_password})
                
                log(f"Login fill: email={filled.get('email')}, pass={filled.get('pass')}")
                time.sleep(1)
                
                # Click submit
                page.evaluate("""() => {
                    const btn = document.querySelector('button[type=submit]');
                    if (btn) { btn.click(); return true; }
                    return false;
                }""")
                
                time.sleep(5)
                
                # Check result
                url2 = page.url.lower()
                log(f"After login: {url2[:80]}")
                
                if "login" in url2 or "checkpoint" in url2:
                    log("⚠️ Login echoue - Chrome va rester ouvert")
                    log("Connecte-toi manuellement dans la fenetre Chrome")
                    log("Le bot attend jusqu'a 5 minutes...")
                    
                    for i in range(60):
                        try:
                            page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=10000)
                            time.sleep(2)
                            if "feed" in page.url.lower():
                                log("✅ Connecte!")
                                break
                        except: pass
                        time.sleep(5)
                    else:
                        log("❌ TIMEOUT connexion")
                        return
            
            # Now apply!
            terms = cf_terms
            loc = cf_location
            
            total_applied = 0
            max_apps = 1
            
            for term in terms:
                if total_applied >= max_apps: break
                
                log(f"\nRecherche: {term}")
                qs = f"keywords={term.replace(' ', '+')}&location={loc.replace(' ', '+').replace(',', '%2C')}&f_AL=true&start=0"
                
                try:
                    page.goto(f"https://www.linkedin.com/jobs/search/?{qs}", wait_until="load", timeout=20000)
                except: pass
                time.sleep(3)
                
                # Scroll to load jobs
                for _ in range(3):
                    try:
                        cards = page.locator("[data-entity-urn*=jobPosting], .job-card-container, [class*=job-card]")
                        if cards.count() > 0: break
                    except: pass
                    page.evaluate("window.scrollBy(0, 400)")
                    time.sleep(2)
                
                try:
                    cards_count = cards.count()
                except:
                    cards_count = 0
                log(f"  {cards_count} offres chargees")
                
                for i in range(min(cards_count, 5)):
                    if total_applied >= max_apps: break
                    
                    try:
                        log(f"  Offre {i+1}...")
                        cards.nth(i).click()
                        time.sleep(random.uniform(2, 4))
                        
                        # Find Easy Apply
                        easy = None
                        for t in ["Candidature simplifiee", "Easy Apply", "Postuler facilement"]:
                            try:
                                b = page.locator(f"button:has-text('{t}')").first
                                if b.is_visible(timeout=2000):
                                    easy = b; break
                            except: pass
                        
                        if not easy:
                            log("    Pas de Easy Apply")
                            continue
                        
                        log("  ✅ Easy Apply!")
                        easy.click()
                        time.sleep(random.uniform(2, 3))
                        
                        if handle_easy_apply(page):
                            total_applied += 1
                            log(f"  ** Total: {total_applied} **")
                            time.sleep(random.uniform(5, 10))
                    
                    except Exception as e:
                        log(f"    Error: {str(e)[:60]}")
            
            log(f"\n{'='*50}")
            log(f"  FINI - {total_applied} candidature(s)")
            log(f"{'='*50}")
            
        except Exception as e:
            log(f"FATAL: {str(e)[:200]}")
        finally:
            context.close()

if __name__ == "__main__":
    main()
