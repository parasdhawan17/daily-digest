const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('public/index.html', 'utf8');
const source = html.match(/<script>\s*(window\.dataLayer[\s\S]*?)<\/script>/)[1];

function boot(href, referrer) {
  const context = {URL, URLSearchParams, location: {href}, document: {referrer}};
  context.window = context;
  vm.runInNewContext(source, context);
  return context.dataLayer.map(args => Array.from(args));
}

test('private URL data is removed before GA4 configuration while ad attribution is preserved', () => {
  const calls = boot('https://www.mydailydigest.online/digest?t=private-token&email=private%40example.com&utm_source=google&utm_campaign=research&gclid=ad-click#secret', 'https://www.mydailydigest.online/welcome?token=private#secret');
  assert.equal(calls[0][0], 'js');
  assert.equal(calls[1][0], 'set');
  assert.equal(calls[1][1].page_location, 'https://www.mydailydigest.online/digest?utm_source=google&utm_campaign=research&gclid=ad-click');
  assert.equal(calls[1][1].page_referrer, 'https://www.mydailydigest.online/welcome');
  assert.deepEqual(calls[2], ['config', 'G-6HV1LTZVDF']);
});

test('direct visits and company URLs work without a referrer', () => {
  const calls = boot('https://www.mydailydigest.online/stocks/IN:TCS', '');
  assert.equal(calls[1][1].page_location, 'https://www.mydailydigest.online/stocks/IN:TCS');
  assert.equal(calls[1][1].page_referrer, '');
});
