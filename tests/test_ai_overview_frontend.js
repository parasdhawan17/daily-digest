const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/ai-overview.js', 'utf8');
const template = fs.readFileSync('templates/ai_overview.html', 'utf8');
const stockFormat = require('../public/stock-format.js');

class Element {
  constructor(tagName = '') {
    this.tagName = tagName;
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this.hidden = false;
    this.style = {};
    this.dataset = {};
    this._text = '';
    this.className = '';
    this.classList = {
      add: name => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), name])].join(' '); },
      remove: name => { this.className = this.className.split(/\s+/).filter(value => value && value !== name).join(' '); },
      toggle: (name, force) => {
        const has = this.className.split(/\s+/).includes(name);
        if (force === undefined ? !has : force) this.classList.add(name);
        else this.classList.remove(name);
      }
    };
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  fire(type, event = {}) { this.listeners[type]?.(event); }
  focus() { this.focused = true; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ''; this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
}

const ids = [
  'nav-stock-details', 'hero-stock-details', 'footer-stock-details', 'theme-toggle',
  'company-name', 'company-symbol', 'company-industry', 'company-price', 'company-change',
  'price-meta', 'metrics-grid', 'range-card', 'page-status',
  'overview-content', 'ai-status', 'ai-content', 'ai-summary', 'ai-categories', 'ai-signal-count',
  'ai-robot-guide', 'ai-robot-guide-face', 'ai-robot-tone',
  'sources-list', 'ai-generated', 'ai-coverage'
];

function core(overrides = {}) {
  return {ok: true, data: {
    name: 'Example Ltd', industry: 'Software', prices: {NSE: 100, BSE: null},
    change_percent: 1.5, year_low: 70, year_high: 120,
    snapshot: {marketCap: 5000, pPerEBasicExcludingExtraordinaryItemsTTM: 24},
    health: {groups: [{metrics: [{label: 'Revenue', value: 900, unit: '₹ cr', period: 'FY2026', change_label: '+12% YoY'}]}]},
    ...overrides
  }, fetched_at: '2026-09-25T04:00:00Z'};
}

function ai() {
  return {ok: true, data: {
    summary: {heading: 'Revenue is growing', text: 'Revenue rose in the reported period.', tone: 'positive', evidence_ids: ['S1']},
    encouraging: [{heading: 'Revenue momentum', text: 'Revenue rose.', tone: 'positive', evidence_ids: ['S1'],
      facts: [{label: 'Revenue', value: '+12% YoY'}, {label: 'Operating cash', value: '+6.5%'}]}],
    attention: [], changes: [], catalysts: [], risks: [], watch_next: [],
    sources: [{id: 'S1', section: 'financials', label: 'Reported financial health'}],
    generated_at: '2026-09-25T05:00:00Z'
  }, coverage: {sources: 1, news_stories: 0}};
}

function history() {
  return {ok: true, data: {datasets: [
    {metric: 'Price', values: [['2020-01-01', 90], ['2026-01-01', 150], ['2026-09-01', 110]]},
    {metric: 'Volume', values: [['2026-01-01', 900000]]}
  ]}};
}

async function setup(corePayload, aiResponses, historyResponse = history()) {
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  elements['overview-content'].hidden = true;
  elements['ai-content'].hidden = true;
  elements['range-card'].hidden = true;
  let aiCalls = 0;
  const calls = [];
  const document = {
    body: {dataset: {symbol: 'IN:EXAMPLE'}},
    documentElement: {dataset: {theme: 'light'}, style: {}},
    getElementById: id => elements[id],
    createElement: tag => new Element(tag),
    createElementNS: (_namespace, tag) => new Element(tag),
    title: ''
  };
  const context = {
    document, window: {tickrStockFormat: stockFormat}, URLSearchParams,
    fetch: async url => {
      calls.push(url);
      if (url.includes('section=history')) return {ok: historyResponse.ok, json: async () => historyResponse};
      if (url.startsWith('/api/stock-data?')) return {ok: true, json: async () => corePayload};
      const response = aiResponses[Math.min(aiCalls++, aiResponses.length - 1)];
      return {ok: response.ok, json: async () => response};
    }
  };
  vm.runInNewContext(source, context);
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  return {elements, calls, get aiCalls() { return aiCalls; }, async flush() {
    await new Promise(setImmediate);
    await new Promise(setImmediate);
  }};
}

