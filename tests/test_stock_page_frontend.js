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
  assert.match(template, /stock\.css\?v=20260925-signals-preview/);
  assert.match(template, /stock\.js\?v=20260926-nonempty-signals/);
});

test('AI overview tab omits empty signal groups', () => {
  class Element {
    constructor(tag) {
      this.tagName = tag;
      this.children = [];
      this.className = '';
      this.classList = {add: name => { this.className += ' ' + name; }};
    }
    set textContent(value) { this.value = String(value); this.children = []; }
    get textContent() { return (this.value || '') + this.children.map(child => child.textContent).join(''); }
    append(...children) { this.children.push(...children); }
    setAttribute() {}
  }
  const testSource = source.replace(/\n  init\(\);\n\}\)\(\);\s*$/, '\n  window.testRender = renderAIOverview;\n})();');
  assert.notEqual(testSource, source);
  const themeButton = new Element('button');
  const window = {tickrStockFormat: require('../public/stock-format.js'), addEventListener() {}};
  const document = {body: {dataset: {symbol: 'IN:EXAMPLE'}}, documentElement: {dataset: {theme: 'light'}},
    createElement: tag => new Element(tag), getElementById: () => themeButton, querySelectorAll: () => []};
  vm.runInNewContext(testSource, {window, document, URLSearchParams, Date, Intl});
  const response = {data: {
    summary: {heading: 'Steady revenue', text: 'Revenue was steady.', tone: 'neutral', evidence_ids: []},
    encouraging: [{heading: 'Revenue stability', text: 'Revenue held up.', tone: 'positive', evidence_ids: []}],
    attention: [], changes: [], catalysts: [], risks: [], watch_next: [], sources: [], generated_at: '2026-09-25T00:00:00Z'
  }, coverage: {sources: 0, news_stories: 0}};
  const panel = new Element('section');
  window.testRender(panel, response);
  assert.equal(panel.children.length, 3);
  assert.match(panel.textContent, /What looks encouraging/);
  assert.doesNotMatch(panel.textContent, /What needs attention|What changed recently|Potential catalysts|Key risks|What to watch next/);

  response.data.encouraging = [];
  const emptyPanel = new Element('section');
  window.testRender(emptyPanel, response);
  assert.equal(emptyPanel.children.length, 2);
});
