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
  'price-meta', 'metrics-grid', 'range-card', 'data-freshness', 'page-status',
  'overview-content', 'ai-status', 'ai-content', 'ai-summary', 'ai-categories',
  'ai-active-panel', 'ai-robot-guide', 'ai-robot-guide-face', 'ai-robot-reading', 'ai-robot-tone',
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
    encouraging: [{heading: 'Revenue momentum', text: 'Revenue rose.', tone: 'positive', evidence_ids: ['S1']}],
    attention: [], changes: [], catalysts: [], risks: [], watch_next: [],
    sources: [{id: 'S1', section: 'financials', label: 'Reported financial health'}],
    generated_at: '2026-09-25T05:00:00Z'
  }, coverage: {sources: 1, news_stories: 0}};
}

async function setup(corePayload, aiResponses) {
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
  assert.match(app.calls[1], /^\/api\/stock-ai\?symbol=IN%3AEXAMPLE&schema=2$/);
  assert.equal(e['company-name'].textContent, 'Example Ltd');
  assert.equal(e['metrics-grid'].children.length, 3);
  assert.equal(e['range-card'].hidden, false);
  assert.equal(e['ai-content'].hidden, false);
  assert.equal(e['nav-stock-details'].href, '/stocks/IN:EXAMPLE');
  assert.equal(e['ai-summary'].children[0].children[2].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.equal(e['ai-summary'].children.length, 1);
  assert.equal(e['ai-categories'].children.length, 6);
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'positive');
  assert.equal(e['sources-list'].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.match(e['ai-generated'].textContent, /Generated 25 Sep(?:t)? 2026/);
});

test('removes only the color bar card and keeps the signals explorer', () => {
  assert.doesNotMatch(template, /ai-signal-board|ai-signal-bar|ai-signal-counts/);
  assert.match(template, /class="ai-insight-heading"[^>]*>[\s\S]*id="ai-robot-guide"[\s\S]*id="ai-categories"/);
  assert.match(template, /<article id="ai-summary" class="ai-summary"><\/article>/);
  assert.match(template, /id="metrics-title">Market facts/);
  assert.ok(template.indexOf('class="ai-company-bar"') < template.indexOf('id="metrics-title"'));
  assert.ok(template.indexOf('id="metrics-title"') < template.indexOf('id="ai-insights"'));
  assert.match(template, /class="ai-insight-explorer">\s*<article id="ai-summary" class="ai-summary"><\/article>\s*<div class="ai-insight-body">/);
});

test('signal tabs support keyboard navigation and source citations', async () => {
  const result = ai();
  result.data.risks = [{heading: 'Execution risk', text: 'A risk was reported.', tone: 'negative', evidence_ids: ['S1']}];
  const app = await setup(core(), [result]);
  const e = app.elements;
  e['ai-categories'].children[4].fire('click');
  assert.equal(e['ai-categories'].children[4].attributes['aria-selected'], 'true');
  assert.match(e['ai-active-panel'].textContent, /Execution risk/);
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'negative');
  assert.equal(e['ai-active-panel'].children[0].children[0].children[0].children[1].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  e['ai-categories'].children[4].fire('keydown', {key: 'ArrowRight', preventDefault() {}});
  assert.equal(e['ai-categories'].children[5].attributes['aria-selected'], 'true');
  assert.equal(e['ai-categories'].children[5].focused, true);
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'neutral');
});

test('selecting a second insight updates the expression', async () => {
  const result = ai();
  result.data.encouraging.push({heading: 'Mixed outlook', text: 'Evidence is mixed.', tone: 'caution', evidence_ids: ['S1']});
  const app = await setup(core(), [result]);
  const e = app.elements;
  const rows = e['ai-active-panel'].children[0].children;
  const secondButton = rows[1].children[0].children[0];
  let prevented = false;
  secondButton.fire('keydown', {key: 'Enter', preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(secondButton.attributes['aria-pressed'], 'true');
  assert.equal(e['ai-robot-guide-face'].children[0].dataset.tone, 'caution');
  assert.equal(e['ai-robot-reading'].textContent, 'Mixed outlook');
});

test('omits unavailable numbers and the 52-week range', async () => {
  const app = await setup(core({prices: {NSE: null, BSE: null}, change_percent: null,
    year_low: null, year_high: null, snapshot: {}, health: null}), [ai()]);
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
