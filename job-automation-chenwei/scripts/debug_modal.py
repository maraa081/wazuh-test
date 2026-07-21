"""
Debug script: opens LinkedIn, user logs in, clicks a job, dumps Easy Apply modal HTML.
"""
import os, sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bots" / "linkedin"))

pw_data_dir = str(Path(__file__).parent / "playwright_data")
os.makedirs(pw_data_dir, exist_ok=True)
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=pw_data_dir,
        headless=False,
        args=["--no-sandbox"],
        viewport={"width": 1920, "height": 1080},
        locale="fr-FR",
    )
    page = context.pages[0] if context.pages else context.new_page()
    
    print("=== LOGIN MANUEL ===")
    page.goto("https://www.linkedin.com/")
    input(">>> Connecte-toi a LinkedIn, puis appuie sur ENTREE... ")
    
    print("=== RECHERCHE ===")
    page.goto("https://www.linkedin.com/jobs/search/?keywords=alternance+graphiste&location=Paris&f_AL=true")
    time.sleep(5)
    input(">>> Appuie sur ENTREE pour cliquer la 1ere offre... ")
    
    # Click first job via JS
    page.evaluate("""() => {
        const links = document.querySelectorAll('a[href*="/jobs/view/"]');
        if (links[0]) links[0].click();
    }""")
    time.sleep(4)
    
    print("=== ANALYSE BOUTONS ===")
    # Dump ALL button info
    info = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        const results = [];
        btns.forEach((b, i) => {
            const rect = b.getBoundingClientRect();
            results.push({
                idx: i,
                text: (b.textContent || '').trim().substring(0,40),
                cls: (b.className || '').substring(0,80),
                type: b.type || '',
                aria: (b.getAttribute('aria-label') || '').substring(0,40),
                w: Math.round(rect.w || rect.width),
                h: Math.round(rect.h || rect.height),
                visible: b.offsetParent !== null,
                top: Math.round(rect.top)
            });
        });
        return results;
    }""")
    
    print(f"\n{len(info)} boutons sur la page:")
    for b in info:
        if b['visible']:
            print(f"  [{b['idx']}] txt='{b['text']}' cls='{b['cls'][:40]}' w={b['w']} top={b['top']}")
    
    # Screenshot
    page.screenshot(path=str(LOG_DIR / "debug_job_page.png"))
    print("\nScreenshot: logs/debug_job_page.png")
    
    # Try to click Easy Apply
    print("\n=== CLIC Easy Apply ===")
    clicked = page.evaluate("""() => {
        const allEls = document.querySelectorAll('button, a, span, div');
        for (const el of allEls) {
            const t = (el.textContent || '').trim().toLowerCase();
            const cl = (el.className || '').toLowerCase();
            if ((t.includes('easy apply') || t.includes('candidature simplifi') || t.includes('postuler facilement') || cl.includes('easy-apply')) && el.offsetParent !== null) {
                el.click();
                return 'clicked: ' + t.substring(0,30) + ' tag=' + el.tagName;
            }
        }
        return 'not found';
    }""")
    print(f"Result: {clicked}")
    
    if 'clicked' in clicked:
        time.sleep(3)
        input(">>> Modal ouverte ? Appuie sur ENTREE pour dumper le HTML... ")
        
        # Dump modal HTML
        modal_html = page.evaluate("""() => {
            const modal = document.querySelector('[class*="artdeco-modal"], [class*="modal"], [role="dialog"]');
            if (!modal) return 'NO MODAL FOUND';
            return modal.outerHTML.substring(0, 5000);
        }""")
        print(f"\n=== MODAL HTML (5000 chars) ===\n{modal_html}")
        
        # Dump modal buttons
        modal_btns = page.evaluate("""() => {
            const modal = document.querySelector('[class*="artdeco-modal"], [class*="modal"], [role="dialog"]');
            if (!modal) return [];
            const btns = modal.querySelectorAll('button');
            return Array.from(btns).map(b => ({
                text: (b.textContent || '').trim().substring(0,40),
                cls: (b.className || '').substring(0,60),
                w: Math.round(b.getBoundingClientRect().w || b.getBoundingClientRect().width),
                visible: b.offsetParent !== null
            }));
        }""")
        print(f"\n=== BOUTONS DANS MODAL ({len(modal_btns)}) ===")
        for b in modal_btns:
            print(f"  txt='{b['text']}' cls='{b['cls']}' w={b['w']} visible={b['visible']}")
    
    input(">>> Appuie sur ENTREE pour fermer...")
    context.close()
