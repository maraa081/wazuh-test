const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  
  await page.goto('https://www.linkedin.com/login', { waitUntil: 'load', timeout: 20000 });
  await page.waitForTimeout(3000);
  
  // Fill via JavaScript execution (bypass visibility checks)
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('input');
    for (const input of inputs) {
      const autocomplete = input.getAttribute('autocomplete') || '';
      if (autocomplete === 'username') {
        input.value = 'chen771216000@gmail.com';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
      if (autocomplete === 'current-password') {
        input.value = '1216413@Huchenyang';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
  });
  console.log('✅ Values set via JS');
  
  await page.waitForTimeout(1000);
  
  // Click submit via JS too
  await page.evaluate(() => {
    const btn = document.querySelector('button[type="submit"]');
    if (btn) btn.click();
  });
  console.log('✅ Submit clicked');
  
  await page.waitForTimeout(8000);
  console.log('URL after:', page.url());
  
  if (page.url().includes('feed')) {
    console.log('✅✅✅ LOGIN SUCCESSFUL! LinkedIn feed loaded');
    await page.screenshot({ path: 'logs/linkedin_success.png' });
  } else if (page.url().includes('checkpoint')) {
    console.log('⚠️ LinkedIn checkpoint/challenge page');
    await page.screenshot({ path: 'logs/linkedin_challenge.png' });
  } else {
    console.log('⚠️ Unexpected URL');
    await page.screenshot({ path: 'logs/linkedin_unknown.png' });
  }
  
  await browser.close();
})().catch(e => console.log('ERROR:', e.message.substring(0, 300)));