test('renders available metrics and links AI citations to stock evidence', async () => {
  const app = await setup(core(), [ai()]);
  const e = app.elements;
  assert.equal(e['overview-content'].hidden, false);
  assert.match(app.calls[0], /^\/api\/stock-data\?symbol=IN%3AEXAMPLE&section=core$/);
  assert.match(app.calls[1], /^\/api\/stock-ai\?symbol=IN%3AEXAMPLE&schema=3$/);
  assert.equal(e['company-name'].textContent, 'Example Ltd');
  assert.match(e['price-meta'].textContent, /^NSE · As of 25 Sep(?:t)? 2026/);
  assert.doesNotMatch(e['price-meta'].textContent, /IndianAPI/);
  assert.equal(e['metrics-grid'].children.length, 3);
  assert.equal(e['range-card'].hidden, false);
  const labels = e['range-card'].children[1].children[1].children;
  assert.deepEqual(labels.map(label => label.children.map(part => part.textContent)), [
    ['₹70.00', '52-week low'], ['₹120.00', '52-week high'], ['₹150.00', 'All-time high']
  ]);
  const landmarks = e['range-card'].children[1].children[0].children;
  assert.equal(landmarks[0].attributes.title, '52-week high ₹120.00');
  assert.equal(landmarks[0].style.left, '62.5%');
  assert.equal(landmarks[1].attributes.title, 'All-time high ₹150.00');
  assert.equal(landmarks[1].style.left, '100%');
  assert.equal(landmarks[2].style.left, '37.5%');
  assert.ok(app.calls.some(url => url.includes('section=history&period=max&filter=price')));
  assert.equal(e['ai-content'].hidden, false);
  assert.equal(e['nav-stock-details'].href, '/stocks/IN:EXAMPLE');
  assert.equal(e['ai-summary'].children[1].children[2].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.equal(e['ai-summary'].children.length, 2);
  assert.equal(e['ai-categories'].children.length, 1);
  assert.equal(e['ai-categories'].hidden, false);
  assert.equal(e['ai-signal-count'].textContent, '1 supported signal across 1 area');
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'positive');
  assert.equal(e['ai-summary'].dataset.tone, 'positive');
  assert.equal(e['ai-summary'].children[1].children[1].textContent, 'Revenue is growing');
  const facts = e['ai-categories'].children[0].children[1].children[0].children[0].children[1];
  assert.equal(facts.className, 'ai-signal-facts');
  assert.equal(facts.children.length, 2);
  assert.equal(facts.textContent, 'Revenue+12% YoYOperating cash+6.5%');
  assert.equal(e['sources-list'].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.match(e['ai-generated'].textContent, /Generated 25 Sep(?:t)? 2026/);
});

test('shows the company summary followed by supported signal groups', () => {
  assert.doesNotMatch(template, /ai-signal-board|ai-signal-bar|ai-signal-counts/);
  assert.match(template, /id="ai-signal-count"[\s\S]*id="ai-categories"/);
  assert.doesNotMatch(template, /Explore the synthesis|Signals and what to watch|signals-title/);
  assert.match(template, /id="ai-categories" class="ai-categories" role="group" aria-label="AI signals"/);
  assert.match(template, /id="ai-robot-guide"/);
  assert.doesNotMatch(template, /id="ai-robot-reading"|class="ai-robot-reading"/);
  assert.doesNotMatch(template, /role="tablist"|id="ai-active-panel"/);
  assert.match(template, /<article id="ai-summary" class="ai-summary"><aside id="ai-robot-guide"[\s\S]*<\/aside><\/article>/);
  assert.ok(template.indexOf('id="ai-robot-guide"') < template.indexOf('class="ai-insight-body"'));
  assert.doesNotMatch(template, /id="metrics-title"|>Market facts<\/h2>/);
  assert.match(template, /<header class="ai-company-bar">[\s\S]*<section class="ai-metrics-section"[\s\S]*id="range-card"[\s\S]*<\/section>\s*<\/header>/);
  assert.ok(template.indexOf('class="ai-metrics-section"') < template.indexOf('id="ai-insights"'));
  assert.match(template, /class="ai-insight-explorer">\s*<article id="ai-summary" class="ai-summary">[\s\S]*<\/article>\s*<div class="ai-insight-body">/);
});

test('nonempty signal groups remain visible with source citations', async () => {
  const result = ai();
  result.data.summary = {...result.data.summary, heading: 'Mixed outlook overall', tone: 'caution'};
  result.data.risks = [{heading: 'Execution risk', text: 'A risk was reported.', tone: 'negative', evidence_ids: ['S1'],
    facts: [{label: 'Risk level', value: 'Elevated'}]}];
  const app = await setup(core(), [result]);
  const e = app.elements;
  assert.equal(e['ai-categories'].children.length, 2);
  assert.match(e['ai-categories'].textContent, /Revenue momentum/);
  assert.match(e['ai-categories'].textContent, /Execution risk/);
  assert.equal(e['ai-signal-count'].textContent, '2 supported signals across 2 areas');
  const risk = e['ai-categories'].children[1].children[1].children[0].children[0];
  assert.equal(risk.children[2].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'caution');
  assert.equal(e['ai-summary'].dataset.tone, 'caution');
  assert.equal(e['ai-robot-tone'].textContent, 'Mixed or uncertain');
  assert.match(e['ai-categories'].textContent, /Revenue momentum/);
});

test('no empty signal grid appears when only the summary is supported', async () => {
  const result = ai();
  result.data.encouraging = [];
  const app = await setup(core(), [result]);
  assert.equal(app.elements['ai-categories'].children.length, 0);
  assert.equal(app.elements['ai-categories'].hidden, true);
  assert.equal(app.elements['ai-signal-count'].textContent, 'No supported signals in the available evidence.');
});

test('multiple insights in a group render together', async () => {
  const result = ai();
  result.data.encouraging.push({heading: 'Mixed outlook', text: 'Evidence is mixed.', tone: 'caution', evidence_ids: ['S1'],
    facts: [{label: 'Signal', value: 'Mixed'}]});
  const app = await setup(core(), [result]);
  const e = app.elements;
  const rows = e['ai-categories'].children[0].children[1].children;
  assert.equal(rows.length, 2);
  assert.match(rows[0].textContent, /Revenue momentum/);
  assert.match(rows[1].textContent, /Mixed outlook/);
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'positive');
});

test('omits unavailable numbers and the price range', async () => {
  const app = await setup(core({prices: {NSE: null, BSE: null}, change_percent: null,
    year_low: null, year_high: null, snapshot: {}, health: null}), [ai()], {ok: true, data: {datasets: []}});
  const e = app.elements;
  assert.equal(e['company-price'].textContent, '—');
  assert.equal(e['company-change'].hidden, true);
  assert.equal(e['range-card'].hidden, true);
  assert.equal(e['metrics-grid'].children.length, 1);
  assert.match(e['metrics-grid'].textContent, /No comparable market/);
});

test('AI failure preserves factual metrics and retry renders the summary', async () => {
  const app = await setup(core(), [{ok: false, error: 'The AI overview is temporarily unavailable.'}, ai()]);
  const e = app.elements;
  assert.equal(e['overview-content'].hidden, false);
  assert.equal(e['metrics-grid'].children.length, 3);
  assert.equal(e['ai-content'].hidden, true);
  assert.match(e['ai-status'].textContent, /temporarily unavailable/);
  e['ai-status'].children[1].fire('click');
  await app.flush();
  assert.equal(app.aiCalls, 2);
  assert.equal(e['ai-content'].hidden, false);
});
