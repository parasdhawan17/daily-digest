const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

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
  assert.match(template, /stock\.css\?v=20260923-facts-pe1/);
  assert.match(template, /stock\.js\?v=20260923-facts-pe1/);
});
