"""
DEBUG V2: Capture the Easy Apply modal fields after clicking the real button.
"""
import os, sys, time, json
from pathlib import Path
os.makedirs(str(Path(__file__).parent / "logs"), exist_ok=True)
pw_data_dir = str(Path(__file__).parent / "playwright_data")
os.makedirs(pw_data_dir, exist_ok=True)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=pw_data_dir, headless=False,
        args=["--no-sandbox"], viewport={"width": 1920, "height": 1080}, locale="fr-FR",
    )
    page = context.pages[0] if context.pages else context.new_page()

    print("=== 1. LOGIN ===")
    page.goto("https://www.linkedin.com/")
    input(">>> Connecte-toi a LinkedIn + code PIN, puis ENTREE... ")

    print("=== 2. RECHERCHE ===")
    try:
        page.goto("https://www.linkedin.com/jobs/search/?keywords=alternance+graphiste&location=Paris&f_AL=true", timeout=30000)
    except: pass
    time.sleep(3)
    print("Page chargee (appuie sur ENTREE pour le debug du modal)")
    input(">>> ENTREE...")

    print("=== 3. CLIC EASY APPLY (via la bonne classe) ===")
    # Click the first job card
    clicked = page.evaluate("""() => {
        const cards = document.querySelectorAll('ul.jobs-search__results-list li, li[data-entity-urn]');
        if (cards.length > 0) { cards[0].click(); return 'card clicked'; }
        return 'no cards';
    }""")
    print(f"Card: {clicked}")
    time.sleep(3)

    # Now click Easy Apply
    result = page.evaluate("""() => {
        const btn = document.querySelector('button.jobs-apply-button');
        if (btn && btn.offsetParent !== null) {
            btn.click();
            return {found: true, text: (btn.textContent || '').trim().substring(0,30)};
        }
        return {found: false, text: 'none'};
    }""")
    print(f"Easy Apply click: {result}")
    time.sleep(4)

    # Dump ALL input fields on the page
    print("\n=== 4. ALL FORM FIELDS ON PAGE ===")
    fields = page.evaluate("""() => {
        const inputs = document.querySelectorAll('input, textarea, select');
        return Array.from(inputs).map(el => ({
            tag: el.tagName,
            type: el.getAttribute('type') || '',
            name: el.getAttribute('name') || '',
            id: el.id || '',
            placeholder: (el.getAttribute('placeholder') || '').substring(0,40),
            ariaLabel: (el.getAttribute('aria-label') || '').substring(0,40),
            cl: (el.className || '').substring(0,40),
            value: (el.value || '').substring(0,20),
            visible: el.offsetParent !== null,
        }));
    }""")
    print(f"{len(fields)} fields found:")
    for f in fields:
        if f['visible']:
            print(f"  <{f['tag']}> type='{f['type']}' name='{f['name']}' placeholder='{f['placeholder']}' aria='{f['ariaLabel']}' cls='{f['cl']}' val='{f['value']}'")

    # Find the actual modal
    print("\n=== 5. MODAL STRUCTURE ===")
    modal_info = page.evaluate("""() => {
        const modal = document.querySelector('[class*="artdeco-modal"], [role="dialog"], [class*="modal"]');
        if (!modal) return 'NO MODAL';
        const html = modal.outerHTML.substring(0, 4000);
        return html;
    }""")
    print(f"Modal:\n{modal_info[:2000]}")

    # Screenshot
    page.screenshot(path=str(Path(__file__).parent / "logs" / "debug_modal_v2.png"))
    print("\nScreenshot: logs/debug_modal_v2.png")
    
    input(">>> ENTREE pour fermer...")
    context.close()
