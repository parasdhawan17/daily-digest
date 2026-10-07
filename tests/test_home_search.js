const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('public/home-search.js', 'utf8');
const pageSource = fs.readFileSync('public/index.html', 'utf8');
const homeStyles = fs.readFileSync('public/home.css', 'utf8');

test('homepage presents Tickr AI with a walking robot companion', () => {
  assert.match(pageSource, /Understand Indian stocks<br><span>with AI\./);
  assert.match(pageSource, /class="home-ai-companion"/);
  assert.match(pageSource, /class="ai-robot-shell"/);
  assert.match(pageSource, /src="\/home-robot\.js/);
  assert.match(homeStyles, /@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*\.home-page \.home-ai-companion/);
});

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
  }
  const area = new Element();
  const form = new Element();
  const input = new Element();
  const popover = new Element();
  const list = new Element();
  const status = new Element();
  const links = [new Element(), new Element()];
  const parts = {'form': form, 'input': input, '.home-search-popover': popover,
    'ul': list, '[role="status"]': status};
  area.querySelector = selector => parts[selector];
  area.contains = target => target !== null;
  const timers = new Map();
  let nextTimer = 0;
  const calls = [];
  const navigations = [];
  const document = {
    querySelector: () => area,
    querySelectorAll: () => links,
    createElement: () => new Element(),
    addEventListener() {}
  };
  const context = {
    document,
    window: {location: {assign(url) { navigations.push(url); }}},
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
    input, form, list, popover, links, calls, navigations,
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

test('selecting a homepage search result opens stock details directly', async () => {
  const app = setup([{market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'}]);
  await app.search('TCS');
  assert.match(app.calls[0], /market=IN&q=TCS$/);
  assert.equal(app.list.children.length, 1);
  assert.equal(app.input.attributes['aria-expanded'], 'true');
  app.list.children[0].fire('click');
  assert.deepEqual(app.navigations, ['/stocks/IN:TCS']);
  assert.doesNotMatch(pageSource, /home-search-choice/);
});

test('keyboard selection opens stock details', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'},
    {market: 'IN', symbol: 'IN:TECHM', name: 'Tech Mahindra'}
  ]);
  await app.search('TECH');
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  app.input.fire('keydown', {key: 'ArrowDown', preventDefault() {}});
  assert.equal(app.input.attributes['aria-activedescendant'], 'home-stock-result-1');
  app.form.fire('submit', {preventDefault() {}});
  assert.deepEqual(app.navigations, ['/stocks/IN:TECHM']);
});

test('ambiguous submitted names require an explicit selection', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TECHM', name: 'Tech Mahindra'},
    {market: 'IN', symbol: 'IN:TECH', name: 'Tech Co'}
  ]);
  await app.search('Techn');
  app.form.fire('submit', {preventDefault() {}});
  assert.deepEqual(app.navigations, []);
  assert.equal(app.list.children.length, 2);
  app.list.children[1].fire('click');
  assert.deepEqual(app.navigations, ['/stocks/IN:TECH']);
});

test('an exact ticker submitted before suggestions return opens stock details', async () => {
  const app = setup([
    {market: 'IN', symbol: 'IN:TCS', name: 'Tata Consultancy Services'},
    {market: 'IN', symbol: 'IN:TCI', name: 'Transport Corporation of India'}
  ]);
  app.input.value = 'TCS';
  app.form.fire('submit', {preventDefault() {}});
  await new Promise(setImmediate);
  assert.deepEqual(app.navigations, ['/stocks/IN:TCS']);
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
