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
    }
    addEventListener(type, handler) { this.listeners[type] = handler; }
    fire(type, event = {}) { this.listeners[type]?.(event); }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren() { this.children = []; }
    setAttribute(key, value) { this.attributes[key] = value; }
    removeAttribute(key) { delete this.attributes[key]; }
    scrollIntoView() {}
    focus() { this.focused = true; }
  }
  const area = new Element();
  const form = new Element();
  const input = new Element();
  const popover = new Element();
  const list = new Element();
  const status = new Element();
  const links = [new Element(), new Element()];
  const parts = {'form': form, 'input': input, '.home-search-popover': popover, 'ul': list, '[role="status"]': status};
  area.querySelector = selector => parts[selector];
  area.contains = target => target !== null;
  const timers = new Map();
  let nextTimer = 0;
  const calls = [];
  let destination;
  const document = {
    querySelector: () => area,
    querySelectorAll: () => links,
    createElement: () => new Element(),
    addEventListener() {}
  };
  const context = {
    document,
    window: {location: {assign(path) { destination = path; }}},
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
    input, form, list, popover, links, calls,
    get destination() { return destination; },
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

test('typing in the homepage field shows Indian results and opens the selected stock', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  assert.match(app.calls[0], /market=IN&q=TCS$/);
  assert.equal(app.list.children.length, 1);
  assert.equal(app.input.attributes['aria-expanded'], 'true');
  app.list.children[0].fire('click');
  assert.equal(app.destination, '/stocks/IN:TCS');
});

test('keyboard selection opens the chosen suggestion without a dialog', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'},
    {market: 'IN', symbol: 'IN:TECHM', name: 'Tech Mahindra'}
  ]);
  await app.search('TECH');
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  assert.equal(app.input.attributes['aria-activedescendant'], 'home-stock-result-1');
  app.form.fire('submit', {preventDefault() {}});
  assert.equal(app.destination, '/stocks/IN:TECHM');
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
