const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {Element, ai, core, install, stockFormat, walk, byClass} = require('./helpers/ai_story_fixture');
class DOMElement extends Element {
  append(...nodes) { super.append(...nodes.map(value => {
    if (typeof value !== 'string') return value;
    const text = new Element(); text.textContent = value; return text;
  })); }
}
const source = fs.readFileSync('public/home-ai-signal.js', 'utf8');
function payload(overrides = {}) {
  return {ok: true, stock: {name: 'Example Ltd', symbol: 'IN:EXAMPLE', industry: 'Software',
    exchange: 'BSE', market_cap_crore: 120000, selection: 'highest_market_cap', price: 100,
    percent_change: 6, source_time: '2026-10-09 10:00', selected_at: '2026-10-10T00:00:00Z'}, core: core().data, overview: ai(), ...overrides};
}
async function setup(data, ok = true) {
  const elements = Object.fromEntries(['home-ai-signal', 'home-ai-content', 'home-ai-caption', 'home-ai-toolbar-status'].map(id => [id, new Element()]));
  let calls = 0;
  const context = {document: {getElementById: id => elements[id], createElement: tag => new DOMElement(tag), createElementNS: (_ns, tag) => new DOMElement(tag)}, window: {tickrStockFormat: stockFormat},
    AbortController, setTimeout, clearTimeout,
    fetch: async url => { assert.equal(url, '/api/home-ai-signal?selection=market-cap-v1'); calls++; if (data instanceof Error) throw data; return {ok, json: async () => data}; }};
  install(context); vm.runInNewContext(source, context);
  await new Promise(setImmediate);
  return {elements, calls};
}
test('loads once and renders real overview, sources, dates and full link', async () => {
  const {elements: e, calls} = await setup(payload());
  assert.equal(calls, 1);
  assert.equal(e['home-ai-signal'].attributes['aria-busy'], 'false');
  assert.match(e['home-ai-content'].textContent, /Example Ltd/);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-stage').length, 3);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-range').length, 0);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-trend').length, 2);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-lead').length, 0);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-more-rows').length, 0);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-footer').length, 0);
  assert.equal(byClass(e['home-ai-toolbar-status'], 'home-ai-mover-tag')[0].textContent, 'Highest market cap');
  assert.doesNotMatch(e['home-ai-content'].textContent, /Read the AI take|Explore more signals|AI-generated synthesis/);
  const links = walk(e['home-ai-content'], el => el.tagName === 'a');
  assert.ok(links.some(link => link.href === '/stocks/IN:EXAMPLE#financials'));
  assert.ok(links.some(link => link.href === '/stocks/IN:EXAMPLE'));
  assert.match(e['home-ai-caption'].textContent, /1,20,000.*Highest market cap.*2026-10-09/);
});
test('small market caps have no minimum threshold claim', async () => {
  const data = payload(); data.stock.market_cap_crore = 32.78;
  const {elements: e} = await setup(data);
  assert.equal(byClass(e['home-ai-toolbar-status'], 'home-ai-mover-tag')[0].textContent, 'Highest market cap');
  assert.doesNotMatch(e['home-ai-content'].textContent, /Trending large stock/);
  assert.match(e['home-ai-caption'].textContent, /33 crore/);
  assert.doesNotMatch(e['home-ai-caption'].textContent, /Filter|NaN/);
});
test('AI failure restores illustrative signal UI', async () => {
  const {elements: e} = await setup(payload({overview: null}));
  assert.match(e['home-ai-content'].textContent, /Tata Consultancy Services.*Steady cash flow/);
  assert.equal(byClass(e['home-ai-content'], 'preview-signal').length, 3);
  assert.equal(e['home-ai-toolbar-status'].textContent, 'Example');
  assert.match(e['home-ai-caption'].textContent, /Not a current assessment of TCS/);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-stage').length, 0);
});
test('no-match and server failure restore the original example', async () => {
  for (const [data, ok] of [[{ok: false, code: 'no_match'}, true], [{}, false]]) {
    const {elements: e} = await setup(data, ok);
    assert.match(e['home-ai-content'].textContent, /Tata Consultancy Services.*Steady cash flow/);
    assert.equal(byClass(e['home-ai-content'], 'preview-signal').length, 3);
    assert.equal(byClass(e['home-ai-toolbar-status'], 'home-ai-mover-tag').length, 0);
    assert.equal(e['home-ai-signal'].attributes['aria-busy'], 'false');
  }
});
test('provider content is rendered as text and unsupported source sections use the safe overview link', async () => {
  const data = payload(); data.stock.name = '<script>bad()</script>';
  data.overview.data.sources[0].section = 'javascript:bad()';
  const {elements: e} = await setup(data);
  assert.match(e['home-ai-content'].textContent, /<script>bad\(\)<\/script>/);
  assert.ok(walk(e['home-ai-content'], el => el.tagName === 'a').every(link => !link.href.includes('javascript:')));
});

