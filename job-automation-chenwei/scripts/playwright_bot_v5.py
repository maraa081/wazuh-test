"""
Playwright LinkedIn Easy Apply Bot V5 - Hu Chenwei
ROBUSTE: tout le form handling en JavaScript, pas de Playwright locators
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
        pass

# V5: All form answers in one JS dict (transferred at runtime)
_ANSWERS_JS = """
const ANSWERS = {
    phone: "+33678352974",
    email: "via0000413@gmail.com",
    portfolio: "https://github.com/maraa081/wazuh-test/tree/main/test",
    linkedin: "https://www.linkedin.com/in/chenwei-h-9223b3422/",
    motivation: "Artiste et designer visuelle formee aux Beaux-Arts de Shanghai, Nantes et Besancon. Je recherche une alternance en design graphique, illustration ou branding.",
    salary: "A discuter selon la grille de l'ecole",
    availability: "A partir de septembre 2026",
    experience: "Formation Beaux-Arts Shanghai, Nantes, Besancon. Projets identite visuelle Yuffee, exposition Shanghai, collaboration Artgogo x Brother China",
    skills: "Photoshop, Illustrator, InDesign, Procreate, ZBrush, Figma",
    languages: "Chinois (maternel), Francais (B2), Anglais (intermediaire)",
    visa: "Non - Titre de sejour valide",
    rhythm: "3j entreprise / 2j ecole",
    years: "2",
    role: "Graphiste / Illustratrice en alternance",
};
"""

def click_easy_apply(page):
    return page.evaluate("""() => {
        const eab = document.querySelector('button.jobs-apply-button');
        if (eab && eab.offsetParent !== null) { eab.click(); return true; }
        const allBtns = document.querySelectorAll('button');
        for (const b of allBtns) {
            const t = (b.textContent || '').trim().toLowerCase();
            if (t.includes('candidature simplifi') || t.includes('easy apply') || t.includes('postuler facilement')) {
                if (b.offsetParent !== null) { b.click(); return true; }
            }
        }
        return false;
    }""")

def handle_easy_apply_v5(page):
    """
    V5: Full JS-based form handler.
    1. JS iterates ALL form fields (input, select, textarea)
    2. Identifies phone by position after country code
    3. Fills all fields with smart matching
    4. Finds and clicks next/submit buttons
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for step in range(15):
        time.sleep(random.uniform(2, 3))
        
        result = page.evaluate(f"""(step) => {{
            {_ANSWERS_JS}
            
            // STEP A: Fill all form fields AND detect file inputs
            const allFields = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea, select, input[type=file]');
            let lastWasCountry = false;
            let filled = [];
            let hasFileInput = false;
            
            for (const field of allFields) {{
                // Handle file upload detection (CV/resume)
                if (field.type === 'file') {{
                    hasFileInput = true;
                    filled.push({{field: 'FILE-input:' + field.id, type: 'file', value: 'NEED_UPLOAD'}});
                    continue;
                }}
                // Already filled
                if (field.value && field.value.trim()) {{
                    // Check if this is a country code (France +33) -> next empty = phone
                    lastWasCountry = field.value.includes('+33');
                    continue;
                }}
                
                // Detect phone: right after country code, or type=tel, or name contains phone
                const tag = field.tagName.toLowerCase();
                const type = (field.getAttribute('type') || '').toLowerCase();
                const ph = (field.getAttribute('placeholder') || '').toLowerCase();
                const aria = (field.getAttribute('aria-label') || '').toLowerCase();
                const name = (field.getAttribute('name') || '').toLowerCase();
                const cl = (field.className || '').toLowerCase();
                const combined = ph + ' ' + aria + ' ' + name + ' ' + type + ' ' + cl;
                
                // DON'T fill search fields
                if (combined.includes('chercher') || combined.includes('search') || combined.includes('recherch')) {{
                    lastWasCountry = false;
                    continue;
                }}
                
                // Already has a relevant value
                if (field.value && field.value.trim()) continue;
                
                let answer = null;
                
                // 1. Phone detection (identified by position or type)
                if (lastWasCountry || type === 'tel' || name.includes('phone') || name.includes('mobile')) {{
                    answer = ANSWERS.phone;
                }}
                // 2. Text matching against answers
                else if (combined.includes('telephone') || combined.includes('phone') || combined.includes('mobile') || combined.includes('portable') || combined.includes('numero') || combined.includes('fixe') || combined.includes('+33') || combined.includes('06') || combined.includes('07')) {{
                    answer = ANSWERS.phone;
                }}
                else if (combined.includes('portfolio') || combined.includes('site') || combined.includes('lien web') || combined.includes('url')) {{
                    answer = ANSWERS.portfolio;
                }}
                else if (combined.includes('linkedin')) {{
                    answer = ANSWERS.linkedin;
                }}
                else if (combined.includes('email') || combined.includes('courriel') || combined.includes('mail') || combined.includes('e-mail')) {{
                    answer = ANSWERS.email;
                }}
                else if (combined.includes('motivation') || combined.includes('lettre') || combined.includes('pourquoi')) {{
                    answer = ANSWERS.motivation;
                }}
                else if (combined.includes('salaire') || combined.includes('pretention') || combined.includes('remuneration')) {{
                    answer = ANSWERS.salary;
                }}
                else if (combined.includes('disponible') || combined.includes('commencer') || combined.includes('debut')) {{
                    answer = ANSWERS.availability;
                }}
                else if (combined.includes('experience') || combined.includes('parcours') || combined.includes('formation')) {{
                    answer = ANSWERS.experience;
                }}
                else if (combined.includes('logiciel') || combined.includes('adobe') || combined.includes('competence') || combined.includes('outil')) {{
                    answer = ANSWERS.skills;
                }}
                else if (combined.includes('langue') || combined.includes('langage') && !combined.includes('programmation')) {{
                    answer = ANSWERS.languages;
                }}
                else if (combined.includes('visa') || combined.includes('sponsor') || combined.includes('travail') || combined.includes('autorisation')) {{
                    answer = ANSWERS.visa;
                }}
                else if (combined.includes('rythme') || combined.includes('alternance') || combined.includes('temps')) {{
                    answer = ANSWERS.rhythm;
                }}
                else if (combined.includes('annee') || combined.includes('years') || combined.includes('duree')) {{
                    answer = ANSWERS.years;
                }}
                else if (combined.includes('souhaitez') || combined.includes('poste') || combined.includes('role') || combined.includes('titre') || combined.includes('fonction') || combined.includes('intitule') || combined.includes('position')) {{
                    answer = ANSWERS.role;
                }}
                // 3. Empty visible text input with no attrs -> assume phone
                else if (tag === 'input' && type === 'text' && !ph && !aria && !name) {{
                    answer = ANSWERS.phone;
                }}
                
                if (answer) {{
                    field.focus();
                    field.value = '';
                    field.value = answer;
                    field.dispatchEvent(new Event('input', {{bubbles: true}}));
                    field.dispatchEvent(new Event('change', {{bubbles: true}}));
                    filled.push({{field: tag + '#' + (field.id || ''), type: type, value: answer.substring(0,15)}});
                }}
                
                lastWasCountry = field.value && field.value.includes('+33');
            }}
            
            // STEP B: Find and click next/submit button
            const allBtns = document.querySelectorAll('button');
            const skipNavText = ['vous', 'emplois', 'reseau', 'messagerie', 'notification', 'accueil', 'profil', 'jobs', 'network', 'messaging', 'notifications', 'home', 'raccourci', 'fermer le menu', 'acceder a la recherche', 'passer au contenu', 'conditions', 'solutions', 'telecharger', 'plus', 'publicite', 'toutes les candidatures'];
            let btnClicked = null;
            
            // Strategy 1: Match text exactly
            const nextTerms = ['suivant', 'next', 'continuer', 'continue', 'examiner', 'review', 'envoyer', 'submit', 'postuler', 'apply', 'send', 'done', 'termine', 'terminer'];
            for (const btn of allBtns) {{
                if (btn.offsetParent === null) continue;
                const t = (btn.textContent || '').trim().toLowerCase();
                const cl = (btn.className || '').toLowerCase();
                if (!t) continue;
                if (skipNavText.some(s => t === s)) continue;
                if (nextTerms.some(term => t === term || t.startsWith(term))) {{
                    btn.click();
                    btnClicked = t.substring(0,20);
                    break;
                }}
            }}
            
            // Strategy 2: Primary styled buttons, not navigation
            if (!btnClicked) {{
                for (const btn of allBtns) {{
                    if (btn.offsetParent === null) continue;
                    const t = (btn.textContent || '').trim().toLowerCase();
                    const cl = (btn.className || '').toLowerCase();
                    if (!t) continue;
                    if (skipNavText.some(s => t.includes(s))) continue;
                    if (cl.includes('primary')) {{
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 50) {{
                            btn.click();
                            btnClicked = 'pri:' + t.substring(0,15);
                            break;
                        }}
                    }}
                }}
            }}
            
            if (!btnClicked) {{
                // Strategy 3: Any visible button not in nav, not save/close, prefer bottom
                const candidates = Array.from(allBtns).filter(b => {{
                    if (b.offsetParent === null) return false;
                    const t = (b.textContent || '').trim().toLowerCase();
                    if (!t) return false;
                    const skip = ['fermer', 'close', 'cancel', 'annuler', 'x', '...', 'enregistrer', 'save', 'suivre', 'follow', 'vous', 'emplois', 'accueil', 'messagerie', 'plus', 'partager'];
                    return !skip.some(s => t === s || t.startsWith(s));
                }});
                // Sort by vertical position (bottom-most is likely the modal button)
                candidates.sort((a,b) => {{
                    const ra = a.getBoundingClientRect();
                    const rb = b.getBoundingClientRect();
                    return (rb.top + rb.height) - (ra.top + ra.height);
                }});
                if (candidates.length > 0) {{
                    const btn = candidates[0];
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 50 && rect.height > 20) {{
                        btn.click();
                        btnClicked = 'pos:' + (btn.textContent || '').trim().substring(0,15);
                    }}}}
            }}
            
            // Check if done
            const body = document.body.innerText || '';
            const done = body.includes('Candidature envoy') || body.includes('Application sent');
            
            return {{ filledCount: filled.length, filled: filled.slice(0,5), button: btnClicked, step: step, done: done }};
        }}""", step)
        
        log(f"  Step {step+1}: fill={result.get('filledCount',0)} btn={result.get('button','none')}")
        for f in result.get('filled', []):
            log(f"    -> {f.get('field','?')} = {f.get('value','?')}")
        
        # Upload CV if a file input was detected
        has_file = any('FILE-input' in (f.get('field','') or '') for f in result.get('filled', []))
        if has_file:
            try:
                cv_paths = [
                    str(Path(__file__).parent.parent / "data" / "CV_Chenwei_Hu.pdf"),
                    str(Path(__file__).parent / ".." / "data" / "CV_Chenwei_Hu.pdf"),
                    str(Path(__file__).parent / ".." / "data" / "resume.txt"),
                ]
                cv_path = None
                for p in cv_paths:
                    if os.path.exists(p):
                        cv_path = p
                        break
                if not cv_path:
                    log("  No CV file found, creating one...")
                    cv_path = str(Path(__file__).parent / ".." / "data" / "CV_Chenwei_Hu.pdf")
                    os.makedirs(os.path.dirname(cv_path), exist_ok=True)
                    with open(cv_path, 'w') as f:
                        f.write("CV - Hu Chenwei\nGraphiste / Illustratrice\nFormation: Beaux-Arts Shanghai, Nantes, Besancon")
                log(f"  Upload CV: {cv_path}")
                # Use Playwright setInputFiles on the file input
                fi = page.locator('input[type=file]')
                count = fi.count()
                log(f"  File inputs found: {count}")
                if count > 0:
                    fi.first.set_input_files(cv_path)
                    log("  CV uploaded!")
                    time.sleep(3)  # Wait for LinkedIn to process
                    log("  Waiting for file processing...")
                    time.sleep(2)
                else:
                    for i in range(10):
                        try:
                            fi2 = page.locator(f'input[id*="file-input"]').first
                            if fi2.count() > 0:
                                fi2.set_input_files(cv_path)
                                log("  CV uploaded via ID!")
                                time.sleep(3)
                                break
                        except:
                            pass
            except Exception as e:
                log(f"  CV upload error: {str(e)[:100]}")
            log("  CANDIDATURE ENVOYEE!")
            try:
                d = page.locator("button[aria-label=Dismiss], button:has-text('Done'), button:has-text('Termine')").first
                if d.is_visible(timeout=1000): d.click(); time.sleep(1)
            except: pass
            return True
        
        if not result.get('button'):
            log(f"    Plus de bouton")
            break
    return False

