import puppeteer from 'puppeteer-core';

(async () => {
    try {
        const browser = await puppeteer.launch({
            executablePath: './run_chrome.sh',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        
        page.on('console', msg => console.log('PAGE LOG:', msg.text()));
        page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
        
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log("Navigating to http://localhost:5173/");
        const res = await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
        console.log("Status:", res.status());
        
        console.log("Scrolling to check GSAP...");
        await page.evaluate(() => window.scrollTo(0, 500));
        await new Promise(r => setTimeout(r, 500));
        
        await page.screenshot({ path: '/home/crim/Projects/gr_sat/.screenshots/landing_debug.png' });
        
        await browser.close();
    } catch (e) {
        console.error("Error running script:", e);
    }
})();
