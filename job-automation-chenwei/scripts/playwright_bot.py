"""
Playwright LinkedIn Easy Apply Bot - Hu Chenwei
Utilise le Chrome installe sur Windows (pas de chromedriver necessaire)
"""
import os, sys, json, time, re, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "candidate_bot"))
from config.personals import *
from config.secrets import *
from config.search import *
from config.questions import *

LOG_DIR = Path(__file__).parent.parent / "logs"
DATA_DIR = Path(__file__).parent.parent / "data"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except:
        print(line.encode('ascii', 'replace').decode(), flush=True)
    try:
        (LOG_DIR / "playwright_bot.log").open("a", encoding="utf-8").write(line + "\n")
    except:
        pass

def answer_question(question_text):
    q = question_text.lower()
    if any(w in q for w in ["portfolio", "site", "lien"]): return portfolio_url
    if "linkedin" in q: return linkedin_url
    if any(w in q for w in ["telephone", "phone", "mobile"]): return phone_number
    if any(w in q for w in ["email", "e-mail", "courriel"]): return "via0000413@gmail.com"
    if any(w in q for w in ["motivation", "lettre", "pourquoi"]): return motivation_letter[:200]
    if any(w in q for w in ["salaire", "pretention"]): return "A discuter selon la grille de l'ecole"
    if any(w in q for w in ["disponible", "disponibilite", "commencer"]): return "A partir de septembre 2026"
    if any(w in q for w in ["experience", "parcours", "formation"]): return additional_questions.get("experience", "Formation Beaux-Arts")
    if any(w in q for w in ["logiciel", "adobe", "competence"]): return "Photoshop, Illustrator, InDesign, Procreate, ZBrush"
    if any(w in q for w in ["langue"]): return "Chinois (maternel), Francais (B2), Anglais (intermediaire)"
    if any(w in q for w in ["github"]): return "https://github.com/maraa081/wazuh-test"
    if any(w in q for w in ["visa", "sponsor", "autorisation"]): return "Non - Titre de sejour valide"
    if any(w in q for w in ["rythme", "alternance"]): return "3j entreprise / 2j ecole"
    return None

