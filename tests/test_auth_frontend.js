// Run with node --test tests/test_auth_frontend.js. External services are stubbed.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('public/auth.js', 'utf8');

async function boot(session, login) {
  const controls = {children: [], replaceChildren() { this.children = []; }, appendChild(x) { this.children.push(x); }};
  const notice = {hidden: true, textContent: ''};
  let callback, redirected, opened = 0, renderOptions;
  const calls = [];
  const listeners = {};
  const location = {pathname: '/', hash: '', assign(path) { redirected = path; }};
  const context = {
    document: {documentElement: {getAttribute: () => 'dark'}, cookie: 'tickr_csrf=csrf', getElementById: id => id === 'auth-controls' ? controls : notice,
      createElement: () => ({}), head: {appendChild: script => script.onload()}},
    location, sessionStorage: {getItem() { return null; }},
    google: {accounts: {id: {initialize: opts => { callback = opts.callback; }, renderButton(_controls, options) { renderOptions = options; }}}},
    CustomEvent: function(type, options) { this.type = type; this.detail = options && options.detail; },
    addEventListener(type, callback) { listeners[type] = callback; },
    fetch: async (url, options) => {
      calls.push({url, options});
      return {json: async () => url.endsWith('/config') ? {ok: true, enabled: true, client_id: 'client'} :
        url.endsWith('/session') ? session : url.endsWith('/logout') ? {ok: true} : login};
    },
    dispatchEvent() {}, openSubscribeModal() { opened++; }
  };
  context.window = context;
  vm.runInNewContext(source, context);
  await context.tickrAuth.ready;
  return {controls, notice, calls, context, listeners, get renderOptions() {return renderOptions;}, get callback() {return callback;},
    get redirected() {return redirected;}, get opened() {return opened;}};
}
const anonymous = {ok: true, authenticated: false};

test('Google button follows the dark theme and can be refreshed', async () => {
  const app = await boot(anonymous, {ok: true, authenticated: true});
  assert.equal(app.renderOptions.theme, 'outline_dark');
  assert.equal(typeof app.listeners['tickr-theme-change'], 'function');
});

test('Google existing subscriber opens digest and sends CSRF', async () => {
  const app = await boot(anonymous, {ok: true, authenticated: true, needs_subscription: false});
  app.callback({credential: 'verified-by-server'});
  await new Promise(setImmediate);
  assert.equal(app.redirected, '/digest');
  assert.equal(app.calls.at(-1).options.headers['X-CSRF-Token'], 'csrf');
});
test('Google new subscriber opens popup without redirect', async () => {
  const app = await boot(anonymous, {ok: true, authenticated: true, needs_subscription: true});
  app.callback({credential: 'token'});
  await new Promise(setImmediate);
  assert.equal(app.opened, 1);
  assert.equal(app.redirected, undefined);
});
test('Failed verification shows error without opening digest', async () => {
  const app = await boot(anonymous, {ok: false, error: 'Could not verify'});
  app.callback({credential: 'bad'});
  await new Promise(setImmediate);
  assert.equal(app.notice.textContent, 'Could not verify');
  assert.equal(app.redirected, undefined);
});
test('Returning session exposes digest and working logout', async () => {
  const app = await boot({ok: true, authenticated: true});
  assert.equal(app.controls.children[0].href, '/digest');
  app.controls.children[1].onclick();
  await new Promise(setImmediate);
  assert.equal(app.calls.at(-1).url, '/api/auth/logout');
  assert.equal(app.redirected, '/');
});
