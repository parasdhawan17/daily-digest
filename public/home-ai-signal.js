(function () {
  'use strict';
  const host = document.getElementById('home-ai-signal');
  const content = document.getElementById('home-ai-content');
  const caption = document.getElementById('home-ai-caption');
  const toolbarStatus = document.getElementById('home-ai-toolbar-status');
  if (!host || !content || !caption) return;
  function node(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text) el.textContent = text;
    return el;
  }
  // A stable, explicitly illustrative tour using the stock page's real card renderer.
  function renderDemo() {
    const company = node('div', 'preview-company');
    company.append(node('h2', '', 'Example Technologies'), node('p', 'preview-kicker', 'DEMO · IT services · Illustrative figures'));
    const summary = node('div', 'preview-ai-summary');
    summary.append(node('h3', '', 'Revenue is growing. Keep an eye on margins.'),
      node('p', '', 'A quick view of where the company stands, what changed, and what to watch next.'));
    const demoCore = {
      prices: {NSE: 3200}, change_percent: 1.24, year_low: 2700, year_high: 3900,
      snapshot: {}, health: {groups: [{metrics: [{id: 'revenue', label: 'Revenue', value: 249,
        unit: '₹ cr', period: '2026-03-31', history: [
          {period: '2024-03-31', value: 210}, {period: '2025-03-31', value: 230}, {period: '2026-03-31', value: 249}
        ]}]}]}
    };
    const demoAI = {ok: true, data: {
      summary: {heading: 'Growth with a margin question', text: 'Illustrative company research.', tone: 'caution'},
      changes: [{heading: 'Revenue keeps moving up', tone: 'positive',
        text: 'In this demo, annual revenue rose from ₹230 crore to ₹249 crore. Higher sales show business growth; cash flow and costs help explain its quality.',
        evidence_ids: ['demo-financials'], facts: [{label: 'Revenue growth', value: '+8.3% YoY'}, {label: 'Annual revenue', value: '₹249 cr'}]}],
      watch_next: [{heading: 'Can profit margins recover?', tone: 'caution',
        text: 'In this demo, operating margin eased from 25.2% to 24.5%. The next results can show whether sales growth is translating into stronger profits.',
        evidence_ids: ['demo-financials'], facts: [{label: 'Operating margin', value: '24.5%'}, {label: 'Previous year', value: '25.2%'}]}],
      encouraging: [], attention: [], risks: [], catalysts: [],
      sources: [{id: 'demo-financials', section: 'financials', label: 'Illustrative financial data'}]
    }};
    const storyHost = node('div', 'home-ai-story-host stock-ai-overview-host home-demo-story');
    storyHost.append(window.tickrAIStory.render(demoAI, demoCore, {
      compact: true, hideEmpty: true, compactCharts: false, sourceHref: () => '#home-ai-caption'
    }));
    const footer = node('div', 'preview-ai-footer');
    const link = node('a', '', 'Try it with a company you follow →'); link.href = '#home-stock-query';
    footer.append(link, node('span', 'preview-ai-footer-note', 'Open a card to explore'));
    content.replaceChildren(company, summary, storyHost, footer);
    if (toolbarStatus) toolbarStatus.replaceChildren(node('span', 'preview-example', 'Interactive demo'));
    caption.textContent = 'Product demo · Fictional company and sample figures. Not live market data or investment advice.';
    host.setAttribute('aria-busy', 'false');
  }
  function unavailable() {
    const company = node('div', 'preview-company'), copy = node('div');
    copy.append(node('h2', '', 'Tata Consultancy Services'), node('p', 'preview-kicker', 'TCS · Technology · NSE'));
    company.append(copy);
    const summary = node('div', 'preview-ai-summary');
    summary.append(node('h3', '', 'Beyond the share price.'), node('p', '', 'What looks positive, what needs attention, and what to watch next.'));
    const signals = node('div', 'preview-signals');
    signals.setAttribute('aria-label', 'Illustrative AI signals');
    const examples = [
      ['positive', 'Looks positive', 'Steady cash flow', 'Cash from the business helps fund growth and dividends.', 'm4 16 6-6 4 4 6-8M14 6h6v6'],
      ['attention', 'Needs attention', 'Slower sales growth', 'Lower client spending could put pressure on revenue.', 'm12 3 9 17H3L12 3ZM12 9v4m0 3h.01'],
      ['next', 'Watch next', 'The next quarterly results', 'Look for changes in new orders and profit margins.', 'M4 5h16v16H4zM8 3v4m8-4v4M4 11h16m-12 5h3']
    ];
    examples.forEach(([tone, label, heading, text, path]) => {
      const card = node('article', 'preview-signal preview-signal-' + tone);
      const mark = node('span', 'preview-signal-icon'); mark.setAttribute('aria-hidden', 'true');
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      for (const [key, value] of Object.entries({viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.7', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'})) svg.setAttribute(key, value);
      const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'path'); arrow.setAttribute('d', path);
      svg.append(arrow); mark.append(svg);
      const body = node('div');
      body.append(node('span', 'preview-signal-label', label), node('h4', '', heading), node('p', '', text));
      card.append(mark, body); signals.append(card);
    });
    const footer = node('div', 'preview-ai-footer', 'Company data & news');
    footer.append(node('span', 'preview-ai-footer-note', 'Summarised by AI'));
    content.replaceChildren(company, summary, signals, footer);
    if (toolbarStatus) toolbarStatus.replaceChildren(node('span', 'preview-example', 'Example'));
    caption.textContent = 'Illustrative AI signals. Not a current assessment of TCS.';
  }
  function render(payload) {
    if (!payload.ok || !payload.stock) {
      return false;
    }
    const stock = payload.stock;
    if (!/^IN:[A-Z][A-Z0-9.&-]{0,19}$/.test(stock.symbol)) throw new Error('Invalid stock');
    const path = '/stocks/' + encodeURIComponent(stock.symbol).replace('%3A', ':');
    const overview = payload.overview && payload.overview.data;
    const {number, money, pct, direction} = window.tickrStockFormat;
    if (!overview || !stock.name?.trim() || number(stock.price) === null
        || number(stock.percent_change) === null || !(number(stock.market_cap_crore) > 0)) {
      return false;
    }
    const company = node('div', 'preview-company'), copy = node('div');
    const ticker = stock.symbol.slice(3);
    const meta = [stock.name.trim().toUpperCase() === ticker ? null : ticker,
      stock.industry || null, stock.exchange || null].filter(Boolean).join(' · ');
    const title = node('div', 'home-ai-company-title');
    title.append(node('h2', '', stock.name));
    const quote = node('div', 'home-ai-header-price ' + direction(stock.percent_change));
    quote.setAttribute('aria-label', 'Latest available price and daily change');
    if (number(stock.price) !== null) quote.append(node('strong', '', money(stock.price)));
    if (number(stock.percent_change) !== null) quote.append(node('span', '', pct(stock.percent_change)));
    if (quote.children.length) title.append(quote);
    copy.append(title, node('p', 'preview-kicker', meta));
    company.append(copy);
    const tag = node('span', 'home-ai-mover-tag', 'Highest market cap');
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('viewBox', '0 0 24 24'); icon.setAttribute('fill', 'none');
    icon.setAttribute('stroke', 'currentColor'); icon.setAttribute('stroke-width', '2');
    icon.setAttribute('aria-hidden', 'true');
    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    arrow.setAttribute('d', 'M4 17l6-6 4 4 6-10M14 5h6v6'); icon.append(arrow);
    tag.append(icon);
    const storyHost = node('div', 'home-ai-story-host stock-ai-overview-host');
    const visualCore = {...(payload.core || {}), name: stock.name, industry: stock.industry,
      prices: {[stock.exchange || 'BSE']: stock.price}, change_percent: stock.percent_change,
      snapshot: {...(payload.core?.snapshot || {}), marketCap: stock.market_cap_crore},
      source_time: stock.source_time};
    if (overview) {
      const story = window.tickrAIStory.render(payload.overview, visualCore, {
        compact: true, hideEmpty: true, compactCharts: true, signalLimit: 3,
        sourceHref: source => path + '#' + (['overview', 'financials', 'ownership', 'analysis', 'actions', 'news'].includes(source.section) ? source.section : 'overview')
      });
      if (!story.children.length) return false;
      storyHost.append(story);
    }
    const footer = node('div', 'preview-ai-footer');
    const link = node('a', '', 'Explore the full stock overview →'); link.href = path;
    footer.append(link);
    if (toolbarStatus) toolbarStatus.replaceChildren(tag);
    content.replaceChildren(company, storyHost, footer);
    const cap = Number(stock.market_cap_crore).toLocaleString('en-IN', {maximumFractionDigits: 0});
    caption.textContent = 'AI generated ' + new Date(overview.generated_at).toLocaleString() + ' · Market cap ₹' + cap + ' crore · Highest market cap among verified trending gainers. Provider data: ' + (stock.source_time || 'Unavailable') + '. Not investment advice.';
    return true;
  }
  const MAX_AGE = 48 * 60 * 60 * 1000;
  let displayedAt = null;
  function timestamp(payload) {
    try {
      const stock = payload.stock, data = payload.overview.data;
      const time = Date.parse(data.generated_at);
      const age = Date.now() - time;
      if (!payload.ok || !payload.overview.ok || !Number.isFinite(time) || age < 0 || age >= MAX_AGE
          || !stock.name?.trim() || !/^IN:[A-Z][A-Z0-9.&-]{0,19}$/.test(stock.symbol)) return null;
      for (const field of ['price', 'percent_change', 'market_cap_crore']) {
        if (typeof stock[field] === 'boolean' || window.tickrStockFormat.number(stock[field]) === null) return null;
      }
      if (!(window.tickrStockFormat.number(stock.market_cap_crore) > 0)) return null;
      const sources = new Set(data.sources.map(source => source.id));
      function valid(item, facts) {
        return item && item.heading?.trim() && item.text?.trim()
          && ['positive', 'negative', 'caution', 'neutral'].includes(item.tone)
          && Array.isArray(item.evidence_ids) && item.evidence_ids.length
          && item.evidence_ids.every(id => sources.has(id))
          && (!facts || Array.isArray(item.facts) && item.facts.length
            && item.facts.every(fact => fact.label?.trim() && fact.value?.trim()));
      }
      const categories = ['encouraging', 'attention', 'changes', 'catalysts', 'risks', 'watch_next'];
      if (!valid(data.summary, false) || !categories.every(key => Array.isArray(data[key]))) return null;
      const items = categories.flatMap(key => data[key]);
      return items.length && items.every(item => valid(item, true)) ? time : null;
    } catch (_) { return null; }
  }
  function accept(payload) {
    const time = timestamp(payload);
    if (time === null || displayedAt !== null && time < displayedAt) return;
    try {
      if (render(payload)) displayedAt = time;
    } catch (_) { /* Keep the visible card if rendering fails. */ }
  }
  if (host.dataset.preview === 'demo') {
    renderDemo();
    return;
  }
  unavailable();
  const snapshot = document.getElementById('home-ai-snapshot');
  try {
    const envelope = JSON.parse(snapshot?.textContent || 'null');
    if (envelope?.format_version === 1) accept(envelope.payload);
  } catch (_) { /* Use the labeled example. */ }
  host.setAttribute('aria-busy', 'false');
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && displayedAt !== null && Date.now() - displayedAt >= MAX_AGE) {
      unavailable(); displayedAt = null;
    }
  });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  fetch('/api/home-ai-signal?selection=market-cap-v1', {signal: controller.signal})
    .then(response => { if (!response.ok) throw new Error('Unavailable'); return response.json(); })
    .then(accept)
    .catch(() => {})
    .finally(() => clearTimeout(timeout));
})();
