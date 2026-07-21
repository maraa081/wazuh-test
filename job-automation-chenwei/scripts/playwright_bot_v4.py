"""
Playwright LinkedIn Easy Apply Bot V4 - Hu Chenwei
APPROCHE FINALE: Playwright + Chromium integre + login fiable
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
    clean = str(msg).encode("ascii", "replace").decode()
    print(f"[{ts}] {clean}", flush=True)
    try:
        (LOG_DIR / "playwright_bot.log").open("a", encoding="utf-8").write(f"[{ts}] {msg}\n")
    except:
        pass

# Default answers for Easy Apply form
_ANSWERS = {
    "portfolio|site|lien web": "https://github.com/maraa081/wazuh-test/tree/main/test",
    "linkedin": "https://www.linkedin.com/in/chenwei-h-9223b3422/",
    "telephone|phone|mobile": "+33678352974",
    "email|courriel": "via0000413@gmail.com",
    "motivation|lettre|pourquoi": "Artiste et designer visuelle formee aux Beaux-Arts de Shanghai, Nantes et Besancon. Je recherche une alternance en design graphique, illustration ou branding.",
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
            for inp in page.locator("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea").all():
                try:
                    if inp.get_attribute("value"): continue
                except: continue
                ph = (inp.get_attribute("placeholder") or "").strip()
                aria = (inp.get_attribute("aria-label") or "").strip()
                name = (inp.get_attribute("name") or "").strip()
                txt = f"{ph} {aria} {name}"
                answer = answer_question(txt)
                if answer:
                    try: inp.fill(answer); log(f"    Rempli: {txt[:20]}..."); time.sleep(0.3)
                    except: pass
        except: pass
        # Handle radio/checkboxes
        try:
            for r in page.locator("input[type=radio], input[type=checkbox]").all():
                if r.is_checked(): continue
                lt = (r.evaluate("el => document.querySelector('label[for=\"' + el.id + '\"]')?.textContent || ''") or "").lower()
                if any(w in lt for w in ["oui", "yes", "agree", "accept"]):
                    try: r.check(); log(f"    Check: {lt[:20]}...")
                    except: pass
        except: pass
        # Click submit/next
        try:
            btn = page.locator("button[type=submit], button:has-text('Suivant'), button:has-text('Next'), button:has-text('Submit'), button:has-text('Examiner'), button:has-text('Review'), button:has-text('Envoyer'), button:has-text('Postuler'), button:has-text('Apply')").first
            if btn.is_visible(timeout=2000):
                t = btn.text_content() or ""
                btn.click()
                log(f"    Bouton: {t[:20]}")
                time.sleep(random.uniform(2, 3))
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
                    if d.is_visible(timeout=1000): d.click(); time.sleep(1)
                except: pass
                return True
        except: pass
    return False

def do_login(page, username, password):
    """Try to log in to LinkedIn with retries and fallback to manual."""
    MAX_WAIT = 300  # 5 minutes in seconds
    CHECK_INTERVAL = 5
    
    page.goto("https://www.linkedin.com/login", wait_until="load", timeout=20000)
    time.sleep(3)
    
    # Method 1: Try automatic login with JS filling
    filled = page.evaluate("""({u, p}) => {
        const uid = document.getElementById('session_key');
        const pwd = document.getElementById('session_password');
        if (!uid || !pwd) {
            // Fallback: find by name
            const allInputs = document.querySelectorAll('input');
            let foundEmail = false, foundPass = false;
            allInputs.forEach(inp => {
                if (!foundEmail && (inp.name === 'session_key' || inp.placeholder.toLowerCase().includes('email') || inp.placeholder.toLowerCase().includes('phone'))) {
                    inp.focus(); inp.value = ''; inp.value = u;
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    foundEmail = true;
                }
                if (!foundPass && inp.type === 'password') {
                    inp.focus(); inp.value = ''; inp.value = p;
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                    foundPass = true;
                }
            });
            return {email: foundEmail, pass: foundPass};
        }
        uid.focus(); uid.value = ''; uid.value = u;
        uid.dispatchEvent(new Event('input', {bubbles: true}));
        uid.dispatchEvent(new Event('change', {bubbles: true}));
        pwd.focus(); pwd.value = ''; pwd.value = p;
        pwd.dispatchEvent(new Event('input', {bubbles: true}));
        pwd.dispatchEvent(new Event('change', {bubbles: true}));
        return {email: true, pass: true};
    }""", {"u": username, "p": password})
    log(f"Login JS fill: email={filled.get('email')}, pass={filled.get('pass')}")
    time.sleep(1)
    
    # Click Sign in button
    btn_clicked = page.evaluate("""() => {
        const btn = document.querySelector('button[type=submit]');
        if (btn) { btn.click(); return true; }
        return false;
    }""")
    log(f"Submit button clicked: {btn_clicked}")
    
    time.sleep(5)
    url_after = page.url.lower()
    log(f"URL after submit: {url_after[:80]}")
    
    if "feed" in url_after:
        log("✅ Connecte automatiquement!")
        return True
    
    # Login failed - wait for manual login
    log("⚠️ Login automatique echoue")
    log("Connecte-toi manuellement dans la fenetre Chromium")
    log(f"Le bot attend jusqu'a {MAX_WAIT//60} minutes...")
    
    start = time.time()
    while time.time() - start < MAX_WAIT:
        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=15000)
            time.sleep(2)
            u = page.url.lower()
            if "feed" in u:
                log("✅ Connecte manuellement!")
                return True
            # Still on login page - check if manual login in progress
            log(f"  Attente connexion... ({int(time.time()-start)}s)")
        except Exception as e:
            log(f"  Goto error: {str(e)[:50]}")
        time.sleep(CHECK_INTERVAL)
    
    log("❌ TIMEOUT - pas connecte apres 5 minutes")
    return False

def find_job_links(page):
    """Find all job posting links on the search page using multiple strategies."""
    return page.evaluate("""() => {
        // Strategy A: Direct job links
        let links = Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'));
        if (links.length > 0) return links.map(a => a.href);
        
        // Strategy B: Click on anything with job data and wait
        const jobElements = document.querySelectorAll(
            '[data-entity-urn*="jobPosting"], ' +
            '.job-card-container, ' +
            'li[data-occludable-job-id], ' +
            'li[class*="job-card"], ' +
            'a[class*="job-card"], ' +
            '[class*="jobs-search-results"] li'
        );
        if (jobElements.length > 0) {
            // Return the element tag info for click strategy
            return 'ELEMENTS:' + jobElements.length + '|TAG:' + jobElements[0].tagName + '|CLS:' + (jobElements[0].className || '').substring(0,80);
        }
        
        // Strategy C: Look for the search results panel and list all links
        const panel = document.querySelector('[class*="search-results"], [class*="jobs-search"], main');
        if (panel) {
            const allA = panel.querySelectorAll('a');
            const jobA = Array.from(allA).filter(a => a.href.includes('/jobs/'));
            if (jobA.length > 0) return jobA.map(a => a.href);
        }
        
        // Strategy D: Dump page structure for debugging
        const allElements = document.querySelectorAll('[class]');
        const classNames = Array.from(allElements).slice(0, 30).map(el => el.className.substring(0,50)).filter(Boolean);
        return 'NONE|CLASSES:' + classNames.join(',');
    }""")

def main():
    from playwright.sync_api import sync_playwright
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log("=" * 50)
    log("  LinkedIn Easy Apply Bot V4 - Hu Chenwei")
    log("  Playwright + Chromium integre")
    log("=" * 50)
    
    cf_username = globals().get("username", "chen771216000@gmail.com")
    cf_password = globals().get("password", "1216413@Huyangfang")
    cf_terms = globals().get("search_terms", ["alternance graphiste", "alternance graphisme", "alternance illustrateur", "alternance branding"])
    cf_location = globals().get("search_location", "Paris, France")
    
    pw_data_dir = str(Path(__file__).parent / "playwright_data")
    os.makedirs(pw_data_dir, exist_ok=True)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=pw_data_dir,
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            # Step 1: Login
            logged_in = do_login(page, cf_username, cf_password)
            if not logged_in:
                log("❌ Impossible de se connecter a LinkedIn")
                return
            
            # Step 2: Search and apply
            total_applied = 0
            max_apps = 3
            
            for term in cf_terms:
                if total_applied >= max_apps:
                    break
                
                log(f"\nRecherche: {term}")
                qs = f"keywords={term.replace(' ', '+')}&location={cf_location.replace(' ', '+').replace(',', '%2C')}&f_AL=true&start=0"
                
                try:
                    page.goto(f"https://www.linkedin.com/jobs/search/?{qs}", wait_until="load", timeout=25000)
                except Exception as e:
                    log(f"  Goto error: {str(e)[:60]}")
                
                time.sleep(4)
                
                # Dismiss cookie popup
                try:
                    dismiss = page.locator("button:has-text('Accepter'), button:has-text('Refuser'), .artdeco-global-alert-action button, [aria-label*=cookie], button:has-text('Autoriser')").first
                    if dismiss.is_visible(timeout=3000):
                        dismiss.click()
                        log("  Cookie dismissed")
                        time.sleep(1)
                except: pass
                
                # Scroll to trigger lazy loading
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
                for _ in range(6):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(0.8)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)
                
                page_title = page.evaluate("document.title")
                log(f"  Page title: {page_title[:80]}")
                
                # Find job links
                links_result = find_job_links(page)
                log(f"  Links result (first 200): {str(links_result)[:200]}")
                
                if isinstance(links_result, list):
                    job_urls = links_result
                elif isinstance(links_result, str):
                    if links_result.startswith('ELEMENTS:'):
                        # Click-based approach for elements
                        parts = links_result.split('|')
                        count = int(parts[0].split(':')[1])
                        tag = parts[1].split(':')[1] if len(parts) > 1 else "?"
                        cls = parts[2].split(':')[1] if len(parts) > 2 else "?"
                        log(f"  {count} elements found (tag={tag}, class={cls})")
                        
                        # Click each element to reveal the detail panel
                        for idx in range(min(count, 5)):
                            if total_applied >= max_apps:
                                break
                            
                            log(f"  Offre {idx+1}...")
                            clicked = page.evaluate(f"""() => {{
                                const els = document.querySelectorAll(
                                    '[data-entity-urn*="jobPosting"], ' +
                                    '.job-card-container, ' +
                                    'li[data-occludable-job-id], ' +
                                    'li[class*="job-card"], ' +
                                    'a[class*="job-card"], ' +
                                    '[class*="jobs-search-results"] li'
                                );
                                if (els[{idx}]) {{ 
                                    els[{idx}].click(); 
                                    return true; 
                                }}
                                return false;
                            }}""")
                            
                            if not clicked:
                                log("    Click failed")
                                continue
                            time.sleep(random.uniform(2, 4))
                            
                            # Look for Easy Apply
                            easy_btn = None
                            for text in ["Candidature simplifiee", "Easy Apply", "Postuler facilement", "Apply"]:
                                try:
                                    btn = page.locator(f"button:has-text('{text}')").first
                                    if btn.is_visible(timeout=2000):
                                        easy_btn = btn
                                        break
                                except: pass
                            
                            if not easy_btn:
                                log("    No Easy Apply")
                                continue
                            
                            log("  ✅ Easy Apply!")
                            easy_btn.click()
                            time.sleep(random.uniform(2, 3))
                            
                            if handle_easy_apply(page):
                                total_applied += 1
                                log(f"  ** Total: {total_applied} **")
                                time.sleep(5)
                        
                        continue  # Skip the link-based loop below
                    
                    elif links_result.startswith('NONE'):
                        log(f"  No job links found. Structure: {links_result[:200]}")
                        try:
                            page.screenshot(path=str(LOG_DIR / f"debug_{term[:15].replace(' ', '_')}.png"))
                        except: pass
                        continue
                    else:
                        job_urls = []
                else:
                    job_urls = []
                
                # Link-based approach
                for i, job_url in enumerate(job_urls[:5]):
                    if total_applied >= max_apps:
                        break
                    
                    log(f"  Offre {i+1}...")
                    try:
                        page.goto(job_url, wait_until="load", timeout=15000)
                        time.sleep(3)
                    except: pass
                    
                    # Find Easy Apply
                    for text in ["Candidature simplifiee", "Easy Apply", "Postuler facilement", "Apply"]:
                        try:
                            btn = page.locator(f"button:has-text('{text}')").first
                            if btn.is_visible(timeout=2000):
                                log(f"  ✅ Easy Apply!")
                                btn.click()
                                time.sleep(random.uniform(2, 3))
                                if handle_easy_apply(page):
                                    total_applied += 1
                                    log(f"  ** Total: {total_applied} **")
                                time.sleep(5)
                                break
                        except: pass
                    else:
                        log("    No Easy Apply")
            
            log(f"\n{'='*50}")
            log(f"  FINI - {total_applied} candidature(s)")
            log(f"{'='*50}")
            
        except Exception as e:
            log(f"FATAL: {str(e)[:300]}")
            import traceback
            log(traceback.format_exc())
        finally:
            time.sleep(3)
            context.close()

if __name__ == "__main__":
    main()