def main():
    from playwright.sync_api import sync_playwright
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    cf_terms = globals().get("search_terms", ["alternance graphiste", "alternance graphisme", "alternance illustrateur", "alternance branding"])
    cf_location = globals().get("search_location", "Paris, France")
    
    # Use persistent browser data outside the project folder (survives re-downloads)
    pw_data_dir = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".linkedin_bot_data")
    os.makedirs(pw_data_dir, exist_ok=True)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=pw_data_dir, headless=False,
            args=["--no-sandbox"],
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR", timezone_id="Europe/Paris",
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        try:
            log("=" * 50)
            log("  LinkedIn Bot V5 - Hu Chenwei")
            log("=" * 50)
            log("")
            log("  1. Chromium s'ouvre")
            log("  2. CONNECTE-TOI dans la fenetre")
            log("  3. Reviens ici, appuie sur ENTREE")
            log("  4. Le bot postule aux offres")
            log("")
            log("=" * 50)
            
            page.goto("https://www.linkedin.com/login", wait_until="load", timeout=20000)
            time.sleep(2)
            input(">>> Appuie sur ENTREE une fois connecte... ")
            
            # Wait for connection (check various logged-in states)
            log("Verification connexion...")
            time.sleep(2)
            connected = False
            for i in range(60):
                try:
                    current_url = page.url.lower()
                    page_title = page.evaluate("document.title")
                    page_text = page.evaluate("document.body.innerText") or ""
                    
                    # Connected: feed in URL, jobs in title, no login in text
                    if "feed" in current_url or ("emploi" in page_title and "S'identifier" not in page_text):
                        log("Connecte!"); connected = True; break
                    if "checkpoint" in current_url or "pin" in current_url or "challenge" in current_url:
                        log("  LinkedIn demande verification (code PIN/email)...")
                    else:
                        log(f"  En attente... ({i*5}s) url={current_url[:40]}")
                    time.sleep(5)
                except Exception as e:
                    log(f"  Check: {str(e)[:40]}")
                    time.sleep(5)
            if not connected:
                log("TIMEOUT connexion"); return
            
            total_applied = 0
            max_apps = 3
            
            for term in cf_terms:
                if total_applied >= max_apps: break
                
                log(f"\nRecherche: {term}")
                qs = f"keywords={term.replace(' ', '+')}&location={cf_location.replace(' ', '+').replace(',', '%2C')}&f_AL=true&start=0"
                
                try:
                    page.goto(f"https://www.linkedin.com/jobs/search/?{qs}", wait_until="load", timeout=25000)
                except: pass
                time.sleep(4)
                
                # Scroll
                page.evaluate("window.scrollTo(0,0)")
                time.sleep(0.5)
                for _ in range(6):
                    page.evaluate("window.scrollBy(0,500)")
                    time.sleep(0.5)
                page.evaluate("window.scrollTo(0,0)")
                time.sleep(2)
                
                # Find cards
                cards_result = page.evaluate("""() => {
                    const list = document.querySelector('ul.jobs-search__results-list');
                    if (list) {
                        const cards = list.querySelectorAll('li');
                        if (cards.length > 0) return cards.length;
                    }
                    const all = document.querySelectorAll('li[data-entity-urn], li[data-occludable-job-id], li.jobs-search-results__list-item');
                    return all.length;
                }""")
                log(f"  {cards_result} offres")
                
                for idx in range(min(cards_result or 0, 5)):
                    if total_applied >= max_apps: break
                    
                    log(f"  Offre {idx+1}...")
                    clicked = page.evaluate(f"""() => {{
                        const cards = document.querySelectorAll('ul.jobs-search__results-list li, li[data-entity-urn], li[data-occludable-job-id]');
                        if (cards[{idx}]) {{ cards[{idx}].click(); return true; }}
                        return false;
                    }}""")
                    if not clicked: log("    Cant click"); continue
                    time.sleep(random.uniform(2, 4))
                    
                    if click_easy_apply(page):
                        log(f"  Easy Apply!")
                        time.sleep(random.uniform(2, 3))
                        if handle_easy_apply_v5(page):
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
