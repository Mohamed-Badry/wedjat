import puppeteer from 'puppeteer-core';

(async () => {
    const browser = await puppeteer.launch({
        executablePath: './run_chrome.sh',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle0' });
    
    await page.evaluate(() => {
        localStorage.setItem('theme', 'light');
    });
    await page.reload({ waitUntil: 'networkidle0' });
    
    await new Promise(r => setTimeout(r, 2000));
    
    const theme = await page.evaluate(() => localStorage.getItem('theme'));
    const classes = await page.evaluate(() => document.documentElement.className);
    const bg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    
    console.log("Local Storage Theme:", theme);
    console.log("HTML Classes:", classes);
    console.log("Body Background:", bg);
    
    await page.screenshot({ path: '/home/crim/Projects/gr_sat/frontend/static/screenshots/debug-light.png' });
    
    await browser.close();
})();
