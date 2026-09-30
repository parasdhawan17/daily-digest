const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('public/home-robot.js', 'utf8');

function setup({reduced = false, legacy = false} = {}) {
  const timers = new Map(), listeners = {}, animations = [];
  let timerId = 0, resized;
  const motion = {matches: reduced};
  motion[legacy ? 'addListener' : 'addEventListener'] = (...args) => { listeners.motion = args.at(-1); };
  const walker = {
    offsetWidth: 32, style: {}, left: 26,
    getBoundingClientRect: () => ({left: walker.left}),
    animate(frames, options) {
      let finish;
      const animation = {frames, options, cancelled: false,
        finished: new Promise(resolve => { finish = resolve; }),
        finish: () => finish(), cancel() { this.cancelled = true; }};
      animations.push(animation);
      return animation;
    }
  };
  const track = {clientWidth: 88, dataset: {}, querySelector: () => walker,
    getBoundingClientRect: () => ({left: 20})};
  const document = {hidden: false, querySelector: () => track,
    addEventListener: (name, fn) => { listeners[name] = fn; }};
  class ResizeObserver { constructor(fn) { resized = fn; } observe() {} }
  vm.runInNewContext(source, {document, window: {ResizeObserver}, ResizeObserver,
    matchMedia: () => motion,
    Math: Object.assign(Object.create(Math), {random: () => .75}),
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
    clearTimeout: id => timers.delete(id)});
  const tick = () => { const [id, fn] = timers.entries().next().value; timers.delete(id); fn(); };
  return {track, walker, document, motion, listeners, animations, timers, tick, resize: () => resized()};
}

test('robot uses measured pixel keyframes and continues after a completed walk', async () => {
  const env = setup();
  env.tick();
  assert.equal(env.track.dataset.action, 'walk');
  const animation = env.animations[0];
  assert.equal(animation.frames[0].transform, 'translateX(6.72px)');
  assert.match(animation.frames[1].transform, /^translateX\([\d.]+px\)$/);
  animation.finish();
  await Promise.resolve();
  assert.equal(env.track.dataset.action, 'look');
  assert.equal(env.timers.size, 1);
});

test('resizing cancels stale keyframes and restarts within the resized runway', () => {
  const env = setup();
  env.tick();
  env.track.clientWidth = 48;
  env.walker.left = 30;
  env.resize();
  assert.equal(env.animations[0].cancelled, true);
  assert.equal(env.walker.style.transform, 'translateX(10px)');
  env.tick();
  const target = parseFloat(env.animations[1].frames[1].transform.slice(11));
  assert.ok(target >= 0 && target <= 16);
});

test('legacy media-query listeners respect reduced motion and hidden tabs', () => {
  const env = setup({reduced: true, legacy: true});
  assert.equal(env.timers.size, 0);
  env.motion.matches = false;
  env.listeners.motion();
  env.tick();
  assert.equal(env.track.dataset.action, 'walk');
  env.document.hidden = true;
  env.listeners.visibilitychange();
  assert.equal(env.animations[0].cancelled, true);
  assert.equal(env.track.dataset.action, 'idle');
  assert.equal(env.timers.size, 0);
});
