// Run with node --test tests/test_analytics_frontend.js.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/analytics.js', 'utf8');

async function boot(enabled = true) {
  const captured = [];
  const listeners = {};
  let scriptSource = '';
  const context = {
    URL,
    setTimeout,
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
        json: async () => ({enabled: enabled, project_key: 'phc_public', host: 'https://us.i.posthog.com'})
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
  let readySDK;
  app.context.tickrAnalytics.onReady(sdk => {readySDK = sdk;});
  assert.equal(readySDK, app.context.posthog);
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


test('GA4 business events work without PostHog and exclude personal fields', async () => {
  const app = await boot(false), events = [];
  app.context.gtag = (...args) => events.push(args);
  app.context.tickrAnalytics.track('view_stock', {symbol: 'IN:TCS', email: 'private@example.com', token: 'private'});
  app.context.tickrAnalytics.track('view_stock', {symbol: 'IN:TCS'});
  app.context.tickrAnalytics.track('view_ai_overview', {symbol: 'IN:TCS'});
  app.context.tickrAnalytics.track('view_stock', {symbol: 'private@example.com'});
  app.context.tickrAnalytics.track('arbitrary_event', {email: 'private@example.com'});
  assert.deepEqual(events.map(event => event[1]), ['view_stock', 'view_ai_overview']);
  assert.equal(events[0][2].send_to, 'G-6HV1LTZVDF');
  assert.doesNotMatch(JSON.stringify(events), /private|email|token/);
});

test('only confirmed new saved accounts emit signup; updates only emit saves', async () => {
  const app = await boot(false), events = [];
  app.context.gtag = (...args) => events.push(args);
  const track = app.context.tickrAnalytics;
  track.savedWatchlist({ok: false, mode: 'verified', is_new_signup: true}, 3);
  track.savedWatchlist({ok: true, mode: 'doi', is_new_signup: true}, 3);
  assert.equal(events.length, 0);
  track.savedWatchlist({ok: true, mode: 'verified', is_new_signup: true}, 3);
  track.savedWatchlist({ok: true, mode: 'verified', is_new_signup: false}, 5);
  assert.deepEqual(events.map(event => event[1]), ['sign_up', 'watchlist_saved', 'watchlist_saved']);
  assert.equal(events[0][2].method, 'google');
  assert.equal(events[1][2].stock_count, 3);
  assert.equal(events[2][2].stock_count, 5);
});

test('watchlist navigation runs once even if Google calls completion more than once', async () => {
  const app = await boot(false), timers = [];
  app.context.setTimeout = callback => timers.push(callback);
  let redirected = 0;
  app.context.gtag = (_command, _event, params) => { if (params.event_callback) params.event_callback(); };
  app.context.tickrAnalytics.savedWatchlist({ok: true, mode: 'verified'}, 2, () => redirected++);
  timers.forEach(callback => callback());
  assert.equal(redirected, 1);
});

test('blocked Google script cannot prevent navigation after a saved watchlist', async () => {
  const app = await boot(false), timers = [];
  app.context.setTimeout = callback => timers.push(callback);
  let redirected = 0;
  app.context.gtag = () => {};
  app.context.tickrAnalytics.savedWatchlist({ok: true, mode: 'verified'}, 2, () => redirected++);
  assert.equal(redirected, 0);
  timers.forEach(callback => callback());
  assert.equal(redirected, 1);
});
