(function () {
  'use strict';

  const symbol = document.body.dataset.symbol;
  if (!/^IN:[A-Z][A-Z0-9&-]{0,19}$/.test(symbol || '')) return;

  const $ = id => document.getElementById(id);
  const {number, fmt, money, pct, direction} = window.tickrStockFormat;
  const stockUrl = '/stocks/' + encodeURIComponent(symbol).replace('%3A', ':');
  const sections = new Set(['overview', 'financials', 'ownership', 'analysis', 'actions', 'news']);
  const categories = [
    ['encouraging', 'What looks encouraging'],
    ['attention', 'What needs attention'],
    ['changes', 'What changed recently'],
    ['catalysts', 'Potential catalysts'],
    ['risks', 'Key risks'],
    ['watch_next', 'What to watch next'],
  ];
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

  function present(value) { return number(value) !== null; }
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

  for (const id of ['nav-stock-details', 'footer-stock-details']) $(id).href = stockUrl;

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
    const response = await fetch(path);
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || 'This overview is temporarily unavailable.');
    return payload;
  }

  function metric(label, value, note) {
    const card = node('article', 'ai-metric');
    card.append(node('span', 'ai-metric-label', label), node('strong', 'ai-metric-value', value));
    if (note) {
      const annotation = node('span', 'ai-metric-note', note);
      if (/^\+/.test(note)) annotation.classList.add('positive');
      if (/^[−-]/.test(note)) annotation.classList.add('negative');
      card.append(annotation);
    }
    return card;
  }

  function healthMetric(core, pattern) {
    for (const group of (core.health && core.health.groups) || []) {
      for (const entry of group.metrics || []) {
        if (pattern.test(entry.label || '') && present(entry.value)) return entry;
      }
    }
    return null;
  }

  function renderRange(core, price) {
    const card = $('range-card');
    const low = number(core.year_low), high = number(core.year_high);
    if (low === null || high === null || high <= low || price === null) { card.hidden = true; return; }
    const position = Math.max(0, Math.min(100, (price - low) / (high - low) * 100));
    const head = node('div', 'ai-range-head');
    head.append(node('strong', '', '52-week price range'), node('span', '', 'Current position ' + Math.round(position) + '% of range'));
    const track = node('div', 'ai-range-track');
    const marker = node('span', 'ai-range-marker');
    marker.style.left = position + '%';
    track.append(marker);
    const labels = node('div', 'ai-range-labels');
    labels.append(node('span', '', money(low) + ' low'), node('span', '', money(high) + ' high'));
    card.replaceChildren(head, track, labels);
    card.hidden = false;
  }

  function renderCore(response) {
    const core = response.data;
    if (!core || typeof core !== 'object') throw new Error('Company data is unavailable.');
    const name = core.name || symbol.slice(3);
    const prices = core.prices || {};
    const exchange = present(prices.NSE) ? 'NSE' : present(prices.BSE) ? 'BSE' : '';
    const price = exchange ? number(prices[exchange]) : null;
    $('company-name').textContent = name;
    $('company-symbol').textContent = symbol.slice(3);
    $('company-industry').textContent = core.industry || 'Indian equity';
    $('company-price').textContent = price === null ? '—' : money(price);
    $('price-meta').textContent = exchange ? exchange + ' · Market data may be delayed' : 'Price unavailable';
    document.title = name + ' AI Overview — Tickr Digest';
    const change = $('company-change');
    change.hidden = !present(core.change_percent);
    if (!change.hidden) {
      change.textContent = pct(core.change_percent) + ' today';
      change.className = 'ai-change ' + direction(core.change_percent);
    }

    const snapshot = core.snapshot || {};
    const grid = $('metrics-grid');
    grid.replaceChildren();
    if (present(snapshot.marketCap)) grid.append(metric('Market cap', '₹' + fmt(snapshot.marketCap) + ' cr', 'Provider-reported'));
    if (present(snapshot.pPerEBasicExcludingExtraordinaryItemsTTM)) grid.append(metric('P/E ratio', fmt(snapshot.pPerEBasicExcludingExtraordinaryItemsTTM) + '×', 'Trailing 12 months'));
    if (present(snapshot.sectorPriceToEarningsValueRatio)) grid.append(metric('Sector P/E', fmt(snapshot.sectorPriceToEarningsValueRatio) + '×', 'Provider-reported'));
    if (present(snapshot.priceYTDPricePercentChange)) grid.append(metric('Year-to-date return', pct(snapshot.priceYTDPricePercentChange), 'Price return'));
    const revenue = healthMetric(core, /^(revenue|sales|total income)$/i);
    const profit = healthMetric(core, /^(net (income|profit)|profit after tax)$/i);
    for (const entry of [revenue, profit]) {
      if (!entry) continue;
      const value = (entry.unit || '').trim() === '₹ cr' ? '₹' + fmt(entry.value) + ' cr' : fmt(entry.value) + (entry.unit ? ' ' + entry.unit : '');
      grid.append(metric(entry.label, value, [entry.period, entry.change_label].filter(Boolean).join(' · ') || 'Reported actual'));
    }
    if (!grid.children.length) grid.append(node('p', 'ai-empty', 'No comparable market or financial measures are available for this company.'));
    renderRange(core, price);
    $('data-freshness').textContent = 'IndianAPI · ' + (core.source_time || 'Retrieved ' + dateTime(response.fetched_at));
    $('page-status').hidden = true;
    $('overview-content').hidden = false;
  }

  function citations(ids, sources) {
    const wrap = node('span', 'ai-evidence');
    for (const id of ids || []) {
      const source = sources.get(id);
      if (!source) continue;
      const link = node('a', '', id);
      link.href = sourceHref(source);
      link.title = 'View source: ' + source.label;
      link.setAttribute('aria-label', id + ': ' + source.label);
      wrap.append(link);
    }
    return wrap;
  }

  function signal(item, sources, onSelect) {
    const tone = Object.hasOwn(tones, item.tone) ? item.tone : 'neutral';
    const card = node('article', 'ai-signal ' + tone);
    const button = node('button', 'ai-signal-select');
    button.type = 'button';
    button.setAttribute('aria-label', 'Read ' + (item.heading || 'company signal') + ', ' + tones[tone].toLowerCase() + ' insight');
    button.setAttribute('aria-pressed', 'false');
    const head = node('span', 'ai-signal-head');
    head.append(node('span', 'ai-signal-title', item.heading || 'Company signal'), node('span', 'ai-tone', tones[tone]));
    button.append(robotFace(tone), head);
    button.addEventListener('click', onSelect);
    const body = node('p', '', item.text || '');
    body.append(citations(item.evidence_ids, sources));
    card.append(button, body);
    return {card, button};
  }

  function renderAI(response) {
    const data = response.data;
    if (!data || !data.summary || !data.summary.text) throw new Error('The AI overview could not be read.');
    const sources = new Map((data.sources || []).map(item => [item.id, item]));
    const summary = $('ai-summary');
    const summaryBody = node('p', '', data.summary.text);
    summaryBody.append(citations(data.summary.evidence_ids, sources));
    const summaryCopy = node('div', 'ai-summary-copy');
    summaryCopy.append(node('span', 'ai-summary-label', '✦ The AI take'), node('h2', '', data.summary.heading || 'Company perspective'), summaryBody);
    summary.replaceChildren(summaryCopy);

    const container = $('ai-categories');
    container.replaceChildren();
    const guide = $('ai-robot-guide'), guideFace = $('ai-robot-guide-face');
    const reading = $('ai-robot-reading'), toneLabel = $('ai-robot-tone');
    const selectable = [];
    function selectInsight(selectedIndex) {
      selectable.forEach(({card, button}, index) => {
        card.classList.toggle('is-selected', index === selectedIndex);
        button.setAttribute('aria-pressed', String(index === selectedIndex));
      });
      const item = selectable[selectedIndex]?.item;
      const tone = item && Object.hasOwn(tones, item.tone) ? item.tone : 'neutral';
      guide.dataset.tone = tone;
      guideFace.replaceChildren(robotFace(tone, true));
      reading.textContent = item ? item.heading || 'Company signal' : 'No supported signal yet';
      toneLabel.textContent = item ? ({positive: 'Encouraging evidence', negative: 'Needs attention',
        caution: 'Mixed or uncertain', neutral: 'Monitoring point'})[tone] : 'Awaiting evidence';
    }
    let total = 0;
    categories.forEach(([key, label]) => {
      const items = Array.isArray(data[key]) ? data[key] : [];
      total += items.length;
      const group = node('section', 'ai-category');
      const heading = node('h3', '', label);
      heading.append(node('span', 'ai-category-count', String(items.length)));
      group.append(heading);
      if (items.length) {
        const list = node('ul');
        items.forEach(item => {
          const row = node('li'), index = selectable.length;
          const insight = signal(item, sources, () => selectInsight(index));
          selectable.push({...insight, item});
          row.append(insight.card);
          list.append(row);
        });
        group.append(list);
      } else group.append(node('p', 'ai-empty', 'No supported insight in the available evidence.'));
      container.append(group);
    });
    $('ai-signal-count').textContent = total + ' supported ' + (total === 1 ? 'signal' : 'signals') + ' across ' + categories.length + ' areas';
    selectInsight(0);

    const sourceList = $('sources-list');
    sourceList.replaceChildren();
    for (const source of data.sources || []) {
      const item = node('li');
      const link = node('a', '', source.label);
      link.href = sourceHref(source);
      item.append(link, node('span', '', ' · ' + source.section));
      sourceList.append(item);
    }
    $('ai-generated').textContent = 'Generated ' + dateTime(data.generated_at);
    const coverage = response.coverage || {};
    $('ai-coverage').textContent = fmt(coverage.sources) + ' evidence groups · ' + fmt(coverage.news_stories) + ' available news stories · Cached for up to 6 hours';
    $('ai-status').hidden = true;
    $('ai-content').hidden = false;
  }

  async function loadCore() {
    const status = $('page-status');
    status.textContent = 'Gathering company evidence…';
    status.hidden = false;
    try {
      renderCore(await request('/api/stock-data?' + new URLSearchParams({symbol, section: 'core'})));
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
    status.textContent = 'Connecting the evidence…';
    status.hidden = false;
    status.setAttribute('aria-busy', 'true');
    try {
      renderAI(await request('/api/stock-ai?' + new URLSearchParams({symbol, schema: '2'})));
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
