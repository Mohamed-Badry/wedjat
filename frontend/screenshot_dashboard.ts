import puppeteer from 'puppeteer-core';

(async () => {
    try {
        const browser = await puppeteer.launch({
            executablePath: './run_chrome.sh',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log("Navigating to http://localhost:5173/eda-report");
        await page.goto('http://localhost:5173/eda-report', { waitUntil: 'networkidle0' });
        
        await page.screenshot({ path: '/home/crim/Projects/gr_sat/.screenshots/eda-report_view.png' });
        
        await browser.close();
    } catch (e) {
        console.error("Error running script:", e);
    }
})();
