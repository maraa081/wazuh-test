"""
Playwright LinkedIn Easy Apply Bot - Hu Chenwei
V2 - With simpler fill approach using type()
"""
import os, sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "config"))
os.environ["PYTHONIOENCODING"] = "utf-8"

from personals import *
from secrets import username, password
from search import *

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

async def main():
    from playwright.async_api import async_playwright
    
    log("=" * 50)
    log(("  LinkedIn Easy Apply Bot - Hu Chenwei").encode("ascii","replace").decode())
    log("=" * 50)
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch with system Chrome
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        page = await context.new_page()
        
        try:
            log("Login to LinkedIn...")
            await page.goto("https://www.linkedin.com/login", wait_until="load", timeout=30000)
            await page.wait_for_timeout(3000)
            
            curr_url = page.url.lower()
            log(f"URL: {curr_url}")
            
            if "login" in curr_url:
                log("Login page detected")
                
                # Use evaluate to fill fields directly
                filled = await page.evaluate("""({u, p}) => {
                    const inputs = document.querySelectorAll('input:not([type="hidden"])');
                    let filledEmail = false, filledPass = false;
                    for (const inp of inputs) {
                        const ph = (inp.placeholder || '').toLowerCase();
                        const type = (inp.type || '').toLowerCase();
                        if (!filledEmail && (ph.includes('email') || ph.includes('phone') || ph.includes('username') || type === 'email' || type === 'text')) {
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(inp, u);
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            filledEmail = true;
                        }
                        if (!filledPass && (ph.includes('password') || type === 'password')) {
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeSetter.call(inp, p);
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            filledPass = true;
                        }
                    }
                    return {emailFilled: filledEmail, passFilled: filledPass};
                }""", {"u": username, "p": password})
                
                log(f"Fields filled via JS: email={filled.get('emailFilled')}, pass={filled.get('passFilled')}")
                
                await page.wait_for_timeout(1000)
                
                # Click submit
                await page.evaluate("""() => {
                    const btns = document.querySelectorAll('button[type="submit"]');
                    for (const btn of btns) { btn.click(); return true; }
                    const allBtns = document.querySelectorAll('button');
                    for (const btn of allBtns) {
                        const t = (btn.textContent || '').toLowerCase();
                        if (t.includes('sign in') || t.includes('sign') || t.includes('connecter')) {
                            btn.click(); return true;
                        }
                    }
                    return false;
                }""")
                
                log("Submit clicked")
                await page.wait_for_timeout(5000)
            
            log(f"After login URL: {page.url[:80]}")
            
            # Take screenshot for debug
            await page.screenshot(path=str(LOG_DIR / "after_login.png"))
            log("Screenshot: logs/after_login.png")
            
            # Search for jobs
            term = search_terms[0]
            log(f"Searching: {term}")
            
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
            
            log(f"Search URL: {page.url[:100]}")
            
            # Get jobs
            job_html = await page.evaluate("""() => {
                const cards = document.querySelectorAll('[data-entity-urn*="jobPosting"], .job-card-container');
                return Array.from(cards).slice(0,3).map(c => ({
                    title: (c.querySelector('a')?.textContent || '').trim(),
                    company: (c.querySelector('[data-tracking*="company"]')?.textContent || '').trim()
                }));
            }""")
            
            log(f"Jobs found: {len(job_html)}")
            for j in job_html:
                log(f"  - {j.get('title','')[:50]} @ {j.get('company','')[:30]}")
            
            # Try Easy Apply on first job
            if job_html:
                cards = await page.query_selector_all('[data-entity-urn*="jobPosting"], .job-card-container')
                if cards:
                    await cards[0].click()
                    await page.wait_for_timeout(2000)
                    
                    easy_btn = await page.query_selector('button:has-text("Easy Apply"), button:has-text("Candidature simplifiee")')
                    if easy_btn:
                        log("Easy Apply found!")
                        await easy_btn.click()
                        await page.wait_for_timeout(3000)
                        await page.screenshot(path=str(LOG_DIR / "easy_apply_modal.png"))
                        log("Screenshot: easy_apply_modal.png")
                    else:
                        log("No Easy Apply button")
            
            await page.screenshot(path=str(LOG_DIR / "final_state.png"))
            log("Done!")
            
        except Exception as e:
            log(f"ERROR: {str(e)[:200]}")
            await page.screenshot(path=str(LOG_DIR / f"error_{int(time.time())}.png"))
        finally:
            await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
