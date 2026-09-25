const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/home-search.js', 'utf8');

function setup(results) {
  class Element {
    constructor() {
      this.children = [];
      this.listeners = {};
      this.attributes = {};
      this.hidden = false;
      this.value = '';
      this.textContent = '';
      this.classList = {add() {}, remove() {}, toggle() {}};
    }
    addEventListener(type, handler) { this.listeners[type] = handler; }
    fire(type, event = {}) { this.listeners[type]?.(event); }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren() { this.children = []; }
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
    scrollIntoView() {}
    focus() { this.focused = true; }
    showModal() { this.open = true; }
    close() { this.open = false; this.fire('close'); }
    getBoundingClientRect() { return {left: 100, right: 500, top: 100, bottom: 500}; }
  }
  const area = new Element();
  const form = new Element();
  const input = new Element();
  const popover = new Element();
  const list = new Element();
  const status = new Element();
  const choice = new Element();
  choice.open = false;
  const choiceClose = new Element();
  const choiceTitle = new Element();
  const choiceSymbol = new Element();
  const choiceAI = new Element();
  const choiceDetails = new Element();
  const choiceParts = {'#home-choice-title': choiceTitle, '#home-choice-symbol': choiceSymbol,
    '#home-choice-ai': choiceAI, '#home-choice-details': choiceDetails,
    '.home-choice-close': choiceClose};
  choice.querySelector = selector => choiceParts[selector];
  const links = [new Element(), new Element()];
  const parts = {'form': form, 'input': input, '.home-search-popover': popover,
    'ul': list, '[role="status"]': status};
  area.querySelector = selector => parts[selector];
  area.contains = target => target !== null;
  const timers = new Map();
  let nextTimer = 0;
  const calls = [];
  const document = {
    querySelector: selector => selector === '.home-search-choice' ? choice : area,
    querySelectorAll: () => links,
    createElement: () => new Element(),
    addEventListener() {}
  };
  const context = {
    document,
    window: {},
    fetch: async url => {
      calls.push(url);
      return {ok: true, json: async () => ({ok: true, results})};
    },
    AbortController,
    setTimeout(fn, ms) { const id = ++nextTimer; timers.set(id, {fn, ms}); return id; },
    clearTimeout(id) { timers.delete(id); }
  };
  vm.runInNewContext(source, context);
  return {
    input, form, list, popover, links, calls, choice, choiceClose, choiceTitle, choiceSymbol, choiceAI, choiceDetails,
    async search(query) {
      input.value = query;
      input.fire('input');
      for (const [id, timer] of timers) {
        if (timer.ms === 250) { timers.delete(id); timer.fn(); }
      }
      await new Promise(setImmediate);
    }
  };
}

test('typing in the homepage field shows Indian results and both navigation choices', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  assert.match(app.calls[0], /market=IN&q=TCS$/);
  assert.equal(app.list.children.length, 1);
  assert.equal(app.input.attributes['aria-expanded'], 'true');
  app.list.children[0].fire('click');
  assert.equal(app.choice.open, true);
  assert.equal(app.choiceTitle.textContent, 'Tata Consultancy Services');
  assert.equal(app.choiceAI.href, '/ai-overview/IN:TCS');
  assert.equal(app.choiceDetails.href, '/stocks/IN:TCS');
  assert.equal(app.choiceTitle.focused, true);
});

test('keyboard selection opens the chosen company actions', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'},
    {market: 'IN', symbol: 'IN:TECHM', name: 'Tech Mahindra'}
  ]);
  await app.search('TECH');
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  assert.equal(app.input.attributes['aria-activedescendant'], 'home-stock-result-1');
  app.form.fire('submit', {preventDefault() {}});
  assert.equal(app.choiceAI.href, '/ai-overview/IN:TECHM');
  assert.equal(app.choiceDetails.href, '/stocks/IN:TECHM');
});

test('ambiguous submitted names require an explicit selection', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TECHM', name: 'Tech Mahindra'},
    {market: 'IN', symbol: 'IN:TECH', name: 'Tech Co'}
  ]);
  await app.search('Techn');
  app.form.fire('submit', {preventDefault() {}});
  assert.equal(app.choice.open, false);
  assert.equal(app.list.children.length, 2);
  app.list.children[1].fire('click');
  assert.equal(app.choiceAI.href, '/ai-overview/IN:TECH');
});

test('editing the chosen company resets both actions', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  app.list.children[0].fire('click');
  assert.equal(app.choice.open, true);
  app.input.value = 'INFY';
  app.input.fire('input');
  assert.equal(app.choice.open, false);
});

test('company dialog closes and can be reopened from the selected search', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  app.list.children[0].fire('click');
  app.choiceClose.fire('click');
  assert.equal(app.choice.open, false);
  assert.equal(app.input.focused, true);
  app.form.fire('submit', {preventDefault() {}});
  assert.equal(app.choice.open, true);
  app.choice.fire('click', {target: app.choice, clientX: 0, clientY: 0});
  assert.equal(app.choice.open, false);
});

test('an exact ticker submitted before suggestions return advances to the choice', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'},
    {market: 'IN', symbol: 'IN:TCI', name: 'Transport Corporation of India'}
  ]);
  app.input.value = 'TCS';
  app.form.fire('submit', {preventDefault() {}});
  await new Promise(setImmediate);
  assert.equal(app.choiceAI.href, '/ai-overview/IN:TCS');
});

test('clearing the field closes suggestions', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  await app.search('');
  assert.equal(app.popover.hidden, true);
  assert.equal(app.input.attributes['aria-expanded'], 'false');
  assert.equal(app.list.children.length, 0);
});

test('other homepage search links focus the direct search field', () => {
  const app = setup([]);
  let prevented = false;
  app.links[0].fire('click', {preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(app.input.focused, true);
});
