(async function () {
  'use strict';

  await window.tickrAIOverviewLayout?.ready;
  if (window.tickrAIOverviewLayout?.visual === false) {
    const template = document.getElementById('ai-overview-legacy-template');
    document.getElementById('overview-content').replaceWith(template.content.firstElementChild.cloneNode(true));
    window.tickrLegacyAIOverviewPage();
    return;
  }

  const symbol = document.body.dataset.symbol;
  if (!/^IN:[A-Z][A-Z0-9&-]{0,19}$/.test(symbol || '')) return;

  const $ = id => document.getElementById(id);
  let companyCore = {};
  let aiResponse = null;
  const stockUrl = '/stocks/' + encodeURIComponent(symbol).replace('%3A', ':');
  const sections = new Set(['overview', 'financials', 'ownership', 'analysis', 'actions', 'news']);
  const tones = {positive: 'Positive', negative: 'Negative', caution: 'Watch', neutral: 'Neutral'};

  function node(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  }

  function svgNode(tag, attributes) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
    return element;
  }

  function robotFace(tone, large = false) {
    const mood = Object.hasOwn(tones, tone) ? tone : 'neutral';
    const face = node('span', 'ai-robot ' + mood + (large ? ' is-large' : ''));
    face.setAttribute('aria-hidden', 'true');
    face.dataset.tone = mood;
    const svg = svgNode('svg', {viewBox: '0 0 88 88', focusable: 'false'});
    svg.append(
      svgNode('path', {class: 'ai-robot-antenna', d: 'M44 18V9'}),
      svgNode('circle', {class: 'ai-robot-antenna-tip', cx: 44, cy: 7, r: 4}),
      svgNode('rect', {class: 'ai-robot-ear', x: 5, y: 39, width: 8, height: 16, rx: 4}),
      svgNode('rect', {class: 'ai-robot-ear', x: 75, y: 39, width: 8, height: 16, rx: 4}),
      svgNode('rect', {class: 'ai-robot-shell', x: 10, y: 18, width: 68, height: 60, rx: 21}),
      svgNode('rect', {class: 'ai-robot-screen', x: 16, y: 25, width: 56, height: 46, rx: 15}),
      svgNode('path', {class: 'ai-robot-brows', d: {
        positive: 'M27 36h10 M51 36h10', negative: 'M27 35l10 3 M51 38l10-3',
        caution: 'M27 38l10-3 M51 35l10 3', neutral: 'M27 36h10 M51 36h10'
      }[mood]}),
      svgNode('circle', {class: 'ai-robot-eye', cx: 32, cy: 45, r: 3}),
      svgNode('circle', {class: 'ai-robot-eye', cx: 56, cy: 45, r: 3}),
      svgNode('path', {class: 'ai-robot-mouth', d: {
        positive: 'M31 55q13 14 26 0', negative: 'M31 64q13-14 26 0',
        caution: 'M31 59q7-6 13 0t13 0', neutral: 'M33 58h22'
      }[mood]})
    );
    face.append(svg);
    return face;
  }

  function loadingBot(message) {
    const loading = node('div', 'ai-bot-loading');
    const face = node('span', 'ai-bot-loading-face');
    const copy = node('span', 'ai-bot-loading-copy');
    const dots = node('span', 'ai-bot-loading-dots');
    face.append(robotFace('neutral', true));
    copy.append(node('strong', '', message));
    dots.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 3; i++) dots.append(node('i'));
    copy.append(dots);
    loading.append(face, copy);
    return loading;
  }

  function dateTime(value) {
    const date = new Date(value);
    return Number.isNaN(+date) ? 'Time unavailable' : date.toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata'
    }) + ' IST';
  }
  function sourceHref(source) {
    return stockUrl + '#' + (sections.has(source.section) ? source.section : 'overview');
  }
  function errorMessage(error, fallback) {
    return error && error.message ? error.message : fallback;
  }

  for (const id of ['nav-stock-details', 'hero-stock-details', 'footer-stock-details']) $(id).href = stockUrl;

  const themeButton = $('theme-toggle');
  function syncTheme() {
    themeButton.setAttribute('aria-label', 'Switch to ' + (document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark') + ' mode');
  }
  themeButton.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try { localStorage.setItem('daily-digest-theme', theme); } catch (error) {}
    syncTheme();
  });
  syncTheme();

  async function request(path) {
    if (path.startsWith('/api/stock-data?') && new URLSearchParams(path.split('?')[1]).get('section') === 'core') {
      try { const seed = $('company-bootstrap'); const payload = seed && JSON.parse(seed.textContent);
        if (payload && payload.ok && payload.symbol === symbol) return payload;
      } catch (error) { /* Fall back to the normal request if bootstrap data is invalid. */ }
    }
    const response = await fetch(path);
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || 'This overview is temporarily unavailable.');
    return payload;
  }

  function renderStory(response = aiResponse) {
    if (!response) return;
    $('ai-content').replaceChildren(window.tickrAIStory.render(response, companyCore, {
      robot: robotFace, sourceHref, stamp: dateTime
    }));
    $('ai-content').hidden = false;
    $('ai-facts').hidden = true;
  }

  function renderCore(response) {
    const core = response.data;
    if (!core || typeof core !== 'object') throw new Error('Company data is unavailable.');
    companyCore = core;
    const name = core.name || symbol.slice(3);
    $('company-name').textContent = name;
    $('company-symbol').textContent = symbol.slice(3);
    $('company-industry').textContent = core.industry || 'Indian equity';
    $('price-meta').textContent = 'Market data as of ' + (core.source_time || (response.fetched_at ? dateTime(response.fetched_at) : 'Time unavailable'));
    document.title = name + ' (' + symbol.slice(3) + ') AI Overview | Tickr Digest';
    $('ai-facts').replaceChildren(window.tickrAIStory.renderFacts(core));
    $('page-status').hidden = true;
    $('overview-content').hidden = false;
    renderStory();
  }

  function renderAI(response) {
    renderStory(response);
    aiResponse = response;
    const data = response.data;
    const sourceList = $('sources-list');
    sourceList.replaceChildren();
    for (const source of data.sources || []) {
      const item = node('li'), link = node('a', '', source.label);
      link.href = sourceHref(source);
      item.append(link, node('span', '', ' · ' + source.section));
      sourceList.append(item);
    }
    const coverage = response.coverage || {};
    $('ai-coverage').textContent = (coverage.sources || 0) + ' evidence groups · ' + (coverage.news_stories || 0) + ' available news stories · Cached for up to 6 hours';
    $('ai-status').hidden = true;
  }

  async function loadCore() {
    const status = $('page-status');
    status.textContent = 'Gathering company evidence…';
    status.hidden = false;
    try {
      const response = await request('/api/stock-data?' + new URLSearchParams({symbol, section: 'core'}));
      renderCore(response);
    } catch (error) {
      const retry = node('button', '', 'Try again');
      retry.type = 'button';
      retry.addEventListener('click', loadCore);
      status.replaceChildren(node('span', '', errorMessage(error, 'Company data is unavailable.')), retry);
    }
  }

  async function loadAI() {
    const status = $('ai-status');
    status.classList.remove('error');
    status.replaceChildren(loadingBot('Connecting the evidence…'));
    status.hidden = false;
    status.setAttribute('aria-busy', 'true');
    try {
      renderAI(await request('/api/stock-ai?' + new URLSearchParams({symbol, schema: '3', brief: window.tickrAIStory.contentVersion})));
    } catch (error) {
      const retry = node('button', '', 'Retry AI overview');
      retry.type = 'button';
      retry.addEventListener('click', loadAI);
      status.classList.add('error');
      status.replaceChildren(node('span', '', errorMessage(error, 'The AI overview is temporarily unavailable.')), retry);
    } finally { status.removeAttribute('aria-busy'); }
  }

  loadCore();
  loadAI();
})();
