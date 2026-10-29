(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('[data-theme-toggle]');
  const updateThemeButton = () => {
    const dark = root.dataset.theme !== 'light';
    if (!themeButton) return;
    themeButton.setAttribute('aria-label', dark ? '切换浅色主题' : '切换深色主题');
    themeButton.title = themeButton.getAttribute('aria-label');
    themeButton.setAttribute('aria-pressed', String(!dark));
  };
  updateThemeButton();
  themeButton?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
    try { localStorage.setItem('u3-theme', root.dataset.theme); } catch {}
    updateThemeButton();
    window.dispatchEvent(new Event('site:theme'));
  });

  const menu = document.querySelector('[data-menu-toggle]');
  const navigation = document.querySelector('#primary-navigation');
  menu?.addEventListener('click', () => {
    const open = navigation.classList.toggle('is-open');
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? '收起导航' : '展开导航');
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && navigation?.classList.contains('is-open')) {
      navigation.classList.remove('is-open');
      menu?.setAttribute('aria-expanded', 'false');
      menu?.focus();
    }
  });

  const search = document.querySelector('[data-post-search]');
  const filters = [...document.querySelectorAll('[data-post-filter]')];
  const items = [...document.querySelectorAll('[data-post-item]')];
  if (items.length) {
    const filterPosts = () => {
      const query = (search?.value || '').trim().toLocaleLowerCase();
      let count = 0;
      for (const item of items) {
        const matches = (!query || item.dataset.search.includes(query)) && filters.every(filter =>
          !filter.value || item.dataset[filter.dataset.postFilter] === filter.value);
        item.hidden = !matches;
        if (matches) count++;
      }
      document.querySelectorAll('[data-year-group]').forEach(group => {
        group.hidden = ![...group.querySelectorAll('[data-post-item]')].some(item => !item.hidden);
      });
      const status = document.querySelector('[data-post-status]');
      if (status) status.textContent = `找到 ${count} 篇文章`;
      const empty = document.querySelector('[data-post-empty]');
      if (empty) empty.hidden = count > 0;
    };
    search?.addEventListener('input', filterPosts);
    filters.forEach(filter => filter.addEventListener('change', filterPosts));
    const params = new URLSearchParams(location.search);
    filters.forEach(filter => {
      const requested = params.get(filter.dataset.postFilter);
      if ([...filter.options].some(option => option.value === requested)) filter.value = requested;
    });
    document.querySelector('[data-clear-search]')?.addEventListener('click', () => {
      if (search) search.value = '';
      filters.forEach(filter => { filter.value = ''; });
      filterPosts();
      search?.focus();
    });
    filterPosts();
  }

  const article = document.querySelector('.single-wrap > article');
  if (article) {
    const headings = [...article.querySelectorAll('h1,h2,h3')];
    if (headings.length > 2) {
      const details = document.createElement('details');
      details.className = 'article-toc';
      const summary = document.createElement('summary');
      summary.textContent = '文章目录';
      const list = document.createElement('ol');
      headings.forEach((heading, index) => {
        if (!heading.id) heading.id = `section-${index + 1}`;
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = `#${encodeURIComponent(heading.id)}`;
        a.textContent = heading.textContent;
        li.classList.toggle('toc-subsection', heading.tagName === 'H3');
        li.append(a); list.append(li);
      });
      details.append(summary, list);
      article.before(details);
    }
    article.querySelectorAll('pre').forEach(pre => {
      if (pre.querySelector('.language-mermaid')) return;
      const code = pre.querySelector('code');
      if (!code || !navigator.clipboard) return;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'copy-code';
      button.textContent = '复制'; button.title = '复制代码';
      button.setAttribute('aria-label', '复制代码');
      button.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(code.textContent);
          button.textContent = '已复制';
        } catch { button.textContent = '复制失败'; }
        setTimeout(() => { button.textContent = '复制'; }, 1800);
      });
      pre.append(button);
    });
  }

  const zoomable = [...document.querySelectorAll('.single-wrap article img, .screenshot-gallery img')]
    .filter(img => !img.closest('a'));
  if (zoomable.length) {
    const dialog = document.createElement('dialog');
    dialog.className = 'image-viewer';
    dialog.setAttribute('aria-label', '查看原尺寸图片');
    const close = document.createElement('button');
    close.type = 'button'; close.textContent = '关闭';
    const full = document.createElement('img');
    dialog.append(close, full); document.body.append(dialog);
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    for (const img of zoomable) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'image-zoom';
      button.setAttribute('aria-label', `放大图片：${img.alt || '文章配图'}`);
      img.before(button); button.append(img);
      button.addEventListener('click', () => {
        full.src = img.currentSrc || img.src; full.alt = img.alt;
        dialog.showModal();
      });
    }
  }
})();
