import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const pages = [
  { url: 'http://localhost:5173/dashboard', name: 'home' },
  { url: 'http://localhost:5173/dashboard/operations', name: 'ops' },
  { url: 'http://localhost:5173/dashboard/live', name: 'live' },
  { url: 'http://localhost:5173/dashboard/inspector', name: 'inspector' },
  { url: 'http://localhost:5173/dashboard/ml', name: 'ml' },
  { url: 'http://localhost:5173/dashboard/analytics', name: 'analytics' }
];

const screenshotsDir = '/home/crim/Projects/gr_sat/frontend/static/screenshots';

(async () => {
    try {
        if (!fs.existsSync(screenshotsDir)){
            fs.mkdirSync(screenshotsDir, { recursive: true });
        }

        const browser = await puppeteer.launch({
            executablePath: './run_chrome.sh',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        // Ensure starting state is clean
        await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle0' });
        await page.evaluate(() => localStorage.setItem('theme', 'dark'));
        
        for (const p of pages) {
            console.log(`\nProcessing ${p.name}...`);
            
            // Navigate to page (should be dark mode based on localstorage)
            await page.goto(p.url, { waitUntil: 'networkidle0' });
            
            // Force dark mode just in case (no reload)
            await page.evaluate(() => {
                if (document.documentElement.classList.contains('light')) {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Light Mode'));
                    if (btn) btn.click();
                }
            });
            
            // Special handling for ops page to populate the pass data
            if (p.name === 'ops') {
                console.log(`  [Ops Page] Activating pass predictions...`);
                await page.evaluate(() => {
                    const calcBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Calculate'));
                    if (calcBtn) calcBtn.click();
                });
                // Wait for the API to return and the map to update
                await new Promise(r => setTimeout(r, 4000));
            }
            
            // Wait for entry animations
            await new Promise(r => setTimeout(r, 2000));
            
            const darkPath = path.join(screenshotsDir, `${p.name}-dark.png`);
            await page.screenshot({ path: darkPath });
            console.log(`  [Dark Mode] Saved ${darkPath}`);

            // --- LIGHT MODE ---
            console.log(`  [Light Mode] Toggling Theme...`);
            let isLight = false;
            for (let attempt = 0; attempt < 3; attempt++) {
                isLight = await page.evaluate(() => {
                    if (document.documentElement.classList.contains('light')) return true;
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.includes('Dark Mode'));
                    if (btn) btn.click();
                    return document.documentElement.classList.contains('light');
                });
                if (isLight) break;
                await new Promise(r => setTimeout(r, 500));
            }
            
            if (!isLight) {
                console.log("  [ERROR] FAILED TO TOGGLE LIGHT MODE!");
                await page.evaluate(() => {
                    localStorage.setItem('theme', 'light');
                    document.documentElement.classList.add('light');
                });
            }
            
            // Wait for color transitions to finish (usually 300ms, wait 2s to be safe)
            await new Promise(r => setTimeout(r, 2000));
            
            const lightPath = path.join(screenshotsDir, `${p.name}-light.png`);
            await page.screenshot({ path: lightPath });
            console.log(`  [Light Mode] Saved ${lightPath}`);
            
            // Reset back to dark mode for the next page so the loop starts clean
            await page.evaluate(() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const themeBtns = buttons.filter(b => b.textContent && b.textContent.includes('Light Mode'));
                let clicked = false;
                for (const btn of themeBtns) {
                    btn.click();
                    clicked = true;
                }
                if (!clicked) {
                    localStorage.setItem('theme', 'dark');
                    document.documentElement.classList.remove('light');
                }
            });
            await new Promise(r => setTimeout(r, 500));
        }
        
        await browser.close();
        console.log("\nAll screenshots completed successfully!");
    } catch (e) {
        console.error("Error running script:", e);
    }
})();
