const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const posts = JSON.parse(fs.readFileSync(path.join(root, 'data/posts.json'), 'utf8'));
const base = process.env.SITE_TEST_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const failures = [];
  const errors = [];
  const results = [];
  try {
    for (const width of [375,1280]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      page.on('pageerror', error => errors.push(error.message));
      for (let index=0; index<posts.length; index++) {
        const post = posts[index];
        await page.goto(base+post.url,{waitUntil:'load'});
        assert.equal(await page.locator('.single-head .title').textContent(),post.title);
        for (const theme of ['dark','light']) {
          if (await page.locator('html').getAttribute('data-theme')!==theme) await page.locator('[data-theme-toggle]').click();
          const state = await page.evaluate(() => {
            const article = document.querySelector('.single-wrap > article');
            const rect = article.getBoundingClientRect();
            const escaped = [...article.children].filter(e=>!e.hidden).map(e=>({tag:e.tagName,rect:e.getBoundingClientRect()}))
              .filter(e=>e.rect.width>0 && (e.rect.left < -1 || e.rect.right>innerWidth+1)).map(e=>e.tag);
            return { documentWidth:document.documentElement.scrollWidth,articleWidth:rect.width,
              body:getComputedStyle(article.querySelector('p') || article).color,
              background:getComputedStyle(article).backgroundColor,escaped };
          });
          if(state.documentWidth>width+1 || state.escaped.length) failures.push({id:post.id,width,theme,...state});
          if(state.body !== (theme==='dark'?'rgb(237, 245, 242)':'rgb(21, 43, 36)')) failures.push({id:post.id,width,theme,issue:'body color',...state});
          results.push({id:post.id,width,theme});
        }
        if((index+1)%50===0) console.log(`${width}px: ${index+1}/215 articles`);
      }
      await page.close();
    }
    fs.writeFileSync(path.resolve(root,'../qa/post-results.json'),JSON.stringify({checks:results.length,failures,errors},null,2));
    assert.deepEqual(failures,[]);
    assert.deepEqual(errors,[]);
    console.log(`PASS: ${results.length} article/theme/viewport checks across all 215 posts.`);
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
