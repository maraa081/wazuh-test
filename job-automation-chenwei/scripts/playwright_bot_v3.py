"""
Playwright LinkedIn Easy Apply Bot V3 - Hu Chenwei
CONNECTION VIA CDP : Pilote le Chrome Windows deja connecte a LinkedIn
Plus besoin de login ! Le bot se branche sur la session existante.
"""
import os, sys, time, json, random
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, str(Path(__file__).parent.parent / "candidate_bot" / "config"))
try:
    from personals import *
    from secrets import *
    from search import *
    from questions import *
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent / "config"))
    from personals import *
    from secrets import *
    from search import *
    from questions import *

LOG_DIR = Path(__file__).parent / "logs"
DATA_DIR = Path(__file__).parent / "data"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    clean = msg.encode("ascii", "replace").decode()
    line = f"[{ts}] {clean}"
    try: print(line, flush=True)
    except: pass
    try:
        (LOG_DIR / "playwright_bot.log").open("a", encoding="utf-8").write(f"[{ts}] {msg}\n")
    except:
        pass

def answer_question(question_text):
    q = question_text.lower()
    if any(w in q for w in ["portfolio", "site", "lien web"]): return portfolio_url
    if "linkedin" in q: return linkedin_url
    if any(w in q for w in ["telephone", "phone", "mobile"]): return phone_number
    if any(w in q for w in ["email", "e-mail", "courriel"]): return "via0000413@gmail.com"
    if any(w in q for w in ["motivation", "lettre", "pourquoi"]): return motivation_letter[:300]
    if any(w in q for w in ["salaire", "pretention"]): return "A discuter selon la grille de l'ecole"
    if any(w in q for w in ["disponible", "disponibilite", "commencer"]): return "A partir de septembre 2026"
    if any(w in q for w in ["experience", "parcours", "formation"]): return "Formation Beaux-Arts Shanghai, Nantes, Besancon. Projets: identite visuelle Yuffee, exposition Shanghai, collaboration Artgogo x Brother China"
    if any(w in q for w in ["logiciel", "adobe", "competence"]): return "Photoshop, Illustrator, InDesign, Procreate, ZBrush, Figma"
    if any(w in q for w in ["langue"]): return "Chinois (maternel), Francais (B2), Anglais (intermediaire)"
    if any(w in q for w in ["visa", "sponsor", "autorisation"]): return "Non - Titre de sejour valide autorisant le travail"
    if any(w in q for w in ["rythme", "alternance"]): return "3j entreprise / 2j ecole"
    if any(w in q for w in ["annee", "years", "experience"]): return "2"
    if any(w in q for w in ["souhaitez", "poste", "role"]): return "Graphiste / Illustratrice en alternance"
    return None

