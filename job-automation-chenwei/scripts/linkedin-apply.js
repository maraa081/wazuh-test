/**
 * Bot de candidature LinkedIn Easy Apply - Hu Chenwei
 * Utilise Playwright (headless) sur WSL
 * 
 * Usage: node scripts/linkedin-apply.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// ========== CONFIGURATION ==========
const CONFIG = {
  email: 'chen771216000@gmail.com',
  password: '1216413@Huchenyang',
  searchTerms: [
    'alternance graphiste',
    'alternance design graphique',
    'alternance illustrateur',
    'alternance illustration',
    'alternance branding',
    'alternance identité visuelle',
    'alternance direction artistique',
    'alternance PAO',
    'stage graphiste',
    'stage illustrateur',
  ],
  location: 'Paris, Île-de-France, France',
  maxApplications: 15,           // par exécution
  maxPerSearch: 5,               // par terme de recherche
  headless: true,
  // Profil Chenwei
  phone: '+33678352974',
  emailPerso: 'via0000413@gmail.com',
  portfolio: 'https://github.com/maraa081/wazuh-test/tree/main/test',
  linkedin: 'https://www.linkedin.com/in/chenwei-h-9223b3422/',
  // Filtres
  experienceLevel: ['1', '2'],   // 1=Internship, 2=Entry level
  datePosted: 'r604800',         // Past week (7 days)
  easyApplyOnly: true,
};

const LOG_DIR = path.join(__dirname, '..', 'logs');
const DATA_DIR = path.join(__dirname, '..', 'data');

// ========== LOGGING ==========
function log(msg) {
  const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const line = `[${ts}] ${msg}`;
  console.log(line);
  fs.appendFileSync(path.join(LOG_DIR, 'linkedin_apply.log'), line + '\n');
}

// ========== CANDIDATURE ==========
async function waitAndClick(page, selector, timeout = 10000) {
  await page.waitForSelector(selector, { timeout });
  await page.click(selector);
  await page.waitForTimeout(500 + Math.random() * 1000);
}

async function typeLikeHuman(page, selector, text) {
  await page.waitForSelector(selector, { timeout: 5000 });
  await page.click(selector);
  await page.waitForTimeout(200);
  // Clear field
  await page.fill(selector, '');
  // Type character by character with random delays
  for (const char of text) {
    await page.type(selector, char, { delay: 30 + Math.random() * 60 });
  }
}

async function answerQuestion(page, questionText) {
  // Try to find and answer common questions
  const qLower = questionText.toLowerCase();
  
  if (qLower.includes('portfolio') || qLower.includes('site') || qLower.includes('lien')) {
    return CONFIG.portfolio;
  }
  if (qLower.includes('linkedin') || qLower.includes('profil')) {
    return CONFIG.linkedin;
  }
  if (qLower.includes('téléphone') || qLower.includes('phone') || qLower.includes('mobile')) {
    return CONFIG.phone;
  }
  if (qLower.includes('email') || qLower.includes('e-mail') || qLower.includes('courriel')) {
    return CONFIG.emailPerso;
  }
  if (qLower.includes('motivation') || qLower.includes('lettre') || qLower.includes('pourquoi')) {
    return "Artiste et designer visuelle formée aux Beaux-Arts de Shanghai, Nantes et Besançon. Je développe des projets mêlant illustration, design graphique et sculpture, avec un intérêt particulier pour le branding, l'édition et les univers narratifs. Je recherche une alternance en design graphique, illustration ou branding à partir de septembre 2026.";
  }
  if (qLower.includes('salaire') || qLower.includes('prétention')) {
    return "À discuter selon la grille de l'école et les conventions";
  }
  if (qLower.includes('disponible') || qLower.includes('disponibilité') || qLower.includes('commencer')) {
    return "À partir de septembre 2026";
  }
  if (qLower.includes('expérience') || qLower.includes('parcours') || qLower.includes('formation')) {
    return "Formation aux Beaux-Arts de Shanghai (Licence Peinture), Nantes et Besançon (DNA). Expériences : identité visuelle Yuffee (branding café narratif), exposition jeunes artistes Shanghai (vente de 3 sculptures + 20 illustrations), collaboration Artgogo x Brother China (installation écologique CIIE).";
  }
  if (qLower.includes('logiciel') || qLower.includes('adobe') || qLower.includes('compétence')) {
    return "Photoshop, Illustrator, InDesign, Procreate, ZBrush, Keynote";
  }
  if (qLower.includes('langue') || qLower.includes('langue étrangère')) {
    return "Chinois (langue maternelle), Français (B2), Anglais (intermédiaire), Japonais (N4)";
  }
  if (qLower.includes('github') || qLower.includes('code')) {
    return "https://github.com/maraa081/wazuh-test";
  }
  
  return null; // Unknown question
}

async function handleEasyApplyForm(page) {
  log('📝 Remplissage du formulaire Easy Apply...');
  
  // Wait for form to load
  await page.waitForTimeout(2000);
  
  try {
    // Check for text inputs and textareas
    const inputs = await page.$$('input[type="text"], input[type="tel"], input[type="email"], textarea');
    
    for (const input of inputs) {
      const placeholder = await input.getAttribute('placeholder') || '';
      const label = await input.getAttribute('aria-label') || '';
      const name = await input.getAttribute('name') || '';
      const id = await input.getAttribute('id') || '';
      const questionText = (placeholder + ' ' + label + ' ' + name + ' ' + id).toLowerCase();
      
      const answer = await answerQuestion(page, questionText);
      if (answer && !(await input.getAttribute('value'))) {
        await typeLikeHuman(page, input, answer);
        log(`  ✅ Répondu: ${placeholder || label || name}`);
      }
    }
    
    // Handle radio buttons and checkboxes
    const radios = await page.$$('input[type="radio"], input[type="checkbox"]');
    for (const radio of radios) {
      const label = await page.evaluate(el => {
        const lbl = document.querySelector(`label[for="${el.id}"]`);
        return lbl ? lbl.textContent : '';
      }, radio);
      const val = await radio.getAttribute('value');
      const txt = (label + ' ' + (val || '')).toLowerCase();
      
      // Auto-accept: Yes, I agree, I certify...
      if (txt.includes('oui') || txt.includes('yes') || txt.includes('agree') || 
          txt.includes('accept') || txt.includes('certify') || txt.includes('authorize')) {
        if (!(await radio.isChecked())) {
          await radio.check();
          log(`  ✅ Checked: ${label}`);
        }
      }
    }
    
    return true;
  } catch (e) {
    log(`  ⚠️ Erreur formulaire: ${e.message.slice(0, 100)}`);
    return false;
  }
}

async function submitEasyApply(page) {
  try {
    // Look for submit / next / review buttons
    const buttons = await page.$$('button[aria-label*="Submit"], button[aria-label*="Next"], button[aria-label*="Review"], button:has-text("Submit"), button:has-text("Suivant"), button:has-text("Next"), button:has-text("Examiner"), button:has-text("Review")');
    
    for (const btn of buttons) {
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(1000 + Math.random() * 1500);
        return true;
      }
    }
    return false;
  } catch (e) {
    return false;
  }
}

// ========== MAIN FLOW ==========
async function applyToJob(page, jobCard) {
  try {
    // Click on job card
    await jobCard.click();
    await page.waitForTimeout(1000);
    
    // Check if it's Easy Apply
    const easyApplyBtn = await page.$('button[aria-label*="Easy Apply"], button:has-text("Candidature simplifiée"), button:has-text("Easy Apply"), button:has-text("Postuler")');
    if (!easyApplyBtn) {
      log('  ⏭️ Pas de Easy Apply, skip');
      return false;
    }
    
    const btnText = await easyApplyBtn.textContent();
    if (btnText.includes('Postuler') && !btnText.includes('Easy') && !btnText.includes('simplifiée')) {
      log('  ⏭️ Pas un Easy Apply, skip');
      return false;
    }
    
    log('  🎯 Easy Apply trouvé !');
    await easyApplyBtn.click();
    await page.waitForTimeout(2000);
    
    // Handle multi-step form
    let stepsCompleted = 0;
    while (stepsCompleted < 10) {
      // Fill form fields
      await handleEasyApplyForm(page);
      
      // Check for submit/next button
      const nextBtn = await page.$('button[aria-label*="Submit"], button[aria-label*="Next"], button:has-text("Suivant"), button:has-text("Submit"), button:has-text("Examiner")');
      
      if (nextBtn && await nextBtn.isVisible()) {
        const btnTxt = await nextBtn.textContent();
        await nextBtn.click();
        await page.waitForTimeout(1500 + Math.random() * 2000);
        stepsCompleted++;
        
        // Check if we got to the final screen (confirmation or thank you)
        const thankYou = await page.$('[data-test-modal-close-btn], .artdeco-modal__dismiss, button:has-text("Done"), button:has-text("Terminé"), button[aria-label*="Dismiss"]');
        if (thankYou) {
          log('  ✅ Candidature envoyée !');
          await thankYou.click();
          await page.waitForTimeout(1000);
          return true;
        }
      } else {
        break;
      }
    }
    
    // Try to find and click the final submit
    const submitBtns = await page.$$('button[aria-label*="Submit"], button:has-text("Submit"), button:has-text("Envoyer")');
    for (const btn of submitBtns) {
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(2000);
        log('  ✅ Candidature envoyée !');
        
        // Dismiss confirmation modal
        const dismissBtn = await page.$('[data-test-modal-close-btn], button[aria-label*="Dismiss"]');
        if (dismissBtn) await dismissBtn.click();
        return true;
      }
    }
    
    log('  ⚠️ Bouton de soumission non trouvé');
    return false;
    
  } catch (e) {
    log(`  ❌ Erreur: ${e.message.slice(0, 150)}`);
    return false;
  }
}

async function main() {
  log('═══════════════════════════════════════════');
  log('  🔧 LinkedIn Easy Apply Bot - Hu Chenwei');
  log('═══════════════════════════════════════════');
  
  fs.mkdirSync(LOG_DIR, { recursive: true });
  fs.mkdirSync(DATA_DIR, { recursive: true });
  
  const browser = await chromium.launch({ 
    headless: CONFIG.headless,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    locale: 'fr-FR',
    timezoneId: 'Europe/Paris',
  });
  
  const page = await context.newPage();
  
  try {
    // 1. Login to LinkedIn
    log('🔑 Connexion à LinkedIn...');
    await page.goto('https://www.linkedin.com/login', { waitUntil: 'networkidle' });
    await typeLikeHuman(page, '#username', CONFIG.email);
    await typeLikeHuman(page, '#password', CONFIG.password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);
    await page.waitForSelector('.global-nav__primary-links', { timeout: 15000 });
    log('✅ Connecté !');
    
    let totalApplied = 0;
    
    // 2. Search for each term
    for (const searchTerm of CONFIG.searchTerms) {
      if (totalApplied >= CONFIG.maxApplications) break;
      
      log(`🔍 Recherche: "${searchTerm}"`);
      
      // Build search URL
      const params = new URLSearchParams({
        keywords: searchTerm,
        location: CONFIG.location,
        f_AL: CONFIG.easyApplyOnly ? 'true' : '',
        f_E: CONFIG.experienceLevel.join(','),
        f_TPR: CONFIG.datePosted,
        start: 0,
      });
      
      await page.goto(`https://www.linkedin.com/jobs/search/?${params.toString()}`, { 
        waitUntil: 'networkidle' 
      });
      await page.waitForTimeout(2000);
      
      // Scroll to load all job cards
      const jobList = await page.$('.jobs-search-results-list');
      if (!jobList) {
        log('  ⚠️ Aucune offre trouvée');
        continue;
      }
      
      // Get job cards
      const jobCards = await page.$$('.job-card-container, .jobs-search-results__list-item');
      log(`  📋 ${Math.min(jobCards.length, CONFIG.maxPerSearch)} offres chargées`);
      
      let searchApplied = 0;
      
      for (const jobCard of jobCards) {
        if (totalApplied >= CONFIG.maxApplications || searchApplied >= CONFIG.maxPerSearch) break;
        
        const applied = await applyToJob(page, jobCard);
        if (applied) {
          totalApplied++;
          searchApplied++;
          log(`📊 Total: ${totalApplied}/${CONFIG.maxApplications}`);
          
          // Random delay between applications
          const delay = 5000 + Math.random() * 10000;
          log(`⏳ Pause de ${Math.round(delay/1000)}s...`);
          await page.waitForTimeout(delay);
        }
      }
      
      log(`  ✅ "${searchTerm}" terminé (${searchApplied} candidatures)`);
    }
    
    log('═══════════════════════════════════════════');
    log(`  🎉 Terminé ! Total: ${totalApplied} candidatures`);
    log('═══════════════════════════════════════════');
    
    // Save state for next run
    await context.storageState({ path: path.join(DATA_DIR, 'linkedin_state.json') });
    
  } catch (e) {
    log(`❌ ERREUR: ${e.message}`);
    await page.screenshot({ path: path.join(LOG_DIR, `error_${Date.now()}.png`) });
  } finally {
    // Save session for next run
    try {
      await context.storageState({ path: path.join(DATA_DIR, 'linkedin_session.json') });
    } catch (e) {}
    await browser.close();
  }
}

main().catch(e => log(`FATAL: ${e.message}`));
