const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  
  await page.goto('https://www.linkedin.com/login', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(3000);
  
  console.log('Title:', await page.title());
  console.log('URL:', page.url());
  
  // Use evaluate to check form status
  const formInfo = await page.evaluate(() => {
    const forms = document.querySelectorAll('form');
    const inputs = document.querySelectorAll('input');
    return {
      forms: forms.length,
      inputs: inputs.length,
      visibleInputs: Array.from(inputs).filter(i => {
        const style = window.getComputedStyle(i);
        return style.display !== 'none' && style.visibility !== 'hidden' && i.offsetParent !== null;
      }).length,
      formAction: forms[0] ? forms[0].action : 'none',
    };
  });
  console.log('Form info:', JSON.stringify(formInfo));
  
  if (formInfo.visibleInputs >= 2) {
    // Inputs are visible, use normal fill
    const emailInput = await page.$('input[autocomplete="username"]');
    const passInput = await page.$('input[autocomplete="current-password"]');
    
    if (emailInput && passInput) {
      await emailInput.fill('chen771216000@gmail.com');
      await passInput.fill('1216413@Huchenyang');
      console.log('Filled form');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(5000);
      console.log('URL:', page.url());
      await page.screenshot({ path: 'logs/linkedin_after_login.png' });
      
      if (page.url().includes('feed')) {
        console.log('✅✅✅ SUCCESS - Logged in!');
      } else if (page.url().includes('checkpoint')) {
        console.log('⚠️ Security checkpoint');
      }
    }
  } else {
    console.log('Inputs not visible, trying JS approach...');
    // Try JS approach
    await page.evaluate(() => {
      const emailField = document.querySelector('input[autocomplete="username"]');
      const passField = document.querySelector('input[autocomplete="current-password"]');
      if (emailField && passField) {
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(emailField, 'chen771216000@gmail.com');
        emailField.dispatchEvent(new Event('input', { bubbles: true }));
        nativeInputValueSetter.call(passField, '1216413@Huchenyang');
        passField.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await page.waitForTimeout(500);
    
    // Click submit
    await page.evaluate(() => {
      const btn = document.querySelector('button[type="submit"]');
      if (btn) btn.click();
    });
    await page.waitForTimeout(5000);
    console.log('URL:', page.url());
    await page.screenshot({ path: 'logs/linkedin_after_login.png' });
  }
  
  await browser.close();
})().catch(e => console.log('ERROR:', e.message));