def handle_easy_apply(page):
    """Handle the Easy Apply multi-step modal"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    for step in range(10):
        time.sleep(random.uniform(1.5, 3))
        
        # 1. Fill text inputs and textareas
        try:
            inputs = page.locator("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea")
            count = inputs.count()
            for i in range(count):
                inp = inputs.nth(i)
                if inp.get_attribute("value"):
                    continue
                ph = (inp.get_attribute("placeholder") or "").strip()
                aria = (inp.get_attribute("aria-label") or "").strip()
                name = (inp.get_attribute("name") or "").strip()
                txt = f"{ph} {aria} {name}"
                
                answer = answer_question(txt)
                if answer:
                    try:
                        inp.fill(answer)
                        log(f"    Rempli: {txt[:30]}...")
                    except:
                        try:
                            inp.type(answer, delay=random.randint(30, 80))
                            log(f"    Type: {txt[:30]}...")
                        except:
                            pass
        except Exception as e:
            log(f"    Input fill issue: {str(e)[:60]}")
        
        # 2. Handle radio/checkbox
        try:
            radios = page.locator("input[type=radio], input[type=checkbox]")
            rc = radios.count()
            for i in range(rc):
                r = radios.nth(i)
                if r.is_checked(): continue
                label_text = r.evaluate("""el => {
                    const lbl = document.querySelector('label[for="' + el.id + '"]');
                    return lbl ? lbl.textContent : (el.parentElement ? el.parentElement.textContent : '');
                }""") or ""
                lt = label_text.lower()
                if any(w in lt for w in ["oui", "yes", "agree", "accept", "certify"]):
                    try:
                        r.check()
                        log(f"    Check: {lt[:30]}...")
                    except:
                        pass
        except:
            pass
        
        # 3. Find and click submit/next/review button
        try:
            submit_selectors = [
                "button:has-text('Suivant')",
                "button:has-text('Next')",
                "button:has-text('Submit')",
                "button:has-text('Examiner')",
                "button:has-text('Review')",
                "button:has-text('Envoyer')",
                "button:has-text('Postuler')",
                "button:has-text('Apply')",
                "button[aria-label*='Submit']",
                "button[aria-label*='Next']",
                "button[aria-label*='Review']",
                "button[aria-label*='Suivant']",
            ]
            clicked = False
            for sel in submit_selectors:
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn_text = btn.text_content() or ""
                    btn.click()
                    log(f"    Bouton: {btn_text[:30]}")
                    clicked = True
                    time.sleep(random.uniform(2, 4))
                    break
            
            if not clicked:
                log(f"    Plus de bouton (step {step+1})")
                break
        except:
            log(f"    Bouton non trouve (step {step+1})")
            break
        
        # 4. Check success
        try:
            body = page.evaluate("document.body.innerText") or ""
            if "Candidature envoy" in body or "Application sent" in body:
                log(f"  ✅ CANDIDATURE ENVOYEE!")
                # Dismiss success modal
                try:
                    dismiss = page.locator("button[aria-label=Dismiss], button:has-text('Done'), button:has-text('Termine')").first
                    if dismiss.is_visible():
                        dismiss.click()
                        time.sleep(1)
                except:
                    pass
                return True
        except:
            pass
    
    return False

def main(search_terms_list, location, max_apps=1):
    from playwright.sync_api import sync_playwright
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log("=" * 50)
    log("  LinkedIn Easy Apply Bot V3 - CDP Mode")
    log(f"  {len(search_terms_list)} termes | {location}")
    log("=" * 50)
    
    with sync_playwright() as p:
        # Connect to existing Chrome via CDP
        log("Connecting to Chrome via CDP at localhost:9222...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        
        # Get the default context and page
        default_context = browser.contexts[0]
        
        # Open a new tab to avoid interfering with user
        page = default_context.new_page()
        
        try:
            # Check if we're logged into LinkedIn
            log("Checking LinkedIn auth state...")
            page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=15000)
            time.sleep(2)
            
            current_url = page.url.lower()
            log(f"URL after feed: {current_url[:80]}")
            
            if "login" in current_url or "checkpoint" in current_url:
                log("⚠️ NOT LOGGED IN - Chrome n'est pas connecte a LinkedIn!")
                log("Ouvre linkedin.com dans Chrome et connecte-toi manuellement.")
                log("Le bot attend que tu sois connecte...")
                
                # Wait for user to login (up to 5 minutes)
                for i in range(60):
                    try:
                        page.goto("https://www.linkedin.com/feed/", wait_until="load", timeout=10000)
                        time.sleep(2)
                        if "feed" in page.url.lower():
                            log("✅ Connecte!")
                            break
                    except:
                        pass
                    time.sleep(5)
                else:
                    log("❌ TIMEOUT: Connexion LinkedIn NON effectuee")
                    return False
            
            # Now search and apply
            total_applied = 0
            
            for term in search_terms_list:
                if total_applied >= max_apps:
                    break
                
                log(f"\nSearching: {term}")
                
                # Navigate to search
                params_str = f"keywords={term.replace(' ', '+')}&location={location.replace(' ', '+').replace(',', '%2C')}&f_AL=true&start=0"
                url = f"https://www.linkedin.com/jobs/search/?{params_str}"
                
                try:
                    page.goto(url, wait_until="load", timeout=20000)
                except:
                    pass
                time.sleep(random.uniform(2, 4))
                
                # Try to get job cards - use flexible selectors
                job_applied_for_term = 0
                
                for attempt in range(3):  # Try scrolling to load more
                    try:
                        cards = page.locator("[data-entity-urn*=jobPosting], .job-card-container, [class*=job-card]").all()
                        log(f"  {len(cards)} offres trouvees (tentative {attempt+1})")
                        
                        if cards:
                            break
                    except:
                        pass
                    
                    if attempt < 2:
                        page.evaluate("window.scrollBy(0, 500)")
                        time.sleep(2)
                
                # Try to apply to each job
                for i, card in enumerate(cards):
                    if total_applied >= max_apps or job_applied_for_term >= 2:
                        break
                    
                    try:
                        log(f"  Job {i+1}: tentative...")
                        
                        # Click card via multiple methods
                        try:
                            card.click()
                        except:
                            try:
                                card.locator("a").first.click()
                            except:
                                page.evaluate(f"document.querySelectorAll('[data-entity-urn*=jobPosting], .job-card-container, [class*=job-card]')[{i}].click()")
                        
                        time.sleep(random.uniform(2, 4))
                        
                        # Look for Easy Apply button - flexible text matching
                        easy_btn = None
                        for btn_text in ["Candidature simplifiee", "Easy Apply", "Postuler facilement"]:
                            try:
                                btn = page.locator(f"button:has-text('{btn_text}')").first
                                if btn.is_visible(timeout=3000):
                                    easy_btn = btn
                                    break
                            except:
                                pass
                        
                        if not easy_btn:
                            # Try more generic match
                            try:
                                btns = page.locator("button").all()
                                for btn in btns:
                                    txt = btn.text_content() or ""
                                    if ("postuler" in txt.lower() or "apply" in txt.lower()) and "easy" in txt.lower():
                                        easy_btn = btn
                                        break
                            except:
                                pass
                        
                        if not easy_btn:
                            log(f"    Pas de Easy Apply")
                            continue
                        
                        log(f"  ✅ Easy Apply trouve!")
                        
                        # Click Easy Apply
                        try:
                            easy_btn.click()
                        except:
                            page.evaluate("""() => {
                                const btns = document.querySelectorAll('button');
                                for (const b of btns) {
                                    const t = b.textContent || '';
                                    if ((t.includes('Easy') || t.includes('simplifie')) && (t.includes('Apply') || t.includes('Candidature')) || t.includes('Postuler')) {
                                        b.click(); return;
                                    }
                                }
                            }""")
                        
                        time.sleep(random.uniform(2, 3))
                        
                        # Handle the form
                        success = handle_easy_apply(page)
                        if success:
                            total_applied += 1
                            job_applied_for_term += 1
                            log(f"  ** Total: {total_applied}/{max_apps} **")
                            
                            # Random delay between applications
                            delay = random.uniform(5, 10)
                            log(f"  Pause {delay:.0f}s...")
                            time.sleep(delay)
                        
                    except Exception as e:
                        log(f"    Error: {str(e)[:80]}")
                        continue
                
                log(f"  Term '{term}': {job_applied_for_term} candidatures")
            
            log(f"\n{'='*50}")
            log(f"  FINI - {total_applied} candidature(s) envoyee(s)")
            log(f"{'='*50}")
            
            # Save state
            try:
                page.screenshot(path=str(LOG_DIR / "final_state.png"))
            except:
                pass
            
            return total_applied > 0
            
        except Exception as e:
            log(f"ERROR: {str(e)[:200]}")
            try:
                page.screenshot(path=str(LOG_DIR / f"error_{int(time.time())}.png"))
            except:
                pass
            return False
        finally:
            try:
                page.close()
            except:
                pass
            # Don't close browser - it's the user's Chrome

if __name__ == "__main__":
    # Use search config if available
    try:
        terms = search_terms
        loc = search_location
    except:
        terms = ["alternance graphiste", "alternance graphisme", "alternance illustrateur"]
        loc = "Paris, France"
    
    # CRASH TEST: 1 candidature
    main(terms, loc, max_apps=1)
