const fs = require('node:fs');
const vm = require('node:vm');
const stockFormat = require('../../public/stock-format.js');
class Element {
  constructor(tagName = '') {
    this.tagName = tagName; this.children = []; this.listeners = {}; this.attributes = {};
    this.hidden = false; this.open = false; this.style = {setProperty() {}}; this.dataset = {}; this._text = ''; this.className = '';
    this.classList = {
      add: name => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), name])].join(' '); },
      remove: name => { this.className = this.className.split(/\s+/).filter(value => value !== name).join(' '); },
      toggle: (name, force) => { const has = this.className.split(/\s+/).includes(name); if (force === undefined ? !has : force) this.classList.add(name); else this.classList.remove(name); }
    };
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  fire(type, event = {}) { this.listeners[type]?.(event); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._text = ''; this.children = nodes; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
}
function core(overrides = {}) {
  return {ok: true, symbol: 'IN:EXAMPLE', fetched_at: '2026-10-07T04:00:00Z', data: {
    name: 'Example Ltd', industry: 'Software', prices: {NSE: 100, BSE: null}, change_percent: 1.5,
    year_low: 70, year_high: 120, snapshot: {marketCap: 5000, pPerEBasicExcludingExtraordinaryItemsTTM: 24},
    health: {groups: [{metrics: [{id: 'revenue', label: 'Revenue', value: 900, unit: '₹ cr', period: '2026-03-31', change_label: '+12% YoY',
      history: [{period: '2024-03-31', value: 600}, {period: '2025-03-31', value: 800}, {period: '2026-03-31', value: 900}]}]}]}, ...overrides
  }};
}
function signal(heading, overrides = {}) {
  return {heading, text: heading + ' supporting explanation.', tone: 'positive', evidence_ids: ['S1'], facts: [{label: 'Revenue', value: '+12% YoY'}], ...overrides};
}
function ai() {
  return {ok: true, data: {
    summary: {heading: 'Revenue grows as margins tighten', text: 'Revenue rose in the reported period, while margins narrowed. This is the original AI paragraph.', tone: 'caution', evidence_ids: ['S1']},
    encouraging: [signal('Revenue momentum')], attention: [], changes: [signal('Revenue rose')],
    catalysts: [], risks: [], watch_next: [signal('Can margins recover?', {tone: 'neutral', facts: [{label: 'Operating margin', value: '18.4%'}]})],
    sources: [{id: 'S1', section: 'financials', label: 'Reported financial health'}], generated_at: '2026-10-07T05:00:00Z'
  }, coverage: {sources: 1, news_stories: 0}};
}
function walk(root, predicate) {
  return [...(predicate(root) ? [root] : []), ...root.children.flatMap(child => walk(child, predicate))];
}
function byClass(root, name) { return walk(root, el => el.className.split(/\s+/).includes(name)); }
function visibleText(root) {
  if (root.hidden) return '';
  const children = root.tagName === 'details' && !root.open ? root.children.slice(0, 1) : root.children;
  return root._text + children.map(visibleText).join('');
}
function install(context) { vm.runInNewContext(fs.readFileSync('public/ai-story.js', 'utf8'), context); }
function renderer() {
  const context = {document: {createElement: tag => new Element(tag), createElementNS: (_ns, tag) => new Element(tag)}, window: {tickrStockFormat: stockFormat}};
  install(context); return context.window.tickrAIStory;
}
module.exports = {Element, core, ai, signal, walk, byClass, visibleText, install, renderer, stockFormat};
