const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('public/onboarding.html', 'utf8');
const css = fs.readFileSync('public/onboarding.css', 'utf8');
const catalogCss = fs.readFileSync('public/onboarding-catalog.css', 'utf8');
const stepTwoCss = fs.readFileSync('public/onboarding-step-two.css', 'utf8');
const js = fs.readFileSync('public/onboarding.js', 'utf8');
const catalog = JSON.parse(fs.readFileSync('public/dashboard-catalog.json', 'utf8'));

test('onboarding exposes two accessible full-page steps', () => {
  assert.match(html, /aria-label="Onboarding progress"/);
  assert.match(html, /data-step="1"/);
  assert.match(html, /data-step="2"/);
  assert.match(html, /role="alert"/);
  assert.doesNotMatch(html, /role="dialog"/);
});

test('hierarchical selector has rail, card panel, and sticky summary', () => {
  assert.match(html, /id="category-rail"/);
  assert.match(html, /id="card-grid"/);
  assert.match(html, /id="selection-count"/);
  assert.match(css, /\.category-rail/);
  assert.match(css, /\.selection-card/);
  assert.match(css, /@media\(max-width:720px\)/);
});

test('card catalog uses stock dashboard cards with sample data', () => {
  assert.match(html, /onboarding-catalog\.css/);
  assert.match(html, /onboarding-step-two\.css/);
  assert.match(html, /dashboard-cards\.css/);
  assert.match(html, /class="onboarding-step indian-dashboard" data-step="2"/);
  assert.match(html, /id="preview-canvas"/);
  assert.match(js, /function dashboardSample\(/);
  assert.match(js, /dashboardSample\(card,category\.id\)/);
  assert.match(js, /dashboardSample\(card,active\.id\)/);
  assert.match(js, /dashboard-card sample-dashboard-card/);
  assert.match(js, /dashboard-mini-table/);
  assert.match(js, /dashboard-ai-insight/);
  assert.match(html, /Figures are examples/);
  assert.match(catalogCss, /\.tone-overview/);
  assert.match(catalogCss, /\.selection-card \.dashboard-card/);
  assert.match(catalogCss, /prefers-reduced-motion/);
  assert.match(stepTwoCss, /\.step-two-guide/);
});

test('every catalog card is unique and category recommendations are valid', () => {
  const ids = catalog.categories.flatMap(category => category.cards.map(card => card.id));
  assert.equal(new Set(ids).size, ids.length);
  for (const category of catalog.categories) {
    const own = new Set(category.cards.map(card => card.id));
    assert.ok(category.recommended.every(id => own.has(id)));
  }
  assert.match(js, /category\.recommended\.forEach/);
  assert.match(js, /selectedCards\.delete/);
  assert.doesNotMatch(js, /activateCategory\(button\.dataset\.category, true\)/);
});
