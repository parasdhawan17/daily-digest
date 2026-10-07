const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('public/ai-overview-layout.js', 'utf8');
function boot({value, delayed = false, errorsLoading, broken = false} = {}) {
  let timeout, flags, connect;
  const posthog = {getFeatureFlag(key) { assert.equal(key, 'ai-overview-visual'); return value; },
    onFeatureFlags(callback) { flags = callback; if (broken) throw new Error('Unavailable'); if (!delayed) callback([], {}, {errorsLoading}); }};
  const context = {window: {tickrAnalytics: {onReady(callback) { connect = callback; }}},
    document: {body: {dataset: {}}}, setTimeout(callback) {timeout = callback; return 1;}, clearTimeout() {}};
  vm.runInNewContext(source, context);
  return {layout: context.window.tickrAIOverviewLayout, dataset: context.document.body.dataset,
    connect: () => connect(posthog), disable: () => connect(null), timeout: () => timeout(),
    flags: () => flags([], {}, {errorsLoading})};
}
for (const [value, expected] of [[true, true], [false, false], [undefined, true]]) {
  test('PostHog flag '+String(value)+' selects visual='+expected, async () => {
    const app = boot({value}); app.connect();
    assert.equal(await app.layout.ready, expected);
    assert.equal(app.dataset.aiOverviewLayout, expected ? 'visual' : 'legacy');
  });
}
test('waits for flag loading before selecting an explicit false', async () => {
  const app = boot({value: false, delayed: true}); app.connect();
  let resolved = false; app.layout.ready.then(() => {resolved = true;});
  await Promise.resolve(); assert.equal(resolved, false);
  app.flags(); assert.equal(await app.layout.ready, false);
});
test('disabled analytics, SDK errors and flag errors all use the visual default', async () => {
  const disabled = boot(); disabled.disable(); assert.equal(await disabled.layout.ready, true);
  for (const options of [{value: false, broken: true}, {value: false, errorsLoading: true}, {value: false, errorsLoading: ['network']}]) {
    const app = boot(options); app.connect(); assert.equal(await app.layout.ready, true);
  }
  const emptyErrors = boot({value: false, errorsLoading: []}); emptyErrors.connect();
  assert.equal(await emptyErrors.layout.ready, false);
});
test('timeout defaults to visual and late flags cannot replace the current layout', async () => {
  const app = boot({value: false, delayed: true}); app.connect(); app.timeout();
  assert.equal(await app.layout.ready, true);
  app.flags(); assert.equal(app.layout.visual, true);
});
test('selection stays fixed when subsequent flag evaluations change', async () => {
  const app = boot({value: false}); app.connect(); assert.equal(await app.layout.ready, false);
  app.timeout(); assert.equal(app.layout.visual, false);
});
