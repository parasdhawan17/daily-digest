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

  function signal(item, sources) {
    const tone = Object.hasOwn(tones, item.tone) ? item.tone : 'neutral';
    const card = node('article', 'ai-signal ' + tone);
    const head = node('div', 'ai-signal-head');
    head.append(node('span', 'ai-signal-title', item.heading || 'Company signal'), node('span', 'ai-tone', tones[tone]));
    const body = node('p', '', item.text || '');
    body.append(citations(item.evidence_ids, sources));
    card.append(head, body);
    return card;
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
        items.forEach(item => { const row = node('li'); row.append(signal(item, sources)); list.append(row); });
        group.append(list);
      } else group.append(node('p', 'ai-empty', 'No supported insight in the available evidence.'));
      container.append(group);
    });
    $('ai-signal-count').textContent = total + ' supported ' + (total === 1 ? 'signal' : 'signals') + ' across ' + categories.length + ' areas';

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