test('homepage loads the same visual renderer and styles as stock details', () => {
  const html = fs.readFileSync('public/index.html', 'utf8');
  assert.match(html, /ai-story\.css/);
  assert.ok(html.indexOf('stock-format.js') < html.indexOf('ai-story.js'));
  assert.ok(html.indexOf('ai-story.js') < html.indexOf('home-ai-signal.js'));
});

test('empty signal sections are omitted instead of showing placeholders', async () => {
  const data = payload();
  data.overview.data.watch_next = []; data.overview.data.catalysts = [];
  const {elements: e} = await setup(data);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-stage').length, 2);
  assert.doesNotMatch(e['home-ai-content'].textContent, /What to watch|No supported checkpoint/);
  for (const category of ['changes', 'attention', 'encouraging', 'risks']) data.overview.data[category] = [];
  const {elements: empty} = await setup(data);
  assert.equal(byClass(empty['home-ai-content'], 'ai-story-stage').length, 0);
  assert.doesNotMatch(empty['home-ai-content'].textContent, /Recent context|No supported checkpoint/);
  assert.equal(byClass(empty['home-ai-content'], 'preview-signal').length, 3);
  data.core = {}; data.stock.price = null; data.stock.percent_change = null; data.stock.market_cap_crore = null;
  const {elements: none} = await setup(data);
  assert.equal(byClass(none['home-ai-content'], 'ai-story-stage').length, 0);
});

test('prices use gain or loss highlights with correct signed changes', async () => {
  for (const [change, tone, signed] of [[6, 'positive', '+6%'], [-3, 'negative', '-3%'], [0, 'neutral', '0%']]) {
    const data = payload(); data.stock.percent_change = change; data.core.change_percent = change;
    const {elements: e} = await setup(data);
    const quote = byClass(e['home-ai-content'], 'home-ai-header-price')[0];
    assert.ok(quote.className.includes(tone));
    assert.ok(quote.textContent.includes(signed));
    assert.equal(byClass(e['home-ai-content'], 'ai-story-price').length, 0);
  }
});

test('header shows price beside company without duplicate ticker or price card', async () => {
  const data = payload(); data.stock.name = 'EXAMPLE';
  const {elements: e} = await setup(data);
  const company = byClass(e['home-ai-content'], 'preview-company')[0];
  assert.equal((company.textContent.match(/EXAMPLE/g) || []).length, 1);
  assert.equal(byClass(e['home-ai-content'], 'preview-company-badge').length, 0);
  assert.equal(byClass(e['home-ai-content'], 'home-ai-header-price').length, 1);
  assert.match(company.textContent, /₹100.00/);
  assert.doesNotMatch(company.textContent, /Trending large stock/);
  assert.match(e['home-ai-toolbar-status'].textContent, /Highest market cap/);
  assert.equal(byClass(e['home-ai-content'], 'ai-story-price').length, 0);
});

test('homepage financial chart stays inside the expandable explanation', async () => {
  const {elements: e} = await setup(payload());
  const recent = byClass(e['home-ai-content'], 'recent')[0];
  assert.equal(recent.children.filter(child => child.className === 'ai-story-trend').length, 0);
  const details = walk(recent, el => el.tagName === 'details');
  assert.ok(details.some(el => byClass(el, 'ai-story-trend').length === 1));
});

test('fills three available signal cards and caps additional signals without duplicates', async () => {
  const data = payload();
  data.overview.data.watch_next = [];
  const item = data.overview.data.changes[0];
  data.overview.data.attention = [{...item, heading: 'Margins narrowed'}, {...item, heading: 'Costs increased'}];
  data.overview.data.risks = [{...item, heading: 'Demand risk'}, item];
  const {elements: e} = await setup(data);
  const cards = byClass(e['home-ai-content'], 'ai-story-stage');
  assert.equal(cards.length, 3);
  assert.ok(cards.every(card => !card.className.split(' ').includes('now')));
  assert.match(cards[0].textContent, /Revenue rose/);
  assert.match(cards[1].textContent, /Margins narrowed/);
  assert.match(cards[2].textContent, /Costs increased/);
  assert.doesNotMatch(e['home-ai-content'].textContent, /Demand risk|No supported/);
});

test('missing market data, malformed AI, and network errors use the labeled example', async () => {
  const missing = payload(); missing.stock.price = null;
  const malformed = payload(); malformed.overview.data.summary = null;
  const invalid = payload(); invalid.stock.symbol = 'invalid';
  for (const data of [null, missing, malformed, invalid, new Error('Network failed'), new DOMException('Timeout', 'AbortError')]) {
    const {elements: e} = await setup(data);
    assert.equal(byClass(e['home-ai-content'], 'preview-signal').length, 3);
    assert.equal(e['home-ai-toolbar-status'].textContent, 'Example');
    assert.match(e['home-ai-caption'].textContent, /Illustrative.*Not a current assessment/);
    assert.equal(byClass(e['home-ai-content'], 'home-ai-header-price').length, 0);
    assert.equal(e['home-ai-signal'].attributes['aria-busy'], 'false');
  }
});
