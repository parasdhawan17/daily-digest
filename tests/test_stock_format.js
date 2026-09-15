const test = require('node:test');
const assert = require('node:assert/strict');
const {number, fmt, money, pct, statementUnit, metricUnit, field} = require('../public/stock-format.js');

test('missing values stay missing while zero and negatives remain meaningful', () => {
  for (const value of [null, undefined, '', ' ', true, NaN, Infinity, '—']) assert.equal(number(value), null);
  assert.equal(number('0'), 0);
  assert.equal(number('-1,234.5'), -1234.5);
  assert.equal(money(null), '—');
  assert.equal(money(0), '₹0.00');
  assert.equal(pct(-2.5), '-2.5%');
  assert.equal(pct(0), '0%');
  assert.equal(fmt(1234567), '12,34,567');
});
test('per-share measures and shareholder equity use distinct units', () => {
  assert.equal(statementUnit('DPS-CommonStockPrimaryIssue'), '₹');
  assert.equal(statementUnit('DilutedEPSExcludingExtraOrdItems'), '₹');
  assert.equal(statementUnit('TotalCommonSharesOutstanding'), 'cr shares');
  assert.equal(statementUnit("TotalLiabilitiesShareholders'Equity"), '₹ cr');
  assert.equal(statementUnit('periodLength'), 'months');
  assert.equal(statementUnit('periodType'), '');
});
test('unconfirmed metric scales remain explicitly unspecified', () => {
  assert.equal(metricUnit('incomeStatement', 'Revenue'), 'provider units');
  assert.equal(metricUnit('priceandVolume', 'marketCap'), '₹ cr');
  assert.equal(metricUnit('valuation', 'priceToBookMostRecentFiscalYear'), '×');
  assert.equal(metricUnit('persharedata', 'freeCashFlowPerShare'), '₹');
});
test('company codes and reporting years do not receive number grouping', () => {
  assert.equal(field('532540', 'exchangeCodeBse'), '532540');
  assert.equal(field(2026, 'FiscalYear'), '2026');
  assert.equal(field(532540, 'revenue'), '5,32,540');
});

test('direction indicators leave zero and missing values neutral', () => {
  const {direction} = require('../public/stock-format.js');
  assert.equal(direction(12), 'positive');
  assert.equal(direction(-12), 'negative');
  for (const value of [0, '0', null, undefined, '', NaN]) assert.equal(direction(value), 'neutral');
});
