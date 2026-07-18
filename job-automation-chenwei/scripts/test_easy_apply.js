// Test LinkedIn - 1 VRAIE candidature (v3)
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const path = require('path');

(async () => {
  console.log('🚀 Test 1 candidature LinkedIn Easy Apply');
  
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR'
  });
  const page = await context.newPage();
  
  // Cookies
  await page.goto('https://www.linkedin.com/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  const readerScript = path.join(__dirname, 'read_cookies.py');
  const picklePath = '/home/user/.auto-job-apply-profile-linkedin/linkedin_cookies.pkl';
  const result = execSync('python3 ' + readerScript + ' ' + picklePath);
  for (const c of JSON.parse(result.toString())) {
    try { await context.addCookies([c]); } catch(e) {}
  }
  
  await page.goto('https://www.linkedin.com/feed/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  if (!page.url().includes('feed')) { console.log('❌ Session expirée'); await browser.close(); return; }
  console.log('✅ Connecté');
  
  // Search jobs
  const params = new URLSearchParams({
    keywords: 'alternance graphiste',
    location: 'Paris',
    f_AL: 'true',
    f_E: '1,2',
    f_TPR: 'r2592000',
    start: '0'
  });
  
  await page.goto(`https://www.linkedin.com/jobs/search/?${params.toString()}`, { 
    waitUntil: 'domcontentloaded', timeout: 15000 
  });
  await page.waitForTimeout(3000);
  
  // Get job cards
  const cards = await page.evaluate(() => {
    const items = document.querySelectorAll('[data-entity-urn*="jobPosting"], .job-card-container, .scaffold-layout__list-item');
    const jobs = [];
    items.forEach(el => {
      const title = el.querySelector('a, span, strong')?.textContent?.trim() || '';
      const company = el.querySelector('[data-tracking*="company"]')?.textContent?.trim() || '';
      jobs.push({ title, company });
    });
    return jobs;
  });
  
  console.log(`📋 Offres trouvées: ${cards.length}`);
  cards.forEach((j, i) => {
    if (i < 5) console.log(`  ${i+1}. ${j.title.slice(0, 50)} — ${j.company.slice(0, 30)}`);
  });
  
  // Try each card to find Easy Apply
  for (let i = 0; i < Math.min(cards.length, 5); i++) {
    console.log(`\n🔍 Essai offre ${i+1}...`);
    
    // Click card via JS
    await page.evaluate((idx) => {
      const items = document.querySelectorAll('[data-entity-urn*="jobPosting"], .job-card-container, .scaffold-layout__list-item');
      if (items[idx]) items[idx].click();
    }, i);
    await page.waitForTimeout(2000);
    
    // Check Easy Apply
    const hasEasyApply = await page.evaluate(() => {
      const btns = document.querySelectorAll('button');
      console.log('Checking buttons...');
      for (const btn of btns) {
        const txt = btn.textContent.trim();
        // LinkedIn a changé: le bouton s'appelle "Apply" ou "Postuler" maintenant
        if (txt === 'Apply' || txt === 'Postuler' || txt.includes('Candidater') || txt.includes('Postuler') || txt === 'Candidature simplifiée') {
          btn.click();
          return txt;
        }
      }
      return null;
    });
    
    if (hasEasyApply) {
      console.log(`🎯 Easy Apply trouvé !`);
      await page.waitForTimeout(3000);
      
      // Handle multi-step form
      let step = 0;
      while (step < 10) {
        // Fill fields
        await page.evaluate(() => {
          const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea');
          const answers = {
            'portfolio': 'https://github.com/maraa081/wazuh-test',
            'linkedin': 'https://www.linkedin.com/in/chenwei-h-9223b3422/',
            'téléphone': '+33678352974',
            'phone': '+33678352974',
            'email': 'via0000413@gmail.com',
            'motivation': 'Artiste formée aux Beaux-Arts de Shanghai, Nantes et Besançon, recherche alternance en design graphique, illustration ou branding à partir de septembre 2026. Maîtrise Photoshop, Illustrator, InDesign, Procreate, ZBrush.',
            'salaire': 'À discuter',
            'disponible': 'Septembre 2026',
            'prétention': 'Selon grille',
          };
          inputs.forEach(input => {
            const txt = ((input.placeholder || '') + ' ' + (input.getAttribute('aria-label') || '') + ' ' + (input.getAttribute('name') || '') + ' ' + (input.getAttribute('id') || '')).toLowerCase();
            for (const [key, val] of Object.entries(answers)) {
              if (txt.includes(key) && !input.value) {
                const setter = Object.getOwnPropertyDescriptor(
                  input.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(input, val);
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                break;
              }
            }
          });
          document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(el => {
            const label = (document.querySelector('label[for="' + el.id + '"]')?.textContent || '').toLowerCase();
            if ((label.includes('oui') || label.includes('yes') || label.includes('accept')) && !el.checked) el.click();
          });
        });
        
        // Click next/submit
        const btnClicked = await page.evaluate(() => {
          const btns = document.querySelectorAll('button');
          const priority = ['Envoyer', 'Submit', 'Suivant', 'Next', 'Examiner', 'Review'];
          for (const txt of priority) {
            for (const btn of btns) {
              if (btn.offsetParent !== null && btn.textContent.trim() === txt) { btn.click(); return txt; }
            }
          }
          for (const txt of priority) {
            for (const btn of btns) {
              if (btn.offsetParent !== null && btn.textContent.trim().toLowerCase().includes(txt.toLowerCase())) { btn.click(); return txt; }
            }
          }
          return null;
        });
        
        if (!btnClicked) { console.log('ℹ️ Plus de bouton'); break; }
        console.log(`  Étape ${step+1}: "${btnClicked}"`);
        step++;
        await page.waitForTimeout(2000);
        
        // Check success
        if (await page.evaluate(() => document.body.textContent.includes('Candidature envoyée') || document.body.textContent.includes('Application sent'))) {
          console.log('\n✅✅✅ CANDIDATURE ENVOYÉE !');
          await page.screenshot({ path: 'logs/success.png' });
          console.log('📸 Capture: logs/success.png');
          await browser.close();
          console.log('\n🔍 Vérifie sur LinkedIn :');
          console.log('   https://www.linkedin.com/in/chenwei-h-9223b3422/details/interests/');
          console.log('   Ou : Jobs > Mes candidatures');
          return;
        }
      }
      
      break; // Found and tried Easy Apply
    }
    
    console.log('  ⏭️ Pas de Easy Apply');
  }
  
  console.log('\n⚠️ Aucune offre Easy Apply trouvée parmi les 5 premières');
  await page.screenshot({ path: 'logs/search_results.png' });
  
  await browser.close();
})().catch(e => console.log('ERREUR:', e.message));
