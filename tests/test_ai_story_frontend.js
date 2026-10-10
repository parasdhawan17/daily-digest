const {test} = require('node:test');
const assert = require('node:assert/strict');
const {renderer, core, ai, signal, walk, byClass, visibleText} = require('./helpers/ai_story_fixture');

test('initial view presents three stages with explanations and additional signals collapsed', () => {
  const result = ai(), root = renderer().render(result, core().data);
  assert.equal(byClass(root, 'ai-story-stage').length, 3);
  const shown = visibleText(root);
  assert.match(shown, /Revenue grows as margins tighten/);
  assert.match(shown, /Now.*Recent context.*What to watch/);
  assert.match(shown, /Revenue rose/);
  assert.match(shown, /Can margins recover/);
  assert.doesNotMatch(shown, /original AI paragraph|supporting explanation|Revenue momentum/);
  assert.equal(walk(root, el => el.tagName === 'details' && el.open).length, 0);
  const take = walk(root, el => el.tagName === 'details' && el.children[0].textContent === 'Read the AI take')[0];
  take.open = true;
  assert.match(visibleText(root), /original AI paragraph/);
  assert.equal(walk(take, el => el.tagName === 'a')[0].href, '#financials');
});

test('exploring more signals reveals compact fact cards while explanations stay collapsed', () => {
  const root = renderer().render(ai(), core().data);
  const explore = walk(root, el => el.tagName === 'details' && el.children[0].textContent.startsWith('Explore more signals'))[0];
  assert.doesNotMatch(visibleText(root), /Revenue momentum/);
  explore.open = true;
  const card = byClass(root, 'ai-story-more-card')[0];
  assert.match(visibleText(card), /Revenue momentum.*Encouraging.*Revenue\+12% YoY/);
  assert.doesNotMatch(visibleText(card), /supporting explanation/);
  const why = walk(card, el => el.tagName === 'details')[0];
  why.open = true;
  assert.match(visibleText(card), /Revenue momentum supporting explanation/);
  assert.equal(walk(card, el => el.tagName === 'a')[0].href, '#financials');
});

test('price range marker uses the reported endpoints, including zero and missing values', () => {
  const render = overrides => renderer().render(ai(), core(overrides).data);
  assert.equal(byClass(render({}), 'ai-story-range-marker')[0].style.left, '60%');
  assert.equal(byClass(render({prices: {NSE: 0}, year_low: 0, year_high: 100}), 'ai-story-range-marker')[0].style.left, '0%');
  assert.equal(byClass(render({prices: {NSE: 140}}), 'ai-story-range-marker')[0].style.left, '100%');
  assert.match(visibleText(render({prices: {NSE: 140}})), /above the reported range/);
  for (const range of [{year_low: null}, {year_high: 70}, {year_low: 150}]) {
    assert.equal(byClass(render(range), 'ai-story-range').length, 0);
  }
  const missing = render({prices: {NSE: null, BSE: null}, change_percent: null});
  assert.equal(byClass(missing, 'ai-story-range-marker').length, 0);
  assert.match(visibleText(missing), /Daily change unavailable/);
});

test('home and additional stock signals show the same reported chart and expandable data', () => {
  const story = renderer(), data = ai(), coreData = core().data;
  const home = story.render(data, coreData, {compact: true, compactCharts: true, signalLimit: 3});
  const stock = story.render(data, coreData);
  const homeCard = byClass(home, 'ai-story-stage').find(card => /Revenue momentum/.test(card.textContent));
  const stockCard = byClass(stock, 'ai-story-more-card')[0];
  const chart = card => walk(card, el => el.tagName === 'svg' && el.attributes.role === 'img')[0];
  assert.equal(chart(stockCard).attributes['aria-label'], chart(homeCard).attributes['aria-label']);
  assert.equal(byClass(stockCard, 'ai-story-data')[0].textContent, byClass(homeCard, 'ai-story-data')[0].textContent);
  assert.doesNotMatch(visibleText(stockCard), /Reported actuals/);
  const why = walk(stockCard, el => el.tagName === 'details' && el.children[0].textContent === 'Why this matters')[0];
  why.open = true;
  assert.match(visibleText(stockCard), /Reported actuals.*View chart data/);
  const table = walk(why, el => el.tagName === 'details' && el.children[0].textContent === 'View chart data')[0];
  assert.equal(table.open, false);
  table.open = true;
  assert.match(visibleText(stockCard), /2024-03-31600.*2026-03-31900/);
});

test('watch and additional signal charts require supported financial history', () => {
  for (const supported of [true, false]) {
    const data = ai(), coreData = core().data;
    data.data.watch_next = [signal('Will revenue growth continue?')];
    if (!supported) coreData.health.groups[0].metrics[0].history = [{period: '2026-03-31', value: 900}];
    const root = renderer().render(data, coreData);
    for (const card of [byClass(root, 'ai-story-stage')[2], byClass(root, 'ai-story-more-card')[0]]) {
      assert.equal(byClass(card, 'ai-story-trend').length, supported ? 1 : 0);
      assert.equal(byClass(card, 'ai-story-data').length, supported ? 1 : 0);
      assert.match(card.textContent, /\+12% YoY/);
    }
  }
});

