import puppeteer from 'puppeteer-core';

(async () => {
    try {
        const browser = await puppeteer.launch({
            executablePath: '/usr/bin/flatpak',
            args: ['run', 'org.chromium.Chromium', '--headless', '--disable-gpu', '--no-sandbox']
        });
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log("Navigating to http://localhost:5173/");
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2' });
        
        console.log("Scrolling to the map section...");
        // Scroll down by 2000px to trigger the sticky story
        await page.evaluate(() => {
            window.scrollBy(0, 2000);
        });
        
        // Wait for GSAP animations to settle
        await new Promise(r => setTimeout(r, 2000));
        
        const screenshotPath = '/home/crim/Projects/gr_sat/.screenshots/cairo_map_scrolled.png';
        await page.screenshot({ path: screenshotPath });
        console.log(`Screenshot saved to ${screenshotPath}`);
        
        await browser.close();
    } catch (e) {
        console.error("Error running script:", e);
    }
})();
