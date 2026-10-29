const blocks = [...document.querySelectorAll('pre > code.language-mermaid')];
if (blocks.length) {
  const sources = blocks.map(code => {
    const wrapper = document.createElement('div');
    wrapper.className = 'mermaid-wrap';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', '架构图，可横向滚动');
    const source = code.textContent.trim();
    const fallback = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = '图表源码';
    const pre = document.createElement('pre');
    pre.textContent = source;
    fallback.append(summary, pre);
    const graph = document.createElement('div');
    graph.className = 'mermaid';
    const controls = document.createElement('div');
    controls.className = 'diagram-controls';
    const fit = document.createElement('button');
    fit.type = 'button'; fit.className = 'icon-button';
    fit.innerHTML = '<span class="icon icon-fit" aria-hidden="true"></span>';
    wrapper.classList.toggle('diagram-fit', matchMedia('(max-width:620px)').matches);
    const updateFit = () => {
      fit.setAttribute('aria-pressed', String(wrapper.classList.contains('diagram-fit')));
      fit.setAttribute('aria-label', wrapper.classList.contains('diagram-fit') ? '以实际大小查看架构图' : '架构图适应宽度');
      fit.title = fit.getAttribute('aria-label');
    };
    updateFit();
    fit.addEventListener('click', () => { wrapper.classList.toggle('diagram-fit'); updateFit(); });
    controls.append(fit);
    wrapper.append(controls, graph, fallback);
    code.closest('pre').replaceWith(wrapper);
    return { source, graph, fallback };
  });
  try {
    const { default: mermaid } = await import('/assets/vendor/mermaid/mermaid.esm.min.mjs');
    let sequence = 0;
    let rendering = false;
    let pending = false;
    const render = async () => {
      if (rendering) { pending = true; return; }
      rendering = true;
      const dark = document.documentElement.dataset.theme !== 'light';
      mermaid.initialize({
        startOnLoad: false, securityLevel: 'strict', theme: 'base',
        themeVariables: {
          darkMode: dark,
          background: dark ? '#10232b' : '#ffffff',
          primaryColor: dark ? '#173b30' : '#e7f3eb',
          primaryTextColor: dark ? '#edf5f2' : '#17382b',
          primaryBorderColor: dark ? '#65d990' : '#277948',
          secondaryColor: dark ? '#20363e' : '#eef3f5',
          secondaryTextColor: dark ? '#edf5f2' : '#17382b',
          tertiaryColor: dark ? '#172a32' : '#f4f7f6',
          tertiaryTextColor: dark ? '#edf5f2' : '#17382b',
          lineColor: dark ? '#a9c8bd' : '#466255',
          textColor: dark ? '#edf5f2' : '#17382b',
          nodeTextColor: dark ? '#edf5f2' : '#17382b',
          edgeLabelBackground: dark ? '#10232b' : '#ffffff',
          clusterBkg: dark ? '#142b33' : '#f4f7f6',
          clusterBorder: dark ? '#54796d' : '#8eaa9b',
          fontFamily: 'Segoe UI, Microsoft YaHei, sans-serif'
        },
        flowchart: { useMaxWidth: false, htmlLabels: true, wrappingWidth: 400 }
      });
      for (const item of sources) {
        try {
          const { svg } = await mermaid.render(`diagram-${++sequence}`, item.source);
          item.graph.innerHTML = svg;
          item.fallback.open = false;
        } catch {
          item.graph.textContent = '图表未能渲染，可展开下方源码查看。';
          item.fallback.open = true;
        }
      }
      rendering = false;
      if (pending) { pending = false; await render(); }
    };
    window.addEventListener('site:theme', render);
    await render();
  } catch {
    sources.forEach(item => {
      item.graph.textContent = '图表组件加载失败，以下保留完整源码。';
      item.fallback.open = true;
    });
  }
}
