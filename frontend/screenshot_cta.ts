import puppeteer from 'puppeteer-core';

(async () => {
    try {
        const browser = await puppeteer.launch({
            executablePath: './run_chrome.sh',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log("Navigating to http://localhost:5173/");
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
        
        console.log("Scrolling to CTA...");
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await new Promise(r => setTimeout(r, 1500));
        await page.screenshot({ path: '/home/crim/Projects/gr_sat/.screenshots/landing_cta.png' });
        
        console.log("Scrolling to Visual 2...");
        await page.evaluate(() => window.scrollTo(0, 2000));
        await new Promise(r => setTimeout(r, 1500));
        await page.screenshot({ path: '/home/crim/Projects/gr_sat/.screenshots/landing_telemetry.png' });

        await browser.close();
    } catch (e) {
        console.error("Error running script:", e);
    }
})();
