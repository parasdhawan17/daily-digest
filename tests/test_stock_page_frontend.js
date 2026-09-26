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
  assert.match(template, /ai-overview\.css\?v=20260927-compact-type/);
  assert.match(template, /stock\.css\?v=20260927-single-open/);
  assert.match(template, /stock\.js\?v=20260927-single-open/);
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
  assert.match(source, /Long press a section to have an AI summary for it\./);
  assert.match(source, /fetch\('\/api\/stock-section-ai'/);
  assert.match(source, /Restart the local server, then reload this page/);
  assert.match(source, /AI-generated synthesis · Not investment advice/);
  assert.match(styles, /\.stock-section-assistant/);
  assert.match(styles, /\.stock-section-ai-launcher/);
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

test('welcome assistant collapses to the bot after five seconds or on scroll', () => {
  assert.match(source, /setTimeout\(collapseSectionAssistant, 5000\)/);
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

  response.data.encouraging = [];
  const emptyPanel = new Element('section');
  window.testRender(emptyPanel, response);
  assert.equal(emptyPanel.children.length, 1);
  const categories = emptyPanel.children[0].children[1].children[1];
  assert.equal(categories.hidden, true);
});
