"""
Playwright LinkedIn Easy Apply Bot V4 - Hu Chenwei
MODE MANUEL: ouvre Chromium, tu te connectes, il postule
"""
import os, sys, time, json, random
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

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
        try:
            for inp in page.locator("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea").all():
                if inp.get_attribute("value"): continue
                ph = (inp.get_attribute("placeholder") or "").strip()
                aria = (inp.get_attribute("aria-label") or "").strip()
                name = (inp.get_attribute("name") or "").strip()
                txt = f"{ph} {aria} {name}"
                answer = answer_question(txt)
                if answer:
                    try: inp.fill(answer); log(f"    Rempli: {txt[:20]}..."); time.sleep(0.3)
                    except: pass
        except: pass
        try:
            for r in page.locator("input[type=radio], input[type=checkbox]").all():
                if r.is_checked(): continue
                lt = (r.evaluate("el => document.querySelector('label[for=\"' + el.id + '\"]')?.textContent || ''") or "").lower()
                if any(w in lt for w in ["oui", "yes", "agree", "accept"]):
                    try: r.check(); log(f"    Check: {lt[:20]}...")
                    except: pass
        except: pass
        try:
            btn = page.locator("button[type=submit], button:has-text('Suivant'), button:has-text('Next'), button:has-text('Submit'), button:has-text('Examiner'), button:has-text('Review'), button:has-text('Envoyer'), button:has-text('Postuler'), button:has-text('Apply')").first
            if btn.is_visible(timeout=2000):
                t = btn.text_content() or ""
                btn.click()
                log(f"    Bouton: {t[:20]}")
                time.sleep(random.uniform(2, 3))
                body = page.evaluate("document.body.innerText") or ""
                if "Candidature envoy" in body or "Application sent" in body:
                    log("  CANDIDATURE ENVOYEE!")
                    try:
                        d = page.locator("button[aria-label=Dismiss], button:has-text('Done'), button:has-text('Termine')").first
                        if d.is_visible(timeout=1000): d.click(); time.sleep(1)
                    except: pass
                    return True
            else:
                log(f"    Plus de bouton (step {step+1})")
                break
        except:
            log(f"    Bouton pas trouve (step {step+1})")
            break
    return False

def find_job_links(page):
    return page.evaluate("""() => {
        const resultList = document.querySelector('ul.jobs-search__results-list');
        if (resultList) {
            const links = resultList.querySelectorAll('a.base-card__full-link, a[href*="/jobs/view/"]');
            if (links.length > 0) return Array.from(links).map(a => a.href);
            const cards = resultList.querySelectorAll('div.job-search-card, div.base-search-card');
            if (cards.length > 0) return 'ELEMENTS:' + cards.length + '|TAG:DIV|CLS:job-search-card';
        }
        let links = Array.from(document.querySelectorAll('a[href*="/jobs/view/"]'));
        if (links.length > 0) return links.map(a => a.href);
        const allCards = document.querySelectorAll(
            'div.job-search-card, div.base-search-card, a.base-card__full-link, ' +
            '[data-entity-urn*="jobPosting"], .job-card-container, li[data-occludable-job-id]'
        );
        if (allCards.length > 0) return 'ELEMENTS:' + allCards.length + '|TAG:' + allCards[0].tagName + '|CLS:' + (allCards[0].className || '').substring(0,80);
        const panel = document.querySelector('main, [class*="search-results"], [class*="jobs-search"]');
        if (panel) {
            const jobA = Array.from(panel.querySelectorAll('a')).filter(a => a.href.includes('/jobs/'));
            if (jobA.length > 0) return jobA.map(a => a.href);
        }
        return 'NONE';
    }""")

