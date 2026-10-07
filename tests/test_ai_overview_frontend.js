const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {Element, core, ai, walk, byClass, visibleText, install, stockFormat} = require('./helpers/ai_story_fixture');
const source = fs.readFileSync('public/ai-overview.js', 'utf8');
const template = fs.readFileSync('templates/ai_overview.html', 'utf8');
const ids = ['nav-stock-details', 'hero-stock-details', 'footer-stock-details', 'theme-toggle',
  'company-name', 'company-symbol', 'company-industry', 'price-meta', 'page-status', 'overview-content',
  'ai-status', 'ai-content', 'ai-facts', 'sources-list', 'ai-coverage'];
async function setup(corePayload, aiResponses, bootstrap = null, deferCore = false) {
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  if (bootstrap !== null) { elements['company-bootstrap'] = new Element(); elements['company-bootstrap'].textContent = typeof bootstrap === 'string' ? bootstrap : JSON.stringify(bootstrap); }
  elements['overview-content'].hidden = true; elements['ai-content'].hidden = true;
  let aiCalls = 0, releaseCore;
  const calls = [];
  const document = {body: {dataset: {symbol: 'IN:EXAMPLE'}}, documentElement: {dataset: {theme: 'light'}, style: {}},
    getElementById: id => elements[id], createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag)};
  const context = {document, window: {tickrStockFormat: stockFormat}, URLSearchParams,
    fetch: async url => {
      calls.push(url);
      if (url.startsWith('/api/stock-data?')) {
        if (deferCore) await new Promise(resolve => { releaseCore = resolve; });
        return {ok: corePayload.ok, json: async () => corePayload};
      }
      const response = aiResponses[Math.min(aiCalls++, aiResponses.length - 1)];
      return {ok: response.ok, json: async () => response};
    }};
  install(context); vm.runInNewContext(source, context);
  const flush = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
  await flush();
  return {elements, calls, flush, get aiCalls() {return aiCalls;}, releaseCore: () => releaseCore()};
}

test('standalone uses the shared visual story and consolidated company facts', async () => {
  const app = await setup(core(), [ai()]), e = app.elements;
  assert.equal(e['overview-content'].hidden, false);
  assert.equal(e['company-name'].textContent, 'Example Ltd');
  assert.equal(e['ai-content'].hidden, false);
  assert.equal(e['ai-facts'].hidden, true);
  assert.equal(byClass(e['ai-content'], 'ai-story-stage').length, 3);
  assert.match(visibleText(e['ai-content']), /₹100.00/);
  assert.doesNotMatch(visibleText(e['ai-content']), /original AI paragraph/);
  assert.equal(walk(e['ai-content'], el => el.tagName === 'a')[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.equal(e['sources-list'].children[0].children[0].href, '/stocks/IN:EXAMPLE#financials');
  assert.match(e['price-meta'].textContent, /Market data as of 7 Oct 2026/);
  assert.equal(e['hero-stock-details'].href, '/stocks/IN:EXAMPLE');
  assert.equal(app.calls.filter(url => url.includes('section=history')).length, 0);
  assert.ok(app.calls.some(url => url.includes('brief=meaning-v1')));
  assert.equal(app.aiCalls, 1);
  assert.match(template, /ai-story\.js/);
  assert.ok(template.indexOf('ai-story.js') < template.indexOf('ai-overview.js'));
  const activeMarkup = template.replace(/<template id="ai-overview-legacy-template">[\s\S]*?<\/template>/, '');
  assert.doesNotMatch(activeMarkup, /id="metrics-grid"|id="range-card"|id="ai-categories"/);
  assert.match(template, /<template id="ai-overview-legacy-template">/);
});

test('AI failure preserves company facts and retry restores the story', async () => {
  const app = await setup(core(), [{ok: false, error: 'AI temporarily unavailable.'}, ai()]), e = app.elements;
  assert.equal(e['overview-content'].hidden, false);
  assert.equal(e['ai-content'].hidden, true);
  assert.equal(e['ai-facts'].hidden, false);
  assert.match(visibleText(e['ai-facts']), /₹100.00.*52-week low/);
  assert.match(e['ai-facts'].textContent, /Market cap.*5,000/);
  e['ai-status'].children[1].fire('click'); await app.flush();
  assert.equal(app.aiCalls, 2);
  assert.equal(e['ai-content'].hidden, false); assert.equal(e['ai-facts'].hidden, true);
});

test('malformed AI output preserves fallback facts', async () => {
  const app = await setup(core(), [{ok: true, data: {summary: null}}]);
  assert.equal(app.elements['ai-content'].hidden, true);
  assert.match(visibleText(app.elements['ai-facts']), /₹100.00/);
  assert.match(app.elements['ai-status'].textContent, /could not be read/);
});

test('AI arriving before company data updates the timeline when core resolves', async () => {
  const app = await setup(core(), [ai()], null, true);
  assert.doesNotMatch(visibleText(app.elements['ai-content']), /₹100.00/);
  app.releaseCore(); await app.flush();
  assert.match(visibleText(app.elements['ai-content']), /₹100.00/);
  assert.equal(byClass(app.elements['ai-content'], 'ai-story-trend').length, 1);
  assert.equal(app.elements['ai-facts'].hidden, true);
});

test('uses a matching server snapshot and falls back for invalid snapshots', async () => {
  const app = await setup(core(), [ai()], core());
  assert.equal(app.calls.some(url => url.includes('section=core')), false);
  for (const seed of ['invalid json', {...core(), symbol: 'IN:TCS'}]) {
    const fallback = await setup(core(), [ai()], seed);
    assert.ok(fallback.calls.some(url => url.includes('section=core')));
  }
});
