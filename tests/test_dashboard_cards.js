const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const catalog = JSON.parse(fs.readFileSync('public/dashboard-catalog.json', 'utf8'));
const source = fs.readFileSync('public/dashboard-cards.js', 'utf8');
const styles = fs.readFileSync('public/dashboard-cards.css', 'utf8');
const template = fs.readFileSync('templates/web_digest.html', 'utf8');
const format = require('../public/stock-format.js');

test('dashboard cards expose the floating AI explainer flow', () => {
  assert.match(source, /dashboard-section-assistant/);
  assert.match(source, /Ask about any dashboard card/);
  assert.match(source, /fetch\('\/api\/stock-section-ai'/);
  assert.match(source, /node\.dataset\.aiCardId=meta\.id/);
  assert.match(source, /node\.dataset\.aiSymbol=symbol/);
  assert.match(source, /setTimeout\(function\(\)\{var selected=[\s\S]*\},600\)/);
  assert.match(source, /Math\.hypot\([\s\S]*>10/);
  assert.match(styles, /\.dashboard-section-assistant/);
  assert.match(styles, /\.stock-section-ai-launcher/);
  assert.match(styles, /env\(safe-area-inset-bottom\)/);
  assert.match(template, /dashboard-cards\.css\?v=20260927-shared-ai-overview/);
});

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.style = {setProperty() {}};
    this.classList = {add: name => { this.className = `${this.className || ''} ${name}`; }};
    this.childElementCount = 0;
  }
  append(...children) {
    children.forEach(child => { if (child instanceof Element) child.parent = this; });
    this.children.push(...children);
    this.childElementCount = this.children.filter(child => child instanceof Element).length;
  }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  querySelector(selector) {
    if (selector === '[aria-pressed=true]') return this.children.find(child => child.attributes?.['aria-pressed'] === 'true');
    if (selector === '[data-indian-dashboard]') return this.children.find(child => child.dataset?.symbol);
    return null;
  }
  addEventListener() {}
  click() { if (this.onclick) this.onclick(); }
  remove() { if (this.parent) { this.parent.children = this.parent.children.filter(child => child !== this); this.parent.childElementCount = this.parent.children.filter(child => child instanceof Element).length; this.parent = null; } }
}

function descendants(node, predicate) {
  return (node.children || []).flatMap(child => child instanceof Element
    ? [...(predicate(child) ? [child] : []), ...descendants(child, predicate)] : []);
}

function mockData(section, params) {
  if (section === 'core') return {
    snapshot: {marketCap: 10, pPerEBasicExcludingExtraordinaryItemsTTM: 12, currentDividendYieldCommonStockPrimaryIssueLTM: 1, priceYTDPricePercentChange: 2, high: 10, low: 8, close: 9, price5DayPercentChange: -1},
    year_low: 5, year_high: 15, prices: {NSE: 10, BSE: 9},
    profile: {companyDescription: 'Company profile', industry: 'Technology', officers: {officer: [{firstName: 'A', lastName: 'B', title: {Value: 'CEO'}}]}},
    health: {end_date: '2026-06-30', groups: [{title: 'Growth', metrics: [{id: 'revenue', label: 'Revenue', value: 20, unit: '₹ cr', change_label: '+2%', value_tone: 'positive'}]}, {title: 'Profitability', metrics: [{id: 'margin', label: 'Margin', value: 20}]}, {title: 'Balance sheet', metrics: [{id: 'debt', label: 'Debt', value: 10}]}, {title: 'Cash generation', metrics: [{id: 'fcf', label: 'Free cash flow', value: 5}]}]},
    financials: [{Type: 'Annual', EndDate: '2026-06-30', stockFinancialMap: {INC: [{key: 'Revenue', value: 20}], BAL: [{key: 'Assets', value: 40}], CAS: [{key: 'CashFlow', value: 5}]}}],
    ownership: [{displayName: 'Promoter', categoryName: 'Promoter', categories: [{holdingDate: '2026-06-30', percentage: 30}]}],
    peers: [{symbol: 'IN:TCS', companyName: 'TCS', price: 10}],
    ratings: [{ratingName: 'Buy', ratingValue: 1, numberOfAnalystsLatest: 3}], recommendations: {Buy: 3},
    technical: [{days: 50, nsePrice: 8}], risk: {categoryName: 'Low', stdDev: 12.4}, futures: {expiryDates: ['2026-09']}, actions: {dividend: [{remarks: 'Dividend', xdDate: '2026-08-01'}], bonus: [{remarks: 'Bonus'}], rights: [{remarks: 'Rights'}], splits: [{remarks: 'Split'}], annualGeneralMeeting: [{remarks: 'AGM'}], boardMeetings: [{remarks: 'Board meeting'}]},
    metrics: {growth: [{key: 'Revenue', value: 20}]}, additional_financials: {cash: 4},
    news: [{headline: 'Company news', source: 'Example', date: '2026-09-01', url: 'https://example.com/story'}]
  };
  if (section === 'financials') return {Sales: {'Jun 2025': 10, 'Jun 2026': 20}, Expenses: {'Jun 2025': 5, 'Jun 2026': 9}};
  if (section === 'history' && params.get('filter') === 'pe') return {datasets: [{metric: 'PE', label: 'P/E', values: [['2026-01-01', '10'], ['2026-02-01', 14], ['2026-03-01', 12]]}]};
  if (section === 'history') return {datasets: [{metric: 'Price', label: 'Price', values: [['2026-01-01', 10], ['2026-02-01', 12]]}]};
  return {};
}

