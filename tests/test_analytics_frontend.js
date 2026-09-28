// Run with node --test tests/test_analytics_frontend.js.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/analytics.js', 'utf8');

async function boot() {
  const captured = [];
  const listeners = {};
  let scriptSource = '';
  const context = {
    URL,
    Error,
    console,
    innerWidth: 1280,
    location: {pathname: '/stocks/IN:TCS', origin: 'https://example.com'},
    document: {
      readyState: 'complete',
      referrer: 'https://search.example/result?q=private',
      body: {dataset: {symbol: 'IN:TCS'}},
      addEventListener(type, callback) { listeners['document:' + type] = callback; },
      createElement() { return {}; },
      head: {appendChild(script) {
        scriptSource = script.src;
        context.posthog = {
          init(_key, options) { options.loaded(); },
          capture(event, properties) { captured.push({event, properties}); },
          identify() {},
          captureException() {}
        };
        script.onload();
      }}
    },
    addEventListener(type, callback) { listeners[type] = callback; },
    fetch: async url => {
      if (url === '/api/analytics/config') return {
        ok: true,
        json: async () => ({enabled: true, project_key: 'phc_public', host: 'https://us.i.posthog.com'})
      };
      return {ok: true, status: 200, json: async () => ({ok: true})};
    }
  };
  context.window = context;
  vm.runInNewContext(source, context);
  await new Promise(setImmediate);
  return {context, captured, listeners, get scriptSource() { return scriptSource; }};
}

test('loads the regional PostHog SDK and sends privacy-safe page context', async () => {
  const app = await boot();
  assert.equal(app.scriptSource, 'https://us-assets.i.posthog.com/static/array.js');
  const page = app.captured.find(item => item.event === '$pageview');
  assert.equal(page.properties.page_type, 'stock_details');
  assert.equal(page.properties.symbol, 'IN:TCS');
  assert.equal(page.properties.referrer_host, 'search.example');
  assert.equal(page.properties.schema_version, 1);
  assert.equal(JSON.stringify(page.properties).includes('private'), false);
});

test('records API health and AI usage without query strings or payloads', async () => {
  const app = await boot();
  await app.context.fetch('/api/stock-ai?symbol=IN%3ATCS&prompt=private');
  const api = app.captured.find(item => item.event === 'api_request_completed');
  const ai = app.captured.find(item => item.event === 'ai_request_completed');
  assert.equal(api.properties.endpoint, '/api/stock-ai');
  assert.equal(api.properties.success, true);
  assert.equal(ai.properties.feature, 'stock_ai_overview');
  assert.equal(JSON.stringify([api, ai]).includes('prompt'), false);
});

test('records uncaught errors as bounded analytics events', async () => {
  const app = await boot();
  app.listeners.error({error: new Error('render failed')});
  const error = app.captured.find(item => item.event === 'app_error');
  assert.equal(error.properties.source, 'window_error');
  assert.equal(error.properties.error_message, 'render failed');
});
