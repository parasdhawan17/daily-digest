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
  assert.match(template, /ai-overview\.css\?v=20261007-bot-loading/);
  assert.match(template, /stock\.css\?v=20261007-simple-tour/);
  assert.match(template, /stock\.js\?v=20261007-simple-tour/);
  assert.match(template, /data-active-tab="ai-overview"/);
  assert.match(source, /document\.body\.dataset\.activeTab = id/);
  assert.match(styles, /data-active-tab="ai-overview"\] \.stock-section-assistant,[\s\S]*data-active-tab="ai-overview"\] \.stock-section-ai-launcher\{display:none\}/);
});

test('Overview tab does not render company signals', () => {
  const overviewSource = source.slice(source.indexOf('function overview()'), source.indexOf('function aiEvidence('));
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

test('AI overview tab omits empty signal groups', () => {
  class Element {
    constructor(tag) {
      this.tagName = tag;
      this.children = [];
      this.dataset = {};
      this.attributes = {};
      this.style = {setProperty() {}};
      this.hidden = false;
      this.className = '';
      this.classList = {add: name => { this.className += ' ' + name; }};
    }
    set textContent(value) { this.value = String(value); this.children = []; }
    get textContent() { return (this.value || '') + this.children.map(child => child.textContent).join(''); }
    append(...children) { this.children.push(...children); }
    setAttribute(name, value) { this.attributes[name] = value; }
  }
  const testSource = source.replace(/\n  init\(\);\n\}\)\(\);\s*$/, '\n  window.testRender = renderAIOverview;\n})();');
  assert.notEqual(testSource, source);
  const themeButton = new Element('button');
  const window = {tickrStockFormat: require('../public/stock-format.js'), addEventListener() {}};
  const document = {body: {dataset: {symbol: 'IN:EXAMPLE'}}, documentElement: {dataset: {theme: 'light'}},
    createElement: tag => new Element(tag), createElementNS: (_namespace, tag) => new Element(tag), getElementById: () => themeButton, querySelectorAll: () => []};
  vm.runInNewContext(testSource, {window, document, URLSearchParams, Date, Intl});
  const response = {data: {
    summary: {heading: 'Steady revenue', text: 'Revenue was steady.', tone: 'neutral', evidence_ids: []},
    encouraging: [{heading: 'Revenue stability', text: 'Revenue held up.', tone: 'positive', evidence_ids: []}],
    attention: [], changes: [], catalysts: [], risks: [], watch_next: [], sources: [], generated_at: '2026-09-25T00:00:00Z'
  }, coverage: {sources: 0, news_stories: 0}};
  const panel = new Element('section');
  window.testRender(panel, response);
  assert.equal(panel.children.length, 1);
  assert.equal(panel.children[0].className, 'ai-insight-explorer');
  assert.match(panel.textContent, /The AI take/);
  assert.match(panel.textContent, /What looks encouraging/);
  assert.doesNotMatch(panel.textContent, /What needs attention|What changed recently|Potential catalysts|Key risks|What to watch next/);
  const firstCategory = panel.children[0].children[1].children[1].children[0];
  assert.equal(firstCategory.tagName, 'section');

  response.data.attention = [{heading: 'Margin pressure', text: 'Margins narrowed.', tone: 'caution', evidence_ids: []}];
  response.data.changes = [{heading: 'Debt rose', text: 'Net debt increased.', tone: 'negative', evidence_ids: []}];
  response.data.watch_next = [{heading: 'Next results', text: 'Monitor the next report.', tone: 'neutral', evidence_ids: []}];
  const fullPanel = new Element('section');
  window.testRender(fullPanel, response);
  const groups = fullPanel.children[0].children[1].children[1].children;
  assert.equal(groups.length, 4);
  assert.ok(groups.every(group => group.tagName === 'section'));
  const signals = groups.map(group => group.children[1].children[0].children[0]);
  assert.deepEqual(signals.map(signal => signal.children[0].children[0].dataset.tone), ['positive', 'caution', 'negative', 'neutral']);
  assert.equal(new Set(signals.map(signal => signal.children[0].children[0].children[0].children[7].attributes.d)).size, 4);

  response.data.watch_next[0].tone = 'unsupported';
  response.data.watch_next[0].evidence_ids = ['S1'];
  response.data.sources = [{id: 'S1', section: 'financials', label: 'Reported financials'}];
  const fallbackPanel = new Element('section');
  window.testRender(fallbackPanel, response);
  const fallbackSignal = fallbackPanel.children[0].children[1].children[1].children[3].children[1].children[0].children[0];
  assert.equal(fallbackSignal.children[0].children[0].dataset.tone, 'neutral');
  assert.match(fallbackSignal.textContent, /Context/);
  assert.equal(fallbackSignal.children.at(-1).children[0].children[0].href, '#financials');

  response.data.encouraging = [];
  response.data.attention = [];
  response.data.changes = [];
  response.data.watch_next = [];
  const emptyPanel = new Element('section');
  window.testRender(emptyPanel, response);
  assert.equal(emptyPanel.children.length, 1);
  const categories = emptyPanel.children[0].children[1].children[1];
  assert.equal(categories.hidden, true);
});