async def main():
    from playwright.async_api import async_playwright
    
    log("=" * 50)
    log(f"  LinkedIn Easy Apply Bot - Hu Chenwei")
    log("=" * 50)
    log(f"Recherches: {len(search_terms)} termes")
    log(f"Localisation: {search_location}")
    
    (LOG_DIR).mkdir(parents=True, exist_ok=True)
    (DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Utiliser le Chrome installe sur Windows
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
            storage_state=os.path.join(str(DATA_DIR), "linkedin_state.json") if os.path.exists(str(DATA_DIR / "linkedin_state.json")) else None
        )
        page = await context.new_page()
        
        try:
            # Login
            log("Connexion a LinkedIn...")
            await page.goto("https://www.linkedin.com/login", wait_until="load", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Check if already logged in
            if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                log("Remplissage du formulaire de connexion...")
                try:
                    # LinkedIn login fields - use text input detection
                    inputs = await page.query_selector_all('input[type="text"], input[type="email"], input:not([type="hidden"])')
                    for inp in inputs:
                        ph = (await inp.get_attribute("placeholder") or "").lower()
                        name = (await inp.get_attribute("name") or "").lower()
                        if "email" in ph or "email" in name or "phone" in ph or "username" in name:
                            await inp.fill(username)
                            log(f"  Email rempli")
                            break
                    
                    await page.wait_for_timeout(1000)
                    
                    pws = await page.query_selector_all('input[type="password"]')
                    for pw in pws:
                        await pw.fill(password)
                        log(f"  Mot de passe rempli")
                        break
                    
                    await page.wait_for_timeout(1000)
                    
                    # Click submit
                    submit = await page.query_selector('button[type="submit"]')
                    if submit:
                        await submit.click()
                        log(f"  Clic sur connexion")
                    else:
                        # Try any primary button
                        btns = await page.query_selector_all('button')
                        for btn in btns:
                            txt = (await btn.text_content() or "").lower()
                            if "sign in" in txt or "sign" in txt or "connecter" in txt:
                                await btn.click()
                                log(f"  Clic bouton connexion")
                                break
                except Exception as e:
                    log(f"  Erreur formulaire: {str(e)[:80]}")
                    await page.pause()
                await page.wait_for_timeout(5000)
            
            if "checkpoint" in page.url.lower() or "security" in page.url.lower():
                log("⚠️ CHALLENGE DE SECURITE - Laisse la fenetre ouverte et connecte-toi")
                await page.pause()
            
            log("Connecte!")
            
            total_applied = 0
            current_search_idx = 0
            
            while total_applied < 1 and current_search_idx < len(search_terms):
                term = search_terms[current_search_idx]
                log(f"Recherche: {term}")
                
                params = {
                    "keywords": term,
                    "location": search_location,
                    "f_AL": "true",
                    "start": "0"
                }
                qs = "&".join(f"{k}={v}" for k,v in params.items())
                url = f"https://www.linkedin.com/jobs/search/?{qs}"
                
                await page.goto(url, wait_until="load", timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Click job cards
                job_cards = await page.query_selector_all('.job-card-container, [data-entity-urn*="jobPosting"]')
                log(f"  {len(job_cards)} offres trouvees")
                
                for i, card in enumerate(job_cards[:5]):
                    if total_applied >= 1:
                        break
                    
                    await card.click()
                    await page.wait_for_timeout(2000)
                    
                    # Check Easy Apply
                    easy_btn = await page.query_selector('button:has-text("Candidature simplifiee"), button:has-text("Easy Apply"), button:has-text("Postuler")')
                    if not easy_btn:
                        continue
                    
                    btn_text = await easy_btn.text_content()
                    if "Postuler" in btn_text and "Easy" not in btn_text and "simplifiee" not in btn_text:
                        continue
                    
                    log(f"  Candidature trouvee!")
                    await easy_btn.click()
                    await page.wait_for_timeout(2000)
                    
                    # Handle multi-step form
                    for step in range(10):
                        # Fill visible inputs
                        inputs = await page.query_selector_all('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea')
                        for inp in inputs:
                            if await inp.get_attribute("value"):
                                continue
                            placeholder = (await inp.get_attribute("placeholder") or "")
                            aria_label = (await inp.get_attribute("aria-label") or "")
                            name = (await inp.get_attribute("name") or "")
                            txt = placeholder + " " + aria_label + " " + name
                            
                            answer = answer_question(txt)
                            if answer:
                                await inp.fill(answer)
                                log(f"    Rempli: {placeholder or aria_label or name}")
                        
                        # Check radio/checkbox
                        radios = await page.query_selector_all('input[type="radio"], input[type="checkbox"]')
                        for radio in radios:
                            label_el = await page.evaluate('''(el) => {
                                const lbl = document.querySelector('label[for="' + el.id + '"]');
                                return lbl ? lbl.textContent : '';
                            }''', radio)
                            if ("oui" in label_el.lower() or "yes" in label_el.lower() or "agree" in label_el.lower() or "accept" in label_el.lower()):
                                if not await radio.is_checked():
                                    await radio.check()
                                    log(f"    Check: {label_el[:30]}")
                        
                        # Submit/Next
                        submit_btn = await page.query_selector('button[aria-label*="Submit"], button[aria-label*="Next"], button:has-text("Suivant"), button:has-text("Submit"), button:has-text("Examiner"), button:has-text("Review"), button:has-text("Envoyer")')
                        if not submit_btn:
                            log(f"    Plus de bouton (etape {step+1})")
                            break
                        
                        text = await submit_btn.text_content()
                        await submit_btn.click()
                        await page.wait_for_timeout(2000)
                        log(f"    Bouton: {text}")
                        
                        # Check success
                        body_text = await page.evaluate("document.body.innerText")
                        if "Candidature envoyee" in body_text or "Application sent" in body_text:
                            log(f"  ✅ CANDIDATURE ENVOYEE!")
                            total_applied += 1
                            break
                    
                    await page.wait_for_timeout(3000)
                
                current_search_idx += 1
            
            log(f"Total: {total_applied} candidature(s)")
            
            # Save state
            await context.storage_state(path=str(DATA_DIR / "linkedin_state.json"))
            
        finally:
            await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
