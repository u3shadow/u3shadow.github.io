const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const out = path.resolve(root, '../qa');
fs.mkdirSync(out, { recursive: true });
const posts = JSON.parse(fs.readFileSync(path.join(root, 'data/posts.json'), 'utf8'));
const post = posts.find(p => p.id === 711);
const pages = [['home', '/'], ['projects', '/projects/'], ['about', '/about/'],
  ['articles', '/articles/'], ['archive', '/archive/'], ['shaverai', '/projects/shaverai/'], ['post711', post.url]];
const viewports = [{ width: 375, height: 812 }, { width: 768, height: 1024 },
  { width: 1280, height: 900 }, { width: 1920, height: 1080 }];
const base = process.env.SITE_TEST_URL || 'http://127.0.0.1:8765';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const failures = [];
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport, reducedMotion: 'reduce' });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      for (const [name, url] of pages) {
        await page.goto(base + url);
        await page.waitForLoadState('networkidle');
        if (name === 'shaverai' || name === 'post711') {
          await page.locator('.mermaid svg').first().waitFor({ timeout: 30000 });
        }
        for (const theme of ['dark', 'light']) {
          if (await page.locator('html').getAttribute('data-theme') !== theme) {
            await page.locator('[data-theme-toggle]').click();
            await page.waitForTimeout(250);
          }
          if (name === 'post711' || name === 'shaverai') {
            await page.waitForFunction(() => [...document.querySelectorAll('.mermaid')].every(g =>
              g.querySelector('svg') && !g.textContent.includes('Syntax error')));
          }
          const metrics = await page.evaluate(() => {
            const luminance = color => {
              const channels = (color.match(/[\d.]+/g) || []).slice(0,3).map(Number).map(v => {
                v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
              });
              return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
            };
            const ratio = (a,b) => {
              a=luminance(a); b=luminance(b);return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
            };
            const rect = document.querySelector('main').getBoundingClientRect();
            const cards = [...document.querySelectorAll('.project-card,.ref-project')].map(card => {
              const title = card.querySelector('h3,strong');
              const background = getComputedStyle(card).backgroundColor;
              const text = getComputedStyle(card.querySelector('p')).color;
              const titleColor = getComputedStyle(title).color;
              return { background, title: titleColor, text,
                textContrast: ratio(text,background),
                titleContrast: ratio(titleColor, card.classList.contains('ref-project') ? 'rgb(8, 34, 42)' : background) };
            });
            const graph = document.querySelector('.mermaid-wrap');
            return { width: innerWidth, documentWidth: document.documentElement.scrollWidth,
              mainWidth: rect.width, mainLeft: rect.x, cards,
              graph: graph ? { background: getComputedStyle(graph).backgroundColor,
                text: getComputedStyle(graph.querySelector('.nodeLabel')).color,
                textContrast: ratio(getComputedStyle(graph.querySelector('.nodeLabel')).color,
                  getComputedStyle(graph.querySelector('.node rect, .node polygon')).fill),
                width: graph.clientWidth, scrollWidth: graph.scrollWidth } : null };
          });
          if (metrics.documentWidth > viewport.width + 1) failures.push(`${name} ${theme} ${viewport.width}: page overflow`);
          if (metrics.cards.some(card => card.background !== (theme === 'dark' ? 'rgb(16, 35, 43)' : 'rgb(255, 255, 255)'))) {
            failures.push(`${name} ${theme} ${viewport.width}: wrong card surface`);
          }
          if (metrics.cards.some(card => card.textContrast < 4.5 || card.titleContrast < 4.5)) failures.push(`${name} ${theme} ${viewport.width}: card text contrast`);
          if (metrics.graph?.textContrast < 4.5) failures.push(`${name} ${theme} ${viewport.width}: diagram text contrast`);
          if (name === 'projects') {
            const featured = page.locator('.project-card.featured');
            const before = await featured.evaluate(e => [getComputedStyle(e).backgroundColor, getComputedStyle(e.querySelector('p')).color]);
            await featured.hover();
            const after = await featured.evaluate(e => [getComputedStyle(e).backgroundColor, getComputedStyle(e.querySelector('p')).color]);
            assert.deepEqual(after, before);
            await page.mouse.move(0,0);
          }
          if (name === 'home') {
            assert.equal(await page.locator('.ref-app-stage > .concept-label').count(), 1);
          }
          if (viewport.width === 375) {
            await page.locator('[data-menu-toggle]').click();
            assert.equal(await page.locator('#primary-navigation').isVisible(), true);
            await page.locator('[data-menu-toggle]').click();
          }
          if ([375, 1920].includes(viewport.width)) {
            await page.screenshot({ path: path.join(out, `${name}-${theme}-${viewport.width}.png`),
              fullPage: !['post711', 'articles', 'archive', 'shaverai'].includes(name) });
            if (metrics.graph) {
              await page.locator('.mermaid-wrap').first().screenshot({ path: path.join(out, `${name}-diagram-${theme}-${viewport.width}.png`) });
              await page.evaluate(() => scrollTo(0, 0));
            }
          }
          results.push({ page: name, theme, viewport: viewport.width, ...metrics });
        }
      }
      if (errors.length) failures.push(...errors.map(error => `${viewport.width}: ${error}`));
      await context.close();
      console.log(`Checked ${viewport.width}px: seven pages in both themes`);
    }
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(base + '/articles/');
    await page.locator('[data-post-search]').fill('Room');
    assert.ok(await page.locator('[data-post-item]:visible').count() > 0);
    await page.locator('[data-post-search]').fill('no-such-post-abcdef');
    assert.equal(await page.locator('[data-post-item]:visible').count(), 0);
    assert.equal(await page.locator('[data-post-empty]').isVisible(), true);
    await page.locator('[data-clear-search]').click();
    assert.equal(await page.locator('[data-post-item]:visible').count(), 215);
    await page.locator('[data-post-filter="year"]').selectOption('2026');
    assert.equal(await page.locator('[data-post-item]:visible').count(), 1);
    await page.locator('[data-clear-search]').click();
    await page.locator('[data-post-filter="topic"]').selectOption('HarmonyOS');
    assert.ok(await page.locator('[data-post-item]:visible').count() > 0);
    await page.goto(base + '/projects/shaverai/');
    await page.locator('.image-zoom').first().click();
    assert.equal(await page.locator('dialog').isVisible(), true);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('dialog').isVisible(), false);
    await page.goto(base + post.url);
    await page.locator('.article-toc summary').click();
    assert.ok(await page.locator('.article-toc a:visible').count() > 3);
    await page.locator('.diagram-controls button').first().click();
    assert.equal(await page.locator('.mermaid-wrap.diagram-fit').count(), 1);
    await page.close();
    fs.writeFileSync(path.join(out, 'browser-results.json'), JSON.stringify({ results, failures }, null, 2));
    assert.deepEqual(failures, []);
    console.log(`PASS: ${results.length} page/theme/viewport checks; search, filters, menu, image dialog and TOC.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
