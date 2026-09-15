/* Shared, deterministic display rules. No provider scale is inferred from size. */
(function (root) {
  'use strict';
  function number(value) {
    if (value === null || value === undefined || typeof value === 'boolean' || String(value).trim() === '') return null;
    const parsed = Number(String(value).replace(/,/g, ''));
    return Number.isFinite(parsed) ? parsed : null;
  }
  function fmt(value) {
    const n = number(value);
    return n === null ? (value === null || value === undefined || value === '' ? '—' : String(value))
      : new Intl.NumberFormat('en-IN', {maximumFractionDigits: 2}).format(n);
  }
  function money(value) {
    const n = number(value);
    return n === null ? '—' : '₹' + new Intl.NumberFormat('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(n);
  }
  function pct(value) { return number(value) === null ? '—' : (number(value) > 0 ? '+' : '') + fmt(value) + '%'; }
  function statementUnit(key) {
    const k = String(key).toLowerCase();
    if (k === 'periodlength') return 'months';
    if (k === 'periodtype') return '';
    if (/pershare|eps|^dps/.test(k)) return '₹';
    if (/weightedaverageshares|totalcommonsharesoutstanding|^numberofshares/.test(k)) return 'cr shares';
    if (/margin|percent/.test(k)) return '%';
    return '₹ cr';
  }
  function metricUnit(group, key) {
    const k = String(key).toLowerCase();
    if (/date/.test(k)) return '';
    if (/marketcap/.test(k)) return '₹ cr';
    if (group === 'persharedata' || /peremployee/.test(k)) return '₹';
    if (group === 'growth' || /margin|yield|returnon|payout|percent/.test(k)) return '%';
    if (/ratio|turnover|coverage|pere|pricetobook|pricetosales|perfreecashflow|debtper.*equity|currentevper/.test(k)) return '×';
    return 'provider units';
  }
  function field(value, key) {
    // Years and identifiers are not quantities and must not gain digit grouping.
    if (value !== null && value !== undefined && /^(fiscalyear|calendaryear|startyear|year|tickerid|symbol|exchangecodebse|exchangecodense|exchangecodensi|rank|ratingvalue|instrumenttype|periodtype)$/i.test(key)) return String(value);
    return fmt(value);
  }
  function direction(value) {
    const n = number(value);
    return n === null || n === 0 ? 'neutral' : n > 0 ? 'positive' : 'negative';
  }
  const api = {number, fmt, money, pct, statementUnit, metricUnit, field, direction};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.tickrStockFormat = api;
})(typeof window === 'undefined' ? {} : window);
