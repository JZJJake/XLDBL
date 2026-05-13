const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('http://localhost:5173');

  // Wait 10s for initial load/idle
  await page.waitForTimeout(10000);

  // Move to center of canvas
  await page.mouse.move(640, 360);

  await page.evaluate(() => {
    const el = document.querySelector('.graph-wrapper');
    if (el) {
       el.dispatchEvent(new MouseEvent('mouseenter'));
       window.dispatchEvent(new MouseEvent('mousemove'));
    }
  });

  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'frontend_hover_forced.png' });

  await browser.close();
})();
