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
    
    # Use Playwright's type() instead of JS fill for React compatibility
    # LinkedIn now uses randomized IDs for all form inputs
    try:
        email_input = page.locator("input[type='email'][autocomplete='username']")
        email_input.first.wait_for(timeout=5000)
        email_input.first.fill('')
        email_input.first.type(username, delay=50)
        log("  Email filled via Playwright type()")
    except Exception as e:
        log(f"  Email fill failed: {str(e)[:60]}")
        # Try JS fallback with the correct selector
        filled = page.evaluate("""({u, p}) => {
            const emailInput = document.querySelector("input[type='email'][autocomplete='username']");
            const passInput = document.querySelector("input[type='password'][autocomplete='current-password']");
            if (emailInput) {
                emailInput.focus(); emailInput.value = ''; emailInput.value = u;
                emailInput.dispatchEvent(new Event('input', {bubbles: true}));
                emailInput.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (passInput) {
                passInput.focus(); passInput.value = ''; passInput.value = p;
                passInput.dispatchEvent(new Event('input', {bubbles: true}));
                passInput.dispatchEvent(new Event('change', {bubbles: true}));
            }
            return {email: !!emailInput, pass: !!passInput};
        }""", {"u": username, "p": password})
        log(f"  JS fill (fallback): email={filled.get('email')}, pass={filled.get('pass')}")
    
    time.sleep(1)
    
    try:
        pass_input = page.locator("input[type='password'][autocomplete='current-password']")
        pass_input.first.wait_for(timeout=5000)
        pass_input.first.fill('')
        pass_input.first.type(password, delay=50)
        log("  Password filled via Playwright type()")
    except Exception as e:
        log(f"  Password fill failed: {str(e)[:60]}")
    
    time.sleep(1)
    
    # Click Sign in (S'identifier) button - no [type=submit] on LinkedIn!
    btn_clicked = page.evaluate("""() => {
        const allBtns = document.querySelectorAll('button');
        for (const btn of allBtns) {
            const t = (btn.textContent || '').trim().toLowerCase();
            if (t === "s'identifier" || t.includes("sign in") || t.includes("sign-in")) {
                btn.click();
                return 'found-sign-in';
            }
        }
        // Fallback: last button in the form area
        const formArea = document.querySelector('.login__form_action_container') ||
                         document.querySelector('[class*=login]');
        if (formArea) {
            const btns = formArea.querySelectorAll('button');
            if (btns.length > 0) { btns[btns.length-1].click(); return 'form-area-button'; }
        }
        return 'no-button-found';
    }""")
    log(f"Submit: {btn_clicked}")
    
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
        // LinkedIn CURRENT structure (verified July 2026):
        // Container: div.job-search-card (child of ul.jobs-search__results-list)
        // Title: h3.base-search-card__title
        // Link: a.base-card__full-link
        // Company: h4.base-search-card__subtitle
        //
        // Strategy 1: Direct job view links from the results list
        const resultList = document.querySelector('ul.jobs-search__results-list');
        if (resultList) {
            const links = resultList.querySelectorAll('a.base-card__full-link, a[href*="/jobs/view/"]');
            if (links.length > 0) return Array.from(links).map(a => a.href);
            // Try getting parent card clickable area
            const cards = resultList.querySelectorAll('div.job-search-card, div.base-search-card');
            if (cards.length > 0) return 'ELEMENTS:' + cards.length + '|TAG:DIV|CLS:job-search-card'; 
        }
        
        // Strategy 2: Any link with /jobs/view/
        let links = Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'));
        if (links.length > 0) return links.map(a => a.href);
        
        // Strategy 3: Fallback selectors
        const jobElements = document.querySelectorAll(
            'div.job-search-card, ' +
            'div.base-search-card, ' +
            'a.base-card__full-link, ' +
            '[data-entity-urn*="jobPosting"], ' +
            '.job-card-container, ' +
            'li[data-occludable-job-id]'
        );
        if (jobElements.length > 0) {
            return 'ELEMENTS:' + jobElements.length + '|TAG:' + jobElements[0].tagName + '|CLS:' + (jobElements[0].className || '').substring(0,80);
        }
        
        // Strategy 4: Look for search results panel
        const panel = document.querySelector('main, [class*="search-results"], [class*="jobs-search"]');
        if (panel) {
            const allA = panel.querySelectorAll('a');
            const jobA = Array.from(allA).filter(a => a.href.includes('/jobs/'));
            if (jobA.length > 0) return jobA.map(a => a.href);
        }
        
        return 'NONE';
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
                
                # Dismiss cookie/privacy popup
                try:
                    dismiss = page.evaluate("""() => {
                        const allBtns = document.querySelectorAll('button');
                        for (const btn of allBtns) {
                            const t = (btn.textContent || '').trim().toLowerCase();
                            if (t.includes('accepter') || t.includes('accept') || t.includes('refuser') || t.includes('decline') || t.includes('reject') || t.includes('allow') || t.includes('autoriser')) {
                                btn.click();
                                return 'dismissed';
                            }
                        }
                        return 'not-found';
                    }""")
                    if dismiss == 'dismissed':
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
                            clicked = page.evaluate(f"""(idx) => {{
                                // Try multiple selectors for clicking job cards
                                let els = document.querySelectorAll('ul.jobs-search__results-list div.job-search-card, ul.jobs-search__results-list div.base-search-card');
                                if (els.length === 0) {{
                                    els = document.querySelectorAll('div.job-search-card, div.base-search-card, a.base-card__full-link, [data-entity-urn*="jobPosting"], .job-card-container, li[data-occludable-job-id]');
                                }}
                                if (els[idx]) {{
                                    if (els[idx].tagName === 'A') {{ els[idx].click(); }}
                                    else {{ 
                                        const link = els[idx].querySelector('a.base-card__full-link, a[href*="/jobs/view/"]');
                                        if (link) link.click();
                                        else els[idx].click();
                                    }}
                                    return true;
                                }}
                                return false;
                            }}""", idx)
                            
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
