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
    """Fill Easy Apply form and submit. Uses JS to find buttons."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for step in range(10):
        time.sleep(random.uniform(2, 4))
        
        # Fill text inputs via Playwright
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
        
        # Handle radio/checkboxes
        try:
            for r in page.locator("input[type=radio], input[type=checkbox]").all():
                if r.is_checked(): continue
                lt = (r.evaluate("el => document.querySelector('label[for=\"' + el.id + '\"]')?.textContent || ''") or "").lower()
                if any(w in lt for w in ["oui", "yes", "agree", "accept"]):
                    try: r.check(); log(f"    Check: {lt[:20]}...")
                    except: pass
        except: pass
        
        # Find and click the next/submit button - LinkedIn Easy Apply specific
        result = page.evaluate("""() => {
            // Strategy 1: Primary action button in the modal (blue, prominent)
            const modal = document.querySelector('[class*="artdeco-modal"], [class*="modal"], [class*="easy-apply"]') || document;
            const allBtns = modal.querySelectorAll('button');
            
            // Strategy 1: Primary blue button (artdeco-button--primary)
            const primaryBtns = modal.querySelectorAll('button.artdeco-button--primary');
            for (const btn of primaryBtns) {
                const t = (btn.textContent || '').trim().toLowerCase();
                if (t && !t.includes('fermer') && !t.includes('close') && !t.includes('cancel') && !t.includes('annuler') && !t.includes('x')) {
                    btn.click();
                    return {found: true, text: btn.textContent.trim().substring(0,20)};
                }
            }
            
            // Strategy 2: Match button text in modal
            const nextTerms = ['suivant', 'next', 'continuer', 'continue', 'examiner', 'review', 'envoyer', 'submit', 'postuler', 'apply', 'send', 'done', 'termine', 'terminer'];
            for (const btn of allBtns) {
                if (btn.offsetParent === null) continue;
                const t = (btn.textContent || '').trim().toLowerCase().replace(/[\u00a0]/g, ' ');
                if (!t) continue;
                for (const term of nextTerms) {
                    if (t === term || t.startsWith(term)) {
                        btn.click();
                        return {found: true, text: btn.textContent.trim().substring(0,20)};
                    }
                }
            }
            
            // Strategy 3: Wide/decorative buttons (not tiny icons)
            for (const btn of allBtns) {
                if (btn.offsetParent === null) continue;
                const rect = btn.getBoundingClientRect();
                if (rect.width < 30 || rect.height < 20) continue;  // skip tiny buttons
                const t = (btn.textContent || '').trim().toLowerCase();
                if (!t || t.includes('fermer') || t.includes('close') || t.includes('annuler') || t.includes('save') || t.includes('enregistrer') || t === 'x' || t === '...') continue;
                const cls = (btn.className || '').toLowerCase();
                if (cls.includes('primary') || cls.includes('submit')) {
                    btn.click();
                    return {found: true, text: btn.textContent.trim().substring(0,20)};
                }
            }
            
            // Strategy 4: Last NON-close/non-save visible button
            const candidates = Array.from(allBtns).filter(b => {
                if (b.offsetParent === null) return false;
                const t = (b.textContent || '').trim().toLowerCase();
                if (!t) return false;
                const skip = ['fermer', 'close', 'cancel', 'annuler', 'save', 'enregistrer', 'x', '...'];
                return !skip.some(s => t === s || t.startsWith(s));
            });
            if (candidates.length > 0) {
                const last = candidates[candidates.length-1];
                // Only click if it's a meaningful button (not a close X)
                const rect = last.getBoundingClientRect();
                if (rect.width > 40) {
                    last.click();
                    return {found: true, text: 'btn:' + (last.textContent || '').trim().substring(0,15)};
                }
            }
            return {found: false, text: ''};
        }""")
        
        if result.get('found'):
            log(f"    Bouton: {result.get('text', '?')[:20]}")
            time.sleep(random.uniform(2, 3))
            
            # Check if submitted
            body = page.evaluate("document.body.innerText") or ""
            if "Candidature envoy" in body or "Application sent" in body or "Candidature envoyée" in body:
                log("  CANDIDATURE ENVOYEE!")
                try:
                    d = page.locator("button[aria-label=Dismiss], button:has-text('Done'), button:has-text('Termine'), button:has-text('Terminer')").first
                    if d.is_visible(timeout=1000): d.click(); time.sleep(1)
                except: pass
                return True
        else:
            log(f"    Plus de bouton (step {step+1})")
            # Take screenshot for debugging
            try: page.screenshot(path=str(LOG_DIR / f"debug_nobtn_{step}.png"))
            except: pass
            break
    return False

def click_easy_apply(page):
    """Find and click Easy Apply button. Search whole page but smart filter."""
    result = page.evaluate("""() => {
        // Search ALL buttons on the page
        const allBtns = document.querySelectorAll('button');
        
        // Terms to identify Easy Apply
        const applyTerms = ["easy apply", "candidature simplifiée", "candidature simplifiee",
                            "postuler facilement", "apply", "candidature"];
        const skipTerms = ["enregistrer", "save", "message", "follow", "suivre", 
                          "plus", "...", "signaler", "signal", "pour les entrep"];
        
        // Strategy 1: Exact match on any button (class or text contains Easy Apply)
        for (const btn of allBtns) {
            const t = (btn.textContent || '').trim().toLowerCase();
            const cl = (btn.className || '').toLowerCase();
            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
            const combined = t + ' ' + cl + ' ' + aria;
            
            // Skip known non-apply buttons
            if (skipTerms.some(s => t.includes(s) || t === s)) continue;
            
            // Check if it mentions applying
            if (cl.includes('easy-apply') || cl.includes('jobs-apply') ||
                aria.includes('apply') || aria.includes('candidature') ||
                applyTerms.some(term => t.includes(term))) {
                btn.click();
                return {found: true, text: btn.textContent.trim().substring(0,30)};
            }
        }
        
        // Strategy 2: Primary blue buttons - check all, skip non-apply
        for (const btn of allBtns) {
            const t = (btn.textContent || '').trim().toLowerCase();
            const cl = (btn.className || '').toLowerCase();
            
            if (skipTerms.some(s => t.includes(s) || t === s)) continue;
            const rect = btn.getBoundingClientRect();
            
            // A primary button that's wide enough and has apply-related text
            if (cl.includes('primary') && rect.width > 60) {
                if (t.includes('postul') || t.includes('candid') || t.includes('apply') || 
                    t.includes('facile') || !t) {
                    btn.click();
                    return {found: true, text: btn.textContent.trim().substring(0,30)};
                }
            }
        }
        
        // Strategy 3: Take a screenshot so we can see what's on the page
        return {found: false, text: 'none', btns: allBtns.length, 
                btnTexts: Array.from(allBtns).slice(0,10).map(b => 
                    (b.textContent || '').trim().substring(0,25) + '|cls:' + (b.className || '').substring(0,30)
                ).join(' || ')};
    }""")
    if not result.get('found', False):
        log(f"  Debug - buttons found: {result.get('btnTexts', '?')[:200]}")
    return result.get('found', False)

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
            log("  3. Si LinkedIn demande un code PIN, verifie tes mails et tape-le")
            log("  4. Reviens ici et appuie sur ENTREE")
            log("  5. Le bot postule aux offres Easy Apply")
            log("")
            log("=" * 50)
            log("")
            
            page.goto("https://www.linkedin.com/login", wait_until="load", timeout=20000)
            time.sleep(2)
            
            input(">>> Appuie sur ENTREE une fois connecte a LinkedIn... ")
            
            # Wait for any challenge/redirect
            log("Verification de la connexion...")
            time.sleep(3)
            wait_start = time.time()
            max_wait = 300
            
            while time.time() - wait_start < max_wait:
                try:
                    current_url = page.url.lower()
                    if "feed" in current_url:
                        log("Connecte!")
                        break
                    if "checkpoint" in current_url or "challenge" in current_url or "pin" in current_url:
                        log("  LinkedIn demande une verification (code PIN/email)...")
                        log("  Complete la verification dans la fenetre Chromium")
                    elif "login" in current_url:
                        log("  Toujours pas connecte... connecte-toi dans la fenetre Chromium")
                    else:
                        log(f"  Page en cours: {current_url[:60]}")
                    time.sleep(5)
                    elapsed = int(time.time() - wait_start)
                    if elapsed > 0 and elapsed % 30 == 0:
                        log(f"  Attente... ({elapsed}s)")
                except Exception as e:
                    log(f"  Check error: {str(e)[:50]}")
                    time.sleep(5)
            else:
                log("TIMEOUT - pas connecte apres 5 min")
                return
            
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
                log(f"  Jobs: {str(links_result)[:150]}")
                
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
                        
                        # Find Easy Apply button (comprehensive search)
                        found = click_easy_apply(page)
                        if found:
                            log(f"  Easy Apply!")
                            time.sleep(random.uniform(2, 3))
                            if handle_easy_apply(page):
                                total_applied += 1
                                log(f"  Total: {total_applied}")
                            time.sleep(5)
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
                    
                    found = click_easy_apply(page)
                    if found:
                        log(f"  Easy Apply!")
                        time.sleep(random.uniform(2, 3))
                        if handle_easy_apply(page):
                            total_applied += 1
                            log(f"  Total: {total_applied}")
                        time.sleep(5)
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