test('every selectable Indian dashboard card renders without a fallback or exception', async () => {
  const selected = catalog.categories.flatMap(category => category.cards.map(card => card.id));
  const root = new Element(); root.dataset.symbol = 'IN:INFY';
  const section = new Element(); section.append(root);
  const container = new Element(); container.dataset.dashboardCards = JSON.stringify(selected);
  const document = {
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
    createTextNode: text => String(text),
    querySelectorAll: selector => selector === '.ticker-section' ? [section] : [],
    getElementById: id => id === 'digest-sections' ? container : null
  };
  const requested = [];
  const context = {document, Node: Element, URL, URLSearchParams, Intl, Map, Set, Array, Object, Number, String, Date, Math, console,
    window: {tickrStockFormat: format},
    fetch: async url => {
      requested.push(url);
      return {json: async () => url === '/dashboard-catalog.json' ? catalog
        : url.startsWith('/api/stock-ai') ? {ok: true, data: {summary: {heading: 'Summary', text: 'Text', tone: 'positive'}, encouraging: [], attention: [], changes: [], catalysts: [], risks: [], watch_next: [], sources: [], generated_at: '2026-09-01'}}
        : {ok: true, data: mockData(new URL(url, 'https://example.test').searchParams.get('section'), new URL(url, 'https://example.test').searchParams)}};
    }
  };
  vm.runInNewContext(source, context);
  for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve));
  const tabs = descendants(root, node => node.className?.split(/\s+/).includes('dashboard-category-tab'));
  assert.equal(tabs.length, catalog.categories.length, JSON.stringify(root.children.map(child => child.textContent || child.className)));
  for (const tab of tabs) {
    tab.onclick();
    for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve));
  }
  const cards = descendants(root, node => node.tagName === 'ARTICLE' && node.dataset.card);
  const selectedNonAI = selected.filter(id => !id.startsWith('ai_'));
  assert.deepEqual(cards.map(card => card.dataset.card).sort(), selectedNonAI.sort());
  const card = id => cards.find(node => node.dataset.card === id);
  assert.ok(descendants(root, node => node.className === 'ai-insight-explorer').length);
  assert.ok(descendants(root, node => node.className === 'ai-summary').length);
  assert.ok(descendants(card('financial_quarterly_results'), node => node.attributes?.class === 'stock-chart').length);
  assert.ok(descendants(card('ownership_current_mix'), node => node.className === 'dashboard-stacked-bar').length);
  assert.ok(descendants(card('overview_pe_history'), node => node.className === 'dashboard-metrics').length);
  assert.ok(descendants(card('overview_pe_history'), node => node.attributes?.class === 'pe-median-line').length);
  assert.ok(descendants(card('news_company_coverage'), node => node.className === 'dashboard-news-card').length);
  assert.equal(requested.some(url => /section=(targets|forecasts)/.test(url)), false);
  assert.equal(descendants(root, node => node.className === 'dashboard-card-state' && /is not defined|cannot read|could not load/i.test(node.textContent || '')).length, 0);
});

test('P/E history shimmers until its filtered history request settles', async () => {
  const root = new Element(); root.dataset.symbol = 'IN:INFY';
  const section = new Element(); section.append(root);
  const container = new Element(); container.dataset.dashboardCards = JSON.stringify(['overview_pe_history']);
  let resolveHistory;
  const history = new Promise(resolve => { resolveHistory = resolve; });
  const document = {
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
    createTextNode: text => String(text),
    querySelectorAll: selector => selector === '.ticker-section' ? [section] : [],
    getElementById: id => id === 'digest-sections' ? container : null
  };
  vm.runInNewContext(source, {document, Node: Element, URL, URLSearchParams, Intl, Map, Set, Array, Object, Number, String, Date, Math, console,
    window: {tickrStockFormat: format},
    fetch: url => url === '/dashboard-catalog.json' ? Promise.resolve({json: async () => catalog})
      : url.includes('section=history') ? history
      : Promise.resolve({json: async () => ({ok: true, data: mockData('core')})})});
  for (let i = 0; i < 4; i++) await new Promise(resolve => setImmediate(resolve));
  const card = descendants(root, node => node.dataset.card === 'overview_pe_history')[0];
  assert.ok(card);
  assert.equal(descendants(card, node => node.className === 'dashboard-shimmer').length, 1);
  resolveHistory({json: async () => ({ok: true, data: mockData('history', new URLSearchParams('filter=pe'))})});
  for (let i = 0; i < 4; i++) await new Promise(resolve => setImmediate(resolve));
  assert.equal(descendants(card, node => node.className === 'dashboard-shimmer').length, 0);
  assert.equal(descendants(card, node => node.className === 'dashboard-metrics').length, 1);
});

test('empty P/E history removes the card and reports no factual data', async () => {
  const root = new Element(); root.dataset.symbol = 'IN:SPARSE';
  const section = new Element(); section.append(root);
  const container = new Element(); container.dataset.dashboardCards = JSON.stringify(['overview_pe_history']);
  const document = {
    createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag),
    createTextNode: text => String(text), querySelectorAll: selector => selector === '.ticker-section' ? [section] : [],
    getElementById: id => id === 'digest-sections' ? container : null
  };
  vm.runInNewContext(source, {document, Node: Element, URL, URLSearchParams, Intl, Map, Set, Array, Object, Number, String, Date, Math, console,
    window: {tickrStockFormat: format},
    fetch: url => Promise.resolve({json: async () => url === '/dashboard-catalog.json' ? catalog
      : {ok: true, data: url.includes('section=history') ? {datasets: []} : mockData('core')}})});
  for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve));
  assert.equal(descendants(root, node => node.dataset.card === 'overview_pe_history').length, 0);
  assert.equal(descendants(root, node => node.className === 'dashboard-card-state' && /No reported data/.test(node.textContent || '')).length, 1);
});
