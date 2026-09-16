const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('public/onboarding.html', 'utf8');
const css = fs.readFileSync('public/onboarding.css', 'utf8');
const catalogCss = fs.readFileSync('public/onboarding-catalog.css', 'utf8');
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

test('card catalog includes icons, visual examples, and a live dashboard preview', () => {
  assert.match(html, /onboarding-catalog\.css/);
  assert.match(html, /id="preview-canvas"/);
  assert.match(js, /function icon\(/);
  assert.match(js, /function cardVisual\(/);
  assert.match(js, /card-visual--chart/);
  assert.match(js, /card-visual--donut/);
  assert.match(catalogCss, /\.tone-overview/);
  assert.match(catalogCss, /\.preview-dashboard-card/);
  assert.match(catalogCss, /prefers-reduced-motion/);
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
});