test('Now explains the actual range position, with clear handling for missing quotes', () => {
  for (const [price, description] of [[75, 'lower third'], [100, 'middle third'], [115, 'upper third'], [140, 'above'], [60, 'below']]) {
    const root = renderer().render(ai(), core({prices: {NSE: price}}).data);
    const now = byClass(root, 'ai-story-stage')[0];
    const why = walk(now, el => el.tagName === 'details')[0]; why.open = true;
    assert.match(visibleText(now), new RegExp(description));
    assert.match(visibleText(now), /compared with the past year.*earnings, cash flow, and valuation/);
  }
  const root = renderer().render(ai(), core({prices: {NSE: null, BSE: null}}).data);
  assert.match(byClass(root, 'ai-story-stage')[0].textContent, /latest quote is unavailable.*cannot be shown/);
});

test('expanded signals display the complete plain-language explanation and its source', () => {
  const result = ai();
  result.data.changes[0].text = 'Revenue is the money earned from sales. Higher revenue shows more sales in the reported period. Margins and cash flow help clarify how much of those sales becomes profit and cash.';
  const root = renderer().render(result, core().data), recent = byClass(root, 'ai-story-stage')[1];
  assert.doesNotMatch(visibleText(recent), /Revenue is the money/);
  const why = walk(recent, el => el.tagName === 'details')[0]; why.open = true;
  assert.match(visibleText(recent), /Revenue is the money.*how much of those sales becomes profit and cash/);
  assert.equal(walk(why, el => el.tagName === 'a')[0].href, '#financials');
});

test('financial trend uses exact metric history rather than AI fact strings', () => {
  const data = ai(); data.data.changes[0].facts[0].value = '999999% projected';
  const root = renderer().render(data, core().data);
  const chart = walk(root, el => el.tagName === 'svg' && el.attributes.role === 'img')[0];
  assert.match(chart.attributes['aria-label'], /Revenue \(₹ cr\): 2024-03-31: 600; 2025-03-31: 800; 2026-03-31: 900/);
  assert.doesNotMatch(chart.attributes['aria-label'], /999999|projected/);
  assert.match(byClass(root, 'ai-story-trend')[0].textContent, /Reported actuals.*2026-03-31/);
  assert.match(byClass(root, 'ai-story-data')[0].textContent, /2024-03-31600.*2026-03-31900/);
  const coreData = core().data;
  coreData.health.groups[0].metrics[0].history = [{period: '2024-03-31', value: -50}, {period: '2025-03-31', value: -50}];
  assert.doesNotMatch(walk(renderer().render(data, coreData), el => el.tagName === 'polyline')[0].attributes.points, /NaN|Infinity/);
});

test('unmatched, uncited, or insufficient financial series remain fact tiles', () => {
  for (const scenario of ['unmatched', 'uncited', 'insufficient', 'invalid']) {
    const data = ai(), coreData = core().data;
    if (scenario === 'unmatched') data.data.changes[0].facts[0].label = 'Growth outlook';
    if (scenario === 'uncited') data.data.sources[0].section = 'news';
    if (scenario === 'insufficient') coreData.health.groups[0].metrics[0].history = [{period: '2026-03-31', value: 900}];
    if (scenario === 'invalid') coreData.health.groups[0].metrics[0].history = [{period: 'bad', value: 100}, {period: '2026-03-31', value: null}];
    const root = renderer().render(data, coreData);
    assert.equal(byClass(byClass(root, 'ai-story-stage')[1], 'ai-story-trend').length, 0, scenario);
    assert.match(visibleText(root), /\+12% YoY/);
  }
});

test('prioritizes changes and watch questions, deduplicating signals across the whole story', () => {
  const data = ai(), duplicate = data.data.changes[0];
  data.data.attention = [structuredClone(duplicate)];
  data.data.watch_next.unshift(structuredClone(duplicate));
  data.data.catalysts = [signal('Upcoming meeting')];
  const root = renderer().render(data, core().data);
  const stages = byClass(root, 'ai-story-stage');
  assert.match(stages[1].textContent, /Revenue rose/);
  assert.match(stages[2].textContent, /Can margins recover/);
  assert.equal(walk(root, el => el.tagName === 'h4' || el.tagName === 'strong').filter(el => el.textContent === 'Revenue rose').length, 1);
  const more = byClass(root, 'ai-story-more-rows')[0];
  assert.doesNotMatch(more.textContent, /Revenue rose|Can margins recover/);
  assert.match(more.textContent, /Upcoming meeting/);
});

test('fallback selections and empty evidence never invent a checkpoint', () => {
  const data = ai(); data.data.changes = []; data.data.watch_next = [];
  data.data.attention = [signal('Margins narrowed', {tone: 'caution'})]; data.data.catalysts = [signal('Reported expansion')];
  let root = renderer().render(data, {});
  assert.match(byClass(root, 'ai-story-stage')[1].textContent, /Margins narrowed/);
  assert.match(byClass(root, 'ai-story-stage')[2].textContent, /Reported expansion/);
  for (const key of ['attention', 'encouraging', 'catalysts', 'risks']) data.data[key] = [];
  root = renderer().render(data, {});
  assert.match(visibleText(root), /Recent context is limited.*No supported checkpoint yet/);
  assert.equal(byClass(root, 'ai-story-more-rows').length, 0);
  assert.equal(byClass(root, 'ai-story-stage')[2].dataset.tone, 'neutral');
});
