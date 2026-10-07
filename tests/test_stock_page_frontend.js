const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/stock.js', 'utf8');
const template = fs.readFileSync('templates/stock.html', 'utf8');
const styles = fs.readFileSync('public/stock.css', 'utf8');

test('standalone research page exposes facts-only market data', () => {
  assert.match(template, /\('analysis','Market Data'\)/);
  assert.doesNotMatch(template, /analyst views|Analyst opinions/);
  assert.doesNotMatch(source, /request\(['"](?:targets|forecasts)['"]/);
  assert.doesNotMatch(source, /The analyst view|Price targets|Recommendation summary|Looking ahead: earnings per share/);
  assert.match(source, /Provider-reported numerical variability/);
  assert.match(source, /Reported moving-average prices without trading interpretations/);
});

test('standalone research page renders accessible filtered P\/E history', () => {
  assert.match(source, /filter: 'pe'/);
  assert.match(source, /\['Current P\/E', current\], \['Median', median\], \['Low', low\], \['High', high\]/);
  assert.match(source, /Historical price-to-earnings ratio\. Use left and right arrows/);
  assert.match(source, /\['ArrowLeft', 'ArrowRight', 'Home', 'End'\]/);
  assert.match(source, /View P\/E data/);
  assert.match(styles, /\.pe-median-line/);
});

test('standalone research page versions the new assets', () => {
  assert.match(template, /ai-overview\.css\?v=20261007-story/);
  assert.match(template, /stock\.css\?v=20261007-simple-tour/);
  assert.match(template, /stock\.js\?v=20261007-flag/);
  assert.match(template, /data-active-tab="ai-overview"/);
  assert.match(source, /document\.body\.dataset\.activeTab = id/);
  assert.match(styles, /data-active-tab="ai-overview"\] \.stock-section-assistant,[\s\S]*data-active-tab="ai-overview"\] \.stock-section-ai-launcher\{display:none\}/);
});

test('Overview tab does not render company signals', () => {
  const overviewSource = source.slice(source.indexOf('function overview()'), source.indexOf('const aiTones'));
  assert.doesNotMatch(overviewSource, /Company signals|loadSignalPreview|stock-signals-preview/);
  assert.doesNotMatch(styles, /stock-signals-preview/);
});

test('stock cards and metrics expose the floating section explainer', () => {
  assert.match(source, /stock-card stock-ai-target/);
  assert.match(source, /stock-metric stock-ai-target/);
  assert.match(source, /c\.dataset\.aiCardId = 'news_story'/);
  assert.match(source, /Click a section card or metric to get a short AI explanation/);
  assert.match(source, /fetch\('\/api\/stock-section-ai'/);
  assert.match(source, /Restart the local server, then reload this page/);
  assert.match(source, /AI-generated synthesis · Not investment advice/);
  assert.match(styles, /\.stock-section-assistant/);
  assert.match(styles, /\.stock-section-ai-launcher/);
  assert.match(source, /stock-section-ai-launcher-tip', 'Click a section to let Tickr AI explain'/);
  assert.match(styles, /\.stock-section-ai-launcher-tip::after/);
  assert.match(styles, /env\(safe-area-inset-bottom\)/);
});

test('section explainer uses a cancellable 600ms delegated long press', () => {
  assert.match(source, /content\.addEventListener\('pointerdown'/);
  assert.match(source, /setTimeout\(\(\) => \{/);
  assert.match(source, /\}, 600\)/);
  assert.match(source, /Math\.hypot\([\s\S]*> 10/);
  assert.match(source, /\['pointerup', 'pointercancel', 'lostpointercapture'\]/);
  assert.match(source, /window\.addEventListener\('scroll', \(\) => \{ cancelHold\(\);/);
  assert.match(source, /a,button,input,select,textarea,summary,\[role=button\],\.stock-chart/);
  assert.match(source, /target\.closest\('#panel-ai-overview'\)/);
});

test('section explainer replaces prior state and handles stale or failed requests', () => {
  assert.match(source, /sectionAssistantBody\.replaceChildren\(\)/);
  assert.match(source, /sectionAIController\.abort\(\)/);
  assert.match(source, /version === sectionAIRequestVersion/);
  assert.match(source, /error\.name !== 'AbortError'/);
  assert.match(source, /aria-live/);
  assert.match(styles, /prefers-reduced-motion:reduce/);
});

test('welcome assistant remains available until dismissed or the user scrolls', () => {
  assert.doesNotMatch(source, /setTimeout\(collapseSectionAssistant, 5000\)/);
  assert.match(source, /later\.onclick = \(\) => \{ finishOnboarding\(\); collapseSectionAssistant\(\); \}/);
  assert.match(source, /if \(sectionAssistantWelcomeOpen\) collapseSectionAssistant\(\)/);
  assert.match(source, /minimize\.onclick = collapseSectionAssistant/);
  assert.match(styles, /\.stock-section-assistant\.is-collapsing/);
  assert.match(styles, /@keyframes stock-ai-collapse/);
  assert.match(styles, /\.stock-section-ai-launcher\.is-entering/);
});

test('launcher smoothly expands into and attaches to the assistant', () => {
  assert.match(source, /attachFromLauncher/);
  assert.match(source, /classList\.add\('is-opening'\)/);
  assert.match(source, /classList\.add\('is-attaching'\)/);
  assert.match(styles, /\.stock-section-assistant\.is-opening/);
  assert.match(styles, /@keyframes stock-ai-expand/);
  assert.match(styles, /@keyframes stock-ai-launcher-attach/);
  assert.match(source, /stock-section-assistant is-initial/);
  assert.match(styles, /\.stock-section-assistant\.is-initial\{animation:stock-ai-arrive/);
  assert.doesNotMatch(styles, /will-change:transform,opacity;animation:stock-ai-arrive/);
});

test('stock tab uses the shared visual renderer and local evidence navigation', () => {
  const {Element, core, ai, install, stockFormat, byClass, visibleText, walk} = require('./helpers/ai_story_fixture');
  const testSource = source.replace(/\n  init\(\);\n\}\)\(\);\s*$/, '\n  window.testRender = renderAIOverview; window.setCore = value => {core = value;};\n})();');
  assert.notEqual(testSource, source);
  const themeButton = new Element('button');
  const window = {tickrStockFormat: stockFormat, addEventListener() {}};
  const document = {body: {dataset: {symbol: 'IN:EXAMPLE'}}, documentElement: {dataset: {theme: 'light'}},
    createElement: tag => new Element(tag), createElementNS: (_namespace, tag) => new Element(tag), getElementById: () => themeButton, querySelectorAll: () => []};
  const context = {window, document, URLSearchParams, Date, Intl};
  install(context); vm.runInNewContext(testSource, context);
  window.setCore(core().data);
  const panel = new Element('section'); window.testRender(panel, ai());
  assert.equal(byClass(panel, 'ai-story-stage').length, 3);
  assert.equal(byClass(panel, 'ai-story-robot').length, 1);
  assert.equal(byClass(panel, 'ai-story-trend').length, 1);
  assert.match(visibleText(panel), /₹100.00/);
  assert.doesNotMatch(visibleText(panel), /original AI paragraph/);
  assert.equal(walk(panel, el => el.tagName === 'a')[0].href, '#financials');
  assert.ok(template.indexOf('ai-story.js') < template.indexOf('stock.js'));

  vm.runInNewContext(fs.readFileSync('public/ai-overview-legacy-renderer.js', 'utf8'), context);
  window.tickrAIOverviewLayout = {visual: false};
  const legacy = new Element('section'); window.testRender(legacy, ai());
  assert.equal(byClass(legacy, 'ai-story-stage').length, 0);
  assert.equal(byClass(legacy, 'ai-category').length, 3);
  assert.match(visibleText(legacy), /original AI paragraph/);
  assert.match(visibleText(legacy), /What looks encouraging/);
  assert.equal(walk(legacy, el => el.tagName === 'a')[0].href, '#financials');
});