def main():
    from playwright.sync_api import sync_playwright
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
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
            log("=" * 50)
            log("  LinkedIn Easy Apply Bot V4 - Hu Chenwei")
            log("=" * 50)
            log("")
            log("  **** MODE MANUEL ****")
            log("")
            log("  1. Chromium s'ouvre sur la page LinkedIn")
            log("  2. CONNECTE-TOI manuellement dans la fenetre")
            log("  3. Reviens ici et appuie sur ENTREE")
            log("  4. Le bot postule aux offres Easy Apply")
            log("")
            log("=" * 50)
            log("")
            
            page.goto("https://www.linkedin.com/login", wait_until="load", timeout=20000)
            time.sleep(2)
            
            input(">>> Appuie sur ENTREE une fois connecte a LinkedIn... ")
            
            # Verify connection
            page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=15000)
            time.sleep(2)
            if "login" in page.url.lower():
                log("Pas encore connecte, j'attends 5 min...")
                for i in range(60):
                    try:
                        page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=10000)
                        time.sleep(2)
                        if "feed" in page.url.lower():
                            log("Connecte!")
                            break
                    except: pass
                    log(f"  En attente... ({i*7}s)")
                    time.sleep(5)
                else:
                    log("TIMEOUT - pas connecte")
                    return
            else:
                log("Connecte!")
            
            # Search and apply
            total_applied = 0
            max_apps = 3
            
            for term in cf_terms:
                if total_applied >= max_apps:
                    break
                
                log(f"\nRecherche: {term}")
                qs = f"keywords={term.replace(' ', '+')}&location={cf_location.replace(' ', '+').replace(',', '%2C')}&f_AL=true&start=0"
                
                try:
                    page.goto(f"https://www.linkedin.com/jobs/search/?{qs}", wait_until="load", timeout=25000)
                except:
                    pass
                
                time.sleep(4)
                
                # Scroll for lazy load
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
                for _ in range(6):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(0.8)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)
                
                ptitle = page.evaluate("document.title")
                log(f"  Page: {ptitle[:60]}")
                
                links_result = find_job_links(page)
                log(f"  Jobs found: {str(links_result)[:150]}")
                
                if isinstance(links_result, list):
                    urls = links_result
                elif isinstance(links_result, str) and links_result.startswith('ELEMENTS:'):
                    parts = links_result.split('|')
                    count = int(parts[0].split(':')[1])
                    log(f"  {count} cards to click")
                    
                    for idx in range(min(count, 5)):
                        if total_applied >= max_apps:
                            break
                        
                        log(f"  Offre {idx+1}...")
                        clicked = page.evaluate(f"""(idx) => {{
                            let els = document.querySelectorAll('ul.jobs-search__results-list div.job-search-card, ul.jobs-search__results-list div.base-search-card');
                            if (els.length === 0) {{
                                els = document.querySelectorAll('div.job-search-card, div.base-search-card, a.base-card__full-link, [data-entity-urn*=\"jobPosting\"], .job-card-container, li[data-occludable-job-id]');
                            }}
                            if (els[idx]) {{
                                if (els[idx].tagName === 'A') {{ els[idx].click(); }}
                                else {{ 
                                    const link = els[idx].querySelector('a.base-card__full-link, a[href*=\"/jobs/view/\"]');
                                    if (link) link.click();
                                    else els[idx].click();
                                }}
                                return true;
                            }}
                            return false;
                        }}""", idx)
                        
                        if not clicked:
                            log("    Cannot click")
                            continue
                        time.sleep(random.uniform(2, 4))
                        
                        for text in ["Candidature simplifiee", "Easy Apply", "Postuler facilement", "Apply"]:
                            try:
                                btn = page.locator(f"button:has-text('{text}')").first
                                if btn.is_visible(timeout=2000):
                                    log(f"  Easy Apply!")
                                    btn.click()
                                    time.sleep(random.uniform(2, 3))
                                    if handle_easy_apply(page):
                                        total_applied += 1
                                        log(f"  Total: {total_applied}")
                                    time.sleep(5)
                                    break
                            except: pass
                        else:
                            log("    No Easy Apply")
                    
                    continue
                else:
                    urls = []
                
                for i, job_url in enumerate(urls[:5]):
                    if total_applied >= max_apps:
                        break
                    log(f"  Offre {i+1}...")
                    try:
                        page.goto(job_url, wait_until="load", timeout=15000)
                        time.sleep(3)
                    except: pass
                    for text in ["Candidature simplifiee", "Easy Apply", "Postuler facilement", "Apply"]:
                        try:
                            btn = page.locator(f"button:has-text('{text}')").first
                            if btn.is_visible(timeout=2000):
                                log(f"  Easy Apply!")
                                btn.click()
                                time.sleep(random.uniform(2, 3))
                                if handle_easy_apply(page):
                                    total_applied += 1
                                    log(f"  Total: {total_applied}")
                                time.sleep(5)
                                break
                        except: pass
                    else:
                        log("    No Easy Apply")
            
            log(f"\nFini - {total_applied} candidature(s)")
            
        except Exception as e:
            log(f"FATAL: {str(e)[:300]}")
            import traceback
            log(traceback.format_exc())
        finally:
            time.sleep(3)
            context.close()

if __name__ == "__main__":
    main()
