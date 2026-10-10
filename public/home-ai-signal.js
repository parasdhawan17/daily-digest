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
      unavailable();
      return;
    }
    const stock = payload.stock;
    if (!/^IN:[A-Z][A-Z0-9.&-]{0,19}$/.test(stock.symbol)) throw new Error('Invalid stock');
    const path = '/stocks/' + encodeURIComponent(stock.symbol).replace('%3A', ':');
    const overview = payload.overview && payload.overview.data;
    const {number, money, pct, direction} = window.tickrStockFormat;
    if (!overview || !stock.name?.trim() || number(stock.price) === null
        || number(stock.percent_change) === null || !(number(stock.market_cap_crore) > 0)) {
      unavailable(); return;
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
    if (toolbarStatus) toolbarStatus.replaceChildren(tag);
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
      if (!story.children.length) { unavailable(); return; }
      storyHost.append(story);
    }
    const footer = node('div', 'preview-ai-footer');
    const link = node('a', '', 'Explore the full stock overview →'); link.href = path;
    footer.append(link);
    content.replaceChildren(company, storyHost, footer);
    const cap = Number(stock.market_cap_crore).toLocaleString('en-IN', {maximumFractionDigits: 0});
    caption.textContent = 'Market cap ₹' + cap + ' crore · Highest market cap among verified trending gainers. Provider data: ' + (stock.source_time || 'Unavailable') + '. Not investment advice.';
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 180000);
  fetch('/api/home-ai-signal?selection=market-cap-v1', {signal: controller.signal})
    .then(response => { if (!response.ok) throw new Error('Unavailable'); return response.json(); })
    .then(render)
    .catch(() => unavailable())
    .finally(() => { clearTimeout(timeout); host.setAttribute('aria-busy', 'false'); });
})();
