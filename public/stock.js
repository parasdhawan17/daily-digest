(function () {
  'use strict';
  const symbol = document.body.dataset.symbol;
  const $ = id => document.getElementById(id);
  const {number, fmt, money, pct, statementUnit, metricUnit, field, direction} = window.tickrStockFormat;
  const colors = ['#6f8aff', '#60b6b0', '#ce9c67', '#af8bcb', '#8093ac', '#ca8295'];
  const labels = {mgmtEffectiveness: 'Management effectiveness', financialstrength: 'Financial strength', persharedata: 'Per-share data', priceandVolume: 'Price & volume', INC: 'Income statement', BAL: 'Balance sheet', CAS: 'Cash flow', isInId: 'ISIN', exchangeCodeBse: 'BSE code', exchangeCodeNse: 'NSE symbol', xdDate: 'Ex-date', yoy_results: 'Annual results', quarter_results: 'Quarterly results', balancesheet: 'Balance sheet', cashflow: 'Cash flow', ratios: 'Ratios', shareholding_pattern_quarterly: 'Quarterly ownership', shareholding_pattern_yearly: 'Yearly ownership', stockFinancialMap: 'Statements', qoQComp: 'Quarter-over-quarter comparison', yqoQComp: 'Year-over-year comparison', actions: 'Corporate actions', analysis: 'Market Data', 'ai-overview': 'AI Overview'};
  Object.assign(labels, {bsePrice: 'BSE price (₹)', nsePrice: 'NSE price (₹)', stdDev: 'Standard deviation (provider units)',
    yhigh: '52-week high (₹)', ylow: '52-week low (₹)', high: 'Day high (₹)', low: 'Day low (₹)', close: 'Previous close (₹)', price: 'Price (₹)',
    percentChange: 'Change (%)', marketCap: 'Market cap (₹ cr)', pPerEBasicExcludingExtraordinaryItemsTTM: 'P/E · trailing 12 months (×)',
    currentDividendYieldCommonStockPrimaryIssueLTM: 'Dividend yield · last 12 months (%)', totalDebtPerTotalEquityMostRecentQuarter: 'Debt / equity · latest quarter (×)',
    priceYTDPricePercentChange: 'Year-to-date return (%)', price5DayPercentChange: '5-day return (%)', NetIncome: 'Net income (₹ cr)', interimNetIncome: 'Interim net income (₹ cr)',
    sectorPriceToEarningsValueRatio: 'Sector P/E (×)', percentage: 'Percentage (%)', holdingDate: 'Holding date',
    bonus: 'Bonus issues', dividend: 'Dividends', rights: 'Rights issues', splits: 'Stock splits', annualGeneralMeeting: 'Annual general meetings', boardMeetings: 'Board meetings'});
  function label(key) { return labels[key] || String(key).replace(/([a-z\d])([A-Z])/g, '$1 $2').replace(/([A-Z])([A-Z][a-z])/g, '$1 $2').replace(/_/g, ' ').replace(/^./, c => c.toUpperCase()); }
  function node(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
  function has(value) { return value !== null && value !== undefined && value !== '' && (typeof value !== 'object' || Object.values(value).some(has)); }
  function finite(value) { return number(value) !== null; }
  function numericOnly(value) {
    if (Array.isArray(value)) { const values = value.map(numericOnly).filter(has); return values.length ? values : null; }
    if (value && typeof value === 'object') { const result = Object.fromEntries(Object.entries(value).map(([key, item]) => [key, numericOnly(item)]).filter(([, item]) => has(item))); return has(result) ? result : null; }
    return finite(value) ? value : null;
  }
  function url(value) { try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) && !u.username ? u.href : null; } catch (e) { return null; } }
  function date(value) { if (!value) return 'Date unavailable'; const d = new Date(value); return Number.isNaN(+d) ? String(value) : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'}); }
  function stamp(value) { const d = new Date(value); return Number.isNaN(+d) ? 'Time unavailable' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata'}) + ' IST'; }
  function card(title, caption) { const c = node('article', 'stock-card'); c.append(node('h2', '', title)); if (caption) c.append(node('p', 'stock-caption', caption)); return c; }
  function empty(text) { return node('p', 'stock-caption', text || 'Not available for this company.'); }
  function indicator(text, tone = 'neutral', hint = '') { const value = node('span', 'stock-indicator tone-' + tone, text); if (hint) value.title = hint; return value; }
  function factList(entries) { const dl = node('dl', 'stock-facts'); entries.forEach(([key, value]) => { const row = node('div', 'stock-fact'); const dd = node('dd'); if (value instanceof Node) dd.append(value); else dd.textContent = value; row.append(node('dt', '', key), dd); dl.append(row); }); return dl; }
  function details(title, body, open) { const d = node('details', 'stock-detail'); d.open = !!open; d.append(node('summary', '', title)); const inner = node('div'); inner.append(body); d.append(inner); return d; }
  function table(headers, rows) {
    const wrap = node('div', 'stock-table-wrap'); wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Scrollable data table');
    const t = node('table', 'stock-table'), head = node('thead'), tr = node('tr'), body = node('tbody');
    headers.forEach(h => { const th = node('th', '', h); th.scope = 'col'; tr.append(th); }); head.append(tr);
    rows.forEach(row => { const r = node('tr'); row.forEach(value => { const td = node('td'); if (value instanceof Node) td.append(value); else td.textContent = value === null || value === undefined ? '—' : String(value); r.append(td); }); body.append(r); });
    t.append(head, body); wrap.append(t); return wrap;
  }
  // A bounded, semantic fallback keeps less common provider fields accessible.
  function dataView(value, depth = 0) {
    if (!has(value)) return empty();
    if (depth > 8) return empty('Additional nested detail is unavailable.');
    if (typeof value !== 'object') return node('p', 'stock-prose', fmt(value));
    if (Array.isArray(value)) {
      if (value.every(v => !v || typeof v !== 'object')) return node('p', 'stock-prose', value.map(fmt).join(' · '));
      const records = value.filter(v => v && typeof v === 'object');
      if (records.length && records.every(v => ('value' in v) && ('displayName' in v || 'key' in v))) {
        return table(['Metric', 'Reported value', 'Comparisons'], records.map(v => [v.displayName || label(v.key), fmt(v.value), [v.qoQComp, v.yqoQComp].filter(has).map(fmt).join(' · ') || '—']));
      }
      const keys = [...new Set(records.flatMap(v => Object.keys(v)))];
      const simple = keys.filter(k => records.every(v => v[k] === null || typeof v[k] !== 'object'));
      const box = node('div');
      if (simple.length) box.append(table(simple.map(label), records.map(v => simple.map(k => field(v[k], k)))));
      records.forEach((v, i) => { const nested = Object.fromEntries(Object.entries(v).filter(([, x]) => x && typeof x === 'object')); if (has(nested)) box.append(details(v.displayName || v.name || v.holdingDate || 'Record ' + (i + 1), dataView(nested, depth + 1))); });
      return box;
    }
    const box = node('div'); const entries = Object.entries(value), simple = entries.filter(([, v]) => v === null || typeof v !== 'object');
    if (simple.length) box.append(factList(simple.map(([k, v]) => [label(k), field(v, k)])));
    entries.filter(([, v]) => v && typeof v === 'object').forEach(([k, v]) => box.append(details(label(k), dataView(v, depth + 1))));
    return box;
  }
  const requests = new Map();
  function request(section, params = {}) {
    const query = new URLSearchParams({symbol, section, ...params}), key = query.toString();
    if (requests.has(key)) return requests.get(key);
    const promise = fetch('/api/stock-data?' + key).then(async response => {
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Unable to load this section.');
      return data;
    }).catch(error => { requests.delete(key); throw error; });
    requests.set(key, promise); return promise;
  }
  function requestAI() {
    const key = 'ai-overview:' + symbol;
    if (requests.has(key)) return requests.get(key);
    const promise = fetch('/api/stock-ai?' + new URLSearchParams({symbol, schema: '2'})).then(async response => {
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Unable to generate the AI overview.');
      return data;
    }).catch(error => { requests.delete(key); throw error; });
    requests.set(key, promise); return promise;
  }
  async function loadInto(target, section, params, render, onEmpty) {
    const version = (target._requestVersion || 0) + 1; target._requestVersion = version;
    target.replaceChildren(node('div', 'stock-state loading', 'Loading ' + label(section).toLowerCase() + '…'));
    target.setAttribute('aria-busy', 'true');
    try {
      const response = await request(section, params);
      if (version !== target._requestVersion) return;
      target.replaceChildren();
      if (!has(response.data)) { if (onEmpty) onEmpty(); else target.append(empty()); return; }
      const rendered = render(target, response.data);
      if (rendered === false) { target.replaceChildren(); if (onEmpty) onEmpty(); else target.append(empty()); return; }
      target.append(node('p', 'stock-chart-note', 'Retrieved ' + stamp(response.fetched_at) + ' · IndianAPI'));
    } catch (error) {
      if (version !== target._requestVersion) return;
      const state = node('div', 'stock-state'); state.setAttribute('role', 'status'); state.append(node('p', '', error.message));
      const retry = node('button', 'stock-retry', 'Try again'); retry.type = 'button'; retry.onclick = () => loadInto(target, section, params, render, onEmpty); state.append(retry); target.replaceChildren(state);
    } finally { if (version === target._requestVersion) target.removeAttribute('aria-busy'); }
  }
  function metric(title, value, note, tone = 'neutral') { const box = node('div', 'stock-metric tone-' + tone); box.append(node('span', '', title), node('strong', '', value)); if (note) box.append(node('small', '', note)); return box; }
  function bars(rows, unit, stacked = false) {
    const box = node('div', 'stock-bars'); const valid = rows.filter(x => number(x.value) !== null);
    if (!valid.length) return empty();
    const total = valid.reduce((sum, x) => sum + Math.max(0, number(x.value)), 0);
    if (stacked && total > 0) { const strip = node('div', 'stock-stacked-bar'); valid.forEach((row, i) => { const segment = node('span'); segment.style.width = Math.max(0, number(row.value)) / total * 100 + '%'; segment.style.background = colors[i % colors.length]; segment.title = row.label + ': ' + fmt(row.value) + unit; strip.append(segment); }); box.append(strip); }
    valid.forEach((row, i) => { const item = node('div'), top = node('div', 'stock-bar-label'), track = node('div', 'stock-bar-track'), fill = node('div', 'stock-bar-fill'); top.append(node('span', '', row.label), node('strong', '', fmt(row.value) + unit)); fill.style.width = Math.max(0, Math.min(100, unit === '%' ? number(row.value) : total ? number(row.value) / total * 100 : 0)) + '%'; fill.style.setProperty('--bar-color', row.color || colors[i % colors.length]); if (row.tone) top.lastChild.classList.add('tone-' + row.tone); track.append(fill); item.append(top, track); box.append(item); }); return box;
  }
  const svgNS = 'http://www.w3.org/2000/svg';
  function svgNode(tag, attrs, text) { const n = document.createElementNS(svgNS, tag); Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v)); if (text !== undefined) n.textContent = text; return n; }
  function chart(target, datasets, title = 'Price history', unit = '₹') {
    const series = (datasets || []).filter(x => Array.isArray(x.values)).map(s => ({...s, values: s.values.filter(v => Array.isArray(v) && number(v[1]) !== null && Number.isFinite(Date.parse(v[0]))).map(v => [v[0], number(v[1])]).sort((a, b) => Date.parse(a[0]) - Date.parse(b[0]))})).filter(s => s.values.length);
    const price = series.find(s => s.metric === 'Price') || series.find(s => s.metric !== 'Volume');
    if (!price) return false;
    const trend = price.metric === 'Price' ? direction(price.values.at(-1)[1] - price.values[0][1]) : 'neutral';
    const priceColor = trend === 'positive' ? 'var(--pill-up-fg)' : trend === 'negative' ? 'var(--pill-down-fg)' : colors[0];
    const W = 720, H = 245, left = 58, right = 12, top = 18, bottom = 171, plotW = W - left - right;
    const lines = series.filter(s => s.metric !== 'Volume'), all = lines.flatMap(s => s.values.map(v => v[1]));
    let low = Math.min(...all), high = Math.max(...all); const pad = (high - low) * .08 || Math.abs(high) * .05 || 1; low -= pad; high += pad;
    const dates = series.flatMap(s => s.values.map(v => Date.parse(v[0]))), start = Math.min(...dates), end = Math.max(...dates);
    const x = value => left + (Date.parse(value) - start) / (end - start || 1) * plotW, y = value => bottom - (value - low) / (high - low) * (bottom - top);
    const svg = svgNode('svg', {viewBox: `0 0 ${W} ${H}`, class: 'stock-chart', tabindex: '0', role: 'img', 'aria-label': title + '. Use left and right arrows to explore values. Full data table follows.'});
    svg.append(svgNode('title', {}, title));
    for (let i = 0; i < 5; i++) { const value = low + (high - low) * i / 4, yy = y(value); svg.append(svgNode('line', {x1: left, y1: yy, x2: W - right, y2: yy, class: 'grid-line'}), svgNode('text', {x: left - 8, y: yy + 3, 'text-anchor': 'end'}, new Intl.NumberFormat('en-IN', {notation: 'compact', maximumFractionDigits: 1}).format(value))); }
    const volume = series.find(s => s.metric === 'Volume');
    if (volume) { const max = Math.max(...volume.values.map(v => v[1]), 1); volume.values.forEach(v => svg.append(svgNode('rect', {x: x(v[0]), y: 215 - v[1] / max * 24, width: Math.max(.7, Math.min(6, plotW / volume.values.length * .7)), height: v[1] / max * 24, class: 'volume-bar'}))); }
    lines.forEach((s, i) => svg.append(svgNode('path', {d: s.values.map((v, j) => (j ? 'L' : 'M') + x(v[0]).toFixed(2) + ',' + y(v[1]).toFixed(2)).join(' '), fill: 'none', stroke: s === price ? priceColor : colors[i % colors.length], 'stroke-width': s === price ? 2.5 : 1.3, 'stroke-dasharray': s === price ? '' : '5 4'})));
    [0, .5, 1].forEach(t => svg.append(svgNode('text', {x: left + plotW * t, y: H - 7, 'text-anchor': t === 0 ? 'start' : t === 1 ? 'end' : 'middle'}, date(new Date(start + (end - start) * t).toISOString()))));
    const cursor = svgNode('line', {x1: 0, y1: top, x2: 0, y2: 217, stroke: 'var(--text-muted)', 'stroke-dasharray': '3 3', visibility: 'hidden'}), dot = svgNode('circle', {r: 4, fill: priceColor, visibility: 'hidden'}); svg.append(cursor, dot);
    const readout = node('p', 'stock-chart-readout'); readout.setAttribute('aria-live', 'polite');
    let active = price.values.length - 1;
    function inspect(index) { active = Math.max(0, Math.min(price.values.length - 1, index)); const point = price.values[active]; cursor.setAttribute('x1', x(point[0])); cursor.setAttribute('x2', x(point[0])); cursor.setAttribute('visibility', 'visible'); dot.setAttribute('cx', x(point[0])); dot.setAttribute('cy', y(point[1])); dot.setAttribute('visibility', 'visible'); const vol = volume && volume.values.find(v => v[0] === point[0]); readout.textContent = date(point[0]) + ' · ' + price.label + ' ' + (unit === '₹' ? money(point[1]) : fmt(point[1]) + (unit ? ' ' + unit : '')) + (vol ? ' · Volume ' + fmt(vol[1]) : ''); }
    svg.addEventListener('pointermove', event => { const rect = svg.getBoundingClientRect(), relative = (event.clientX - rect.left) / rect.width * W; let best = 0; price.values.forEach((v, i) => { if (Math.abs(x(v[0]) - relative) < Math.abs(x(price.values[best][0]) - relative)) best = i; }); inspect(best); });
    svg.addEventListener('keydown', event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); inspect(event.key === 'Home' ? 0 : event.key === 'End' ? price.values.length - 1 : active + (event.key === 'ArrowLeft' ? -1 : 1)); } });
    const legend = node('div', 'stock-chart-legend'); series.forEach(s => { const item = node('span', '', s.label || s.metric); item.style.setProperty('--series-color', s.metric === 'Volume' ? 'var(--accent)' : s === price ? priceColor : colors[lines.indexOf(s) % colors.length]); legend.append(item); });
    target.append(readout, svg, legend); inspect(active);
    if (price.metric === 'Price' && price.values[0][1] > 0) { const change = (price.values.at(-1)[1] / price.values[0][1] - 1) * 100; legend.append(indicator(pct(change) + ' over selected range', trend)); }
    const tableBody = node('div'), disclosure = details('View chart data', tableBody);
    disclosure.addEventListener('toggle', () => {
      if (!disclosure.open || tableBody.childElementCount) return;
      const indexes = series.map(s => new Map(s.values));
      const days = [...new Set(series.flatMap(s => s.values.map(v => v[0])))].sort().reverse();
      tableBody.append(table(['Date', ...series.map(s => (s.label || s.metric) + (s.metric === 'Volume' ? ' (shares)' : ' (' + unit + ')'))],
        days.map(d => [date(d), ...indexes.map(index => fmt(index.get(d)))])));
    });
    target.append(disclosure); return true;
  }
  function peChart(target, datasets) {
    const source = (datasets || []).find(series => Array.isArray(series.values) && (/((^|[^a-z])pe([^a-z]|$)|earnings)/i.test(String(series.metric || '') + ' ' + String(series.label || '')) || datasets.length === 1));
    if (!source) return false;
    const points = source.values.filter(value => Array.isArray(value) && finite(value[1]) && number(value[1]) !== 0 && Number.isFinite(Date.parse(value[0])))
      .map(value => [value[0], number(value[1])]).sort((a, b) => Date.parse(a[0]) - Date.parse(b[0]));
    if (!points.length) return false;
    const ordered = points.map(point => point[1]).sort((a, b) => a - b), middle = Math.floor(ordered.length / 2);
    const median = ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
    const low = ordered[0], high = ordered.at(-1), current = points.at(-1)[1];
    const metrics = node('div', 'stock-metrics stock-pe-metrics');
    [['Current P/E', current], ['Median', median], ['Low', low], ['High', high]].forEach(([title, value]) => metrics.append(metric(title, fmt(value) + '×')));
    target.append(metrics);

    const W = 720, H = 245, left = 58, right = 12, top = 18, bottom = 210, plotW = W - left - right;
    let min = low, max = high; const pad = (max - min) * .08 || Math.abs(max) * .05 || 1; min -= pad; max += pad;
    const start = Date.parse(points[0][0]), end = Date.parse(points.at(-1)[0]);
    const x = value => left + (Date.parse(value) - start) / (end - start || 1) * plotW;
    const y = value => bottom - (value - min) / (max - min) * (bottom - top);
    const svg = svgNode('svg', {viewBox: `0 0 ${W} ${H}`, class: 'stock-chart', tabindex: '0', role: 'img', 'aria-label': 'Historical price-to-earnings ratio. Use left and right arrows to explore values. Full data table follows.'});
    svg.append(svgNode('title', {}, 'Historical price-to-earnings ratio'));
    for (let i = 0; i < 5; i++) { const value = min + (max - min) * i / 4, yy = y(value); svg.append(svgNode('line', {x1: left, y1: yy, x2: W - right, y2: yy, class: 'grid-line'}), svgNode('text', {x: left - 8, y: yy + 3, 'text-anchor': 'end'}, fmt(value) + '×')); }
    svg.append(svgNode('line', {x1: left, y1: y(median), x2: W - right, y2: y(median), class: 'pe-median-line'}));
    svg.append(svgNode('path', {d: points.map((point, index) => (index ? 'L' : 'M') + x(point[0]).toFixed(2) + ',' + y(point[1]).toFixed(2)).join(' '), class: 'pe-history-line'}));
    [0, .5, 1].forEach(t => svg.append(svgNode('text', {x: left + plotW * t, y: H - 7, 'text-anchor': t === 0 ? 'start' : t === 1 ? 'end' : 'middle'}, date(new Date(start + (end - start) * t).toISOString()))));
    const cursor = svgNode('line', {x1: 0, y1: top, x2: 0, y2: bottom, stroke: 'var(--text-muted)', 'stroke-dasharray': '3 3', visibility: 'hidden'});
    const dot = svgNode('circle', {r: 4, fill: 'var(--accent)', visibility: 'hidden'}); svg.append(cursor, dot);
    const readout = node('p', 'stock-chart-readout'); readout.setAttribute('aria-live', 'polite'); let active = points.length - 1;
    function inspect(index) { active = Math.max(0, Math.min(points.length - 1, index)); const point = points[active]; cursor.setAttribute('x1', x(point[0])); cursor.setAttribute('x2', x(point[0])); cursor.setAttribute('visibility', 'visible'); dot.setAttribute('cx', x(point[0])); dot.setAttribute('cy', y(point[1])); dot.setAttribute('visibility', 'visible'); readout.textContent = date(point[0]) + ' · P/E ' + fmt(point[1]) + '×'; }
    svg.addEventListener('pointermove', event => { const rect = svg.getBoundingClientRect(), relative = (event.clientX - rect.left) / rect.width * W; let best = 0; points.forEach((point, index) => { if (Math.abs(x(point[0]) - relative) < Math.abs(x(points[best][0]) - relative)) best = index; }); inspect(best); });
    svg.addEventListener('keydown', event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) { event.preventDefault(); inspect(event.key === 'Home' ? 0 : event.key === 'End' ? points.length - 1 : active + (event.key === 'ArrowLeft' ? -1 : 1)); } });
    const legend = node('div', 'stock-chart-legend'), seriesLabel = node('span', '', 'P/E ratio'), medianLabel = node('span', 'pe-median-legend', 'Median ' + fmt(median) + '×');
    seriesLabel.style.setProperty('--series-color', 'var(--accent)'); legend.append(seriesLabel, medianLabel);
    target.append(readout, svg, legend, details('View P/E data', table(['Date', 'P/E'], points.slice().reverse().map(point => [date(point[0]), fmt(point[1]) + '×'])))); inspect(active); return true;
  }
  let core;
  function historyCard() {
    const c = card('The price story', 'Price, moving averages and trading volume.');
    const controls = node('div', 'stock-controls'); controls.setAttribute('aria-label', 'Price history range'); const target = node('div');
    [['1m','1M'],['6m','6M'],['1yr','1Y'],['3yr','3Y'],['5yr','5Y'],['10yr','10Y'],['max','Max']].forEach(([period, title]) => { const b = node('button', '', title); b.type = 'button'; b.setAttribute('aria-pressed', String(period === '1yr')); b.onclick = () => { controls.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); loadInto(target, 'history', {period}, (t, d) => chart(t, d.datasets)); }; controls.append(b); });
    c.append(controls, target); loadInto(target, 'history', {period: '1yr'}, (t, d) => chart(t, d.datasets)); return c;
  }
  function peHistoryCard() {
    const c = card('P/E valuation history', 'Historical price-to-earnings ratio with its median.'); c.classList.add('stock-history-card');
    const controls = node('div', 'stock-controls'); controls.setAttribute('aria-label', 'P/E history range'); const target = node('div');
    const load = (period, button) => { controls.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button))); loadInto(target, 'history', {period, filter: 'pe'}, (container, data) => peChart(container, data.datasets), () => c.remove()); };
    [['1m','1M'],['6m','6M'],['1yr','1Y'],['3yr','3Y'],['5yr','5Y'],['10yr','10Y'],['max','Max']].forEach(([period, title]) => { const button = node('button', '', title); button.type = 'button'; button.setAttribute('aria-pressed', String(period === '1yr')); button.onclick = () => load(period, button); controls.append(button); });
    c.append(controls, target); const initial = controls.querySelector('[aria-pressed=true]'); load('1yr', initial); return c;
  }
  function overview() {
    const panel = $('panel-overview'), s = core.snapshot || {}, metrics = node('div', 'stock-metrics');
    if (finite(s.marketCap)) metrics.append(metric('Market cap', '₹' + fmt(s.marketCap) + ' cr', 'Reported market capitalisation'));
    if (finite(s.pPerEBasicExcludingExtraordinaryItemsTTM)) metrics.append(metric('P/E ratio', fmt(s.pPerEBasicExcludingExtraordinaryItemsTTM) + '×', 'Trailing 12 months'));
    if (finite(s.currentDividendYieldCommonStockPrimaryIssueLTM)) metrics.append(metric('Dividend yield', fmt(s.currentDividendYieldCommonStockPrimaryIssueLTM) + '%', 'Last 12 months'));
    if (finite(s.priceYTDPricePercentChange)) metrics.append(metric('Year to date', pct(s.priceYTDPricePercentChange), 'Price return', direction(s.priceYTDPricePercentChange)));
    if (metrics.childElementCount) panel.append(metrics);
    const signals = card('Company signals', 'A quick read of the latest evidence-backed AI overview.');
    signals.classList.add('stock-signals-preview');
    const signalBody = node('div', 'stock-signals-preview-body');
    signals.append(signalBody);
    panel.append(signals);
    loadSignalPreview(signalBody);
    const grid = node('div', 'stock-grid'), left = node('div', 'stock-stack'), right = node('div', 'stock-stack'); left.append(historyCard(), peHistoryCard());
    const range = card('Price context', 'Reported price landmarks · ₹');
    const low = core.year_low, high = core.year_high, current = core.prices.NSE ?? core.prices.BSE;
    if (number(low) !== null && number(high) !== null && high > low && current !== null) { const bar = node('div', 'stock-range'), dot = node('i'); dot.style.left = Math.max(0, Math.min(100, (current - low) / (high - low) * 100)) + '%'; bar.append(dot); range.append(bar); }
    const limits = node('div', 'stock-range-labels'); [low, high].forEach((v, i) => { const part = node('span', '', money(v)); part.append(node('small', '', i ? '52-week high' : '52-week low')); limits.append(part); }); range.append(limits, factList([['Day high', money(s.high)], ['Day low', money(s.low)], ['Previous close', money(s.close)], ['5-day return', indicator(pct(s.price5DayPercentChange), direction(s.price5DayPercentChange))], ['Sector P/E', fmt(s.sectorPriceToEarningsValueRatio)]])); right.append(range);
    const health = card('Financial pulse', core.health ? 'Reported fundamentals · ' + (core.health.period_label || core.health.end_date || '') : 'Latest available fundamentals');
    if (core.health && core.health.groups) { const all = core.health.groups.flatMap(g => g.metrics || []); health.append(factList(['revenue', 'net_profit', 'fcf', 'net_debt'].map(id => { const m = all.find(x => x.id === id); return [m ? m.label : label(id), m ? indicator(fmt(m.value) + ' ' + (m.unit || ''), m.value_tone, m.change_label || '') : '—']; }))); const more = node('button', 'stock-text-button', 'Explore all financials →'); more.onclick = () => activate('financials', true); health.append(more); } else health.append(empty()); right.append(health);
    const about = card('Behind the ticker', 'The business, its people and its place in the market.');
    const description = node('p', 'stock-prose stock-description', core.profile.companyDescription || 'A company description is not available.'); about.append(description);
    if ((core.profile.companyDescription || '').length > 500) { const toggle = node('button', 'stock-text-button', 'Read full company profile'); toggle.setAttribute('aria-expanded', 'false'); toggle.onclick = () => { const expanded = description.classList.toggle('expanded'); toggle.textContent = expanded ? 'Show less' : 'Read full company profile'; toggle.setAttribute('aria-expanded', String(expanded)); }; about.append(toggle); }
    const profile = {...core.profile}; delete profile.companyDescription; delete profile.officers;
    about.append(details('Company information', dataView(profile)));
    const officers = core.profile.officers && core.profile.officers.officer;
    if (Array.isArray(officers) && officers.length) { const people = node('div'); officers.forEach(p => { const person = node('div', 'stock-person'); person.append(node('strong', '', [p.firstName, p.mI, p.lastName].filter(Boolean).join(' ')), node('span', '', p.title && p.title.Value || '')); people.append(person); }); about.append(details('Leadership', people), details('Leadership details', dataView(officers))); }
    left.append(about); grid.append(left, right); panel.append(grid);
    const peers = card('In good company', 'Peers reported by IndianAPI · Prices in ₹ · Market cap in ₹ crore'); peers.classList.add('stock-full'); peers.style.marginTop = '14px';
    if (core.peers.length) {
      peers.append(table(['Company', 'Price', 'Change', 'Market cap', 'P/E', 'P/B'], core.peers.map(p => { const link = node(p.symbol ? 'a' : 'button', p.symbol ? '' : 'stock-text-button', p.companyName); if (p.symbol) link.href = '/stocks/' + encodeURIComponent(p.symbol).replace('%3A', ':'); else link.onclick = () => window.tickrStockSearch.openPeer(link, p.companyName); return [link, money(p.price), indicator(pct(p.percentChange), direction(p.percentChange)), fmt(p.marketCap), fmt(p.priceToEarningsValueRatio), fmt(p.priceToBookValueRatio)]; })));
      peers.append(details('Full peer metrics', dataView(core.peers)));
    } else peers.append(empty()); panel.append(peers);
  }
  async function loadSignalPreview(target) {
    target.replaceChildren(node('p', 'stock-caption', 'Gathering company signals…'));
    try {
      const response = await requestAI(), data = response.data || {};
      if (!data.summary || !data.summary.text) throw new Error('Company signals are unavailable.');
      const sources = new Map((data.sources || []).map(source => [source.id, source]));
      const lead = node('div', 'stock-signals-preview-lead');
      lead.append(node('strong', '', data.summary.heading || 'Company perspective'));
      const description = node('p', '', data.summary.text);
      description.append(aiEvidence(data.summary.evidence_ids, sources));
      lead.append(description);
      const areas = node('div', 'stock-signals-preview-grid');
      const groups = [['encouraging', 'Encouraging'], ['attention', 'Needs attention'], ['changes', 'Recent changes'],
        ['catalysts', 'Catalysts'], ['risks', 'Key risks'], ['watch_next', 'Watch next']];
      groups.forEach(([key, label]) => {
        const items = Array.isArray(data[key]) ? data[key] : [];
        if (!items.length) return;
        const area = node('div', 'stock-signals-preview-area');
        area.append(node('span', '', label), node('strong', '', String(items.length)));
        area.append(node('p', '', items[0].heading || 'Company signal'));
        areas.append(area);
      });
      const link = node('a', 'stock-signals-preview-link', 'See all signals and sources →');
      link.href = '/ai-overview/' + encodeURIComponent(symbol).replace('%3A', ':');
      target.replaceChildren(...(areas.children.length ? [lead, areas, link] : [lead, link]));
    } catch (error) {
      const retry = node('button', 'stock-text-button', 'Retry company signals');
      retry.type = 'button'; retry.onclick = () => loadSignalPreview(target);
      target.replaceChildren(node('p', 'stock-caption', error.message), retry);
    }
  }
  function aiEvidence(ids, sources) {
    const links = node('span', 'stock-ai-evidence');
    (ids || []).forEach(id => {
      const source = sources.get(id); if (!source) return;
      const link = node('a', '', id); link.href = '#' + source.section;
      link.title = 'View source: ' + source.label;
      link.setAttribute('aria-label', id + ': ' + source.label);
      links.append(link);
    });
    return links;
  }
  function aiTone(value, fallback) { return ['positive', 'negative', 'caution', 'neutral'].includes(value) ? value : fallback; }
  function aiSignal(item, sources, fallbackHeading, fallbackTone, lead) {
    const tone = aiTone(item && item.tone, fallbackTone), signal = node('div', 'stock-ai-insight signal-' + tone);
    const head = node('div', 'stock-ai-insight-head'), heading = node('h3', '', item && item.heading || fallbackHeading);
    const toneLabel = node('span', 'stock-ai-tone', ({positive: 'Positive', negative: 'Negative', caution: 'Watch', neutral: 'Neutral'})[tone]);
    head.append(heading, toneLabel);
    const body = node('p', lead ? 'stock-ai-lead' : '', item && item.text || 'A reliable insight could not be generated.');
    if (item) body.append(aiEvidence(item.evidence_ids, sources));
    signal.append(head, body); return signal;
  }
  function aiInsightList(items, sources, fallbackHeading, fallbackTone) {
    const list = node('ul', 'stock-ai-list');
    items.forEach(item => { const li = node('li'); li.append(aiSignal(item, sources, fallbackHeading, fallbackTone, false)); list.append(li); });
    return list;
  }
  function renderAIOverview(panel, response) {
    const data = response.data || {}, sources = new Map((data.sources || []).map(source => [source.id, source]));
    const intro = card('The 60-second view', 'A concise synthesis of the latest available company evidence.'); intro.classList.add('stock-ai-summary');
    intro.append(aiSignal(data.summary, sources, 'Overall picture', 'caution', true)); panel.append(intro);

    function signalGroup(key, title, caption, className, fallbackHeading, fallbackTone) {
      const items = Array.isArray(data[key]) ? data[key] : [];
      if (!items.length) return null;
      const group = card(title, caption);
      if (className) group.classList.add(className);
      group.append(aiInsightList(items, sources, fallbackHeading, fallbackTone));
      return group;
    }
    function appendPair(first, second, className = 'stock-grid') {
      const groups = [first, second].filter(Boolean);
      if (groups.length === 1) panel.append(groups[0]);
      else if (groups.length === 2) { const grid = node('div', className); grid.append(...groups); panel.append(grid); }
    }

    appendPair(
      signalGroup('encouraging', 'What looks encouraging', '', 'stock-ai-positive', 'Positive signal', 'positive'),
      signalGroup('attention', 'What needs attention', '', 'stock-ai-caution', 'Downside signal', 'negative'),
      'stock-grid stock-ai-balance');
    const changes = signalGroup('changes', 'What changed recently', 'Only explicit period-over-period changes are included.', '', 'Recent movement', 'caution');
    if (changes) panel.append(changes);
    appendPair(
      signalGroup('catalysts', 'Potential catalysts', 'Reported events, plans or developments—not predictions.', 'stock-ai-positive', 'Potential catalyst', 'positive'),
      signalGroup('risks', 'Key risks', '', 'stock-ai-negative', 'Risk factor', 'negative'));
    const watch = signalGroup('watch_next', 'What to watch next', 'Measurable questions for future results and disclosures.', '', 'Monitoring point', 'neutral');
    if (watch) panel.append(watch);

    const sourceCard = card('Sources and freshness'); sourceCard.classList.add('stock-ai-sources');
    const sourceList = node('ol');
    (data.sources || []).forEach(source => { const item = node('li'), link = node('a', '', source.label); link.href = '#' + source.section; item.append(link, node('span', '', ' · ' + label(source.section))); sourceList.append(item); });
    sourceCard.append(sourceList);
    const coverage = response.coverage || {}, meta = node('p', 'stock-caption');
    meta.textContent = 'Generated ' + stamp(data.generated_at) + ' · ' + fmt(coverage.sources) + ' evidence groups · ' + fmt(coverage.news_stories) + ' available news stories · Cached for up to 6 hours';
    sourceCard.append(meta, node('p', 'stock-ai-disclaimer', 'AI-generated synthesis · Not investment advice · Coverage may be incomplete or delayed.'));
    panel.append(sourceCard);
  }
  async function aiOverview() {
    const panel = $('panel-ai-overview');
    panel.replaceChildren(node('div', 'stock-state loading', 'Building a concise overview from the latest evidence…'));
    panel.setAttribute('aria-busy', 'true');
    try {
      const response = await requestAI(); panel.replaceChildren(); renderAIOverview(panel, response);
    } catch (error) {
      const state = node('div', 'stock-state'); state.setAttribute('role', 'status'); state.append(node('p', '', error.message));
      const retry = node('button', 'stock-retry', 'Try again'); retry.type = 'button'; retry.onclick = aiOverview; state.append(retry); panel.replaceChildren(state);
    } finally { panel.removeAttribute('aria-busy'); }
  }
  function periodSort(a, b) { const aa = Date.parse('1 ' + a), bb = Date.parse('1 ' + b); return Number.isFinite(aa) && Number.isFinite(bb) ? aa - bb : a.localeCompare(b); }
  function historyTable(target, data, series) {
    const rows = Object.entries(data || {}).filter(([, v]) => v && typeof v === 'object' && !Array.isArray(v));
    const periods = [...new Set(rows.flatMap(([, v]) => Object.keys(v)))].sort(periodSort);
    if (!rows.length || !periods.length) { target.append(empty()); return; }
    const owner = series.startsWith('shareholding'), ratio = series === 'ratios';
    const chartRow = rows.find(([k]) => /^(Sales|Net Profit|Cash from Operating Activity|Promoters|ROCE %|Total Assets)$/i.test(k)) || rows[0];
    const unit = owner ? /shareholder/i.test(chartRow[0]) ? 'holders' : '%' : ratio ? /%/.test(chartRow[0]) ? '%' : 'days' : /EPS/i.test(chartRow[0]) ? '₹' : '₹ cr';
    const values = periods.map(p => { const timestamp = Date.parse('1 ' + p); return [Number.isFinite(timestamp) ? new Date(timestamp).toISOString().slice(0, 10) : '', chartRow[1][p]]; });
    chart(target, [{metric: chartRow[0], label: chartRow[0], values}], chartRow[0] + ' history', unit);
    target.append(table(['Metric', ...periods.slice().reverse()], rows.map(([k, v]) => { let rowUnit = owner ? /shareholder/i.test(k) ? 'holders' : '%' : ratio ? /%/.test(k) ? '%' : 'days' : /%|margin/i.test(k) ? '%' : /EPS/i.test(k) ? '₹' : '₹ cr'; return [k + ' (' + rowUnit + ')', ...periods.slice().reverse().map(p => fmt(v[p]))]; })));
  }
  function supplement(title, options, initial) {
    const c = card(title, 'Explore reported history. Each series keeps its own reporting periods.');
    c.classList.add('stock-history-card');
    const controls = node('div', 'stock-controls'), select = node('select', 'stock-select'); select.setAttribute('aria-label', title + ' series'); options.forEach(value => { const opt = node('option', '', label(value)); opt.value = value; select.append(opt); }); select.value = initial;
    const content = node('div'); select.onchange = () => { const series = select.value; loadInto(content, 'financials', {series}, (t, d) => historyTable(t, d, series)); }; controls.append(select); c.append(controls, content); select.onchange(); return c;
  }
  function statementsView() {
    const box = card('Full financial statements', 'Amounts in ₹ crore; EPS and per-share values in ₹. Share counts are in crore. Reporting metadata is preserved for each statement.');
    const controls = node('div', 'stock-controls'), select = node('select', 'stock-select'); select.setAttribute('aria-label', 'Financial statement period and basis');
    core.financials.forEach((s, i) => { const o = node('option', '', (s.Type || 'Reported') + ' · ' + date(s.EndDate) + (s.consolidated || s.basis ? ' · ' + (s.consolidated || s.basis) : '')); o.value = i; select.append(o); });
    const content = node('div');
    select.onchange = () => { const s = core.financials[Number(select.value)]; content.replaceChildren(); if (!s) { content.append(empty()); return; }
      const meta = {...s}; delete meta.stockFinancialMap;
      content.append(details('Reporting period & basis', dataView(meta)));
      Object.entries(s.stockFinancialMap || {}).forEach(([k, rows]) => {
        if (!Array.isArray(rows)) { content.append(details(label(k), dataView(rows))); return; }
        const valueRows = rows.map(row => [row.displayName || label(row.key), fmt(row.value), statementUnit(row.key), fmt(row.qoQComp), fmt(row.yqoQComp)]);
        content.append(details(label(k), table(['Line item', 'Value', 'Unit', 'QoQ comparison', 'YoY comparison'], valueRows), k === 'INC'));
      });
    }; controls.append(select); box.append(controls, content); select.onchange(); return box;
  }
  function financials() {
    const panel = $('panel-financials'), stack = node('div', 'stock-stack');
    stack.append(supplement('Financial history', ['quarter_results', 'yoy_results', 'balancesheet', 'cashflow', 'ratios'], 'quarter_results'));
    if (core.health) { const c = card('Financial health', 'Reported fundamentals, with comparable changes where available.');
      (core.health.groups || []).forEach(g => c.append(details(g.title || g.name || 'Fundamentals', table(['Metric', 'Value', 'Period', 'Change'], (g.metrics || []).map(m => [m.label, indicator(fmt(m.value) + ' ' + (m.unit || ''), m.value_tone), m.period || core.health.end_date || '—', indicator(m.change_label || '—', m.change_tone)])), true))); stack.append(c); }
    stack.append(statementsView());
    const metrics = card('Every metric, in context', 'Provider periods and labels are preserved. “Provider units” means the monetary scale is unspecified; these values are not mixed with statement amounts.');
    Object.entries(core.metrics || {}).forEach(([group, rows]) => metrics.append(details(label(group), Array.isArray(rows) ? table(['Metric & reporting period', 'Value', 'Unit'], rows.map(row => [row.displayName || label(row.key), fmt(row.value), metricUnit(group, row.key)])) : dataView(rows))));
    stack.append(metrics); if (has(core.additional_financials)) { const extra = card('Additional financial data'); extra.append(dataView(core.additional_financials)); stack.append(extra); } panel.append(stack);
  }
  function ownership() {
    const panel = $('panel-ownership'), grid = node('div', 'stock-grid'), c = card('Who owns the company?', 'Shareholding categories as reported by IndianAPI.');
    const dates = core.ownership.flatMap(x => (x.categories || []).map(v => v.holdingDate)).filter(Boolean).sort(); const latest = dates[dates.length - 1];
    c.append(node('p', 'stock-caption', latest ? 'As of ' + date(latest) : 'Reporting date unavailable'));
    c.append(bars(core.ownership.map(x => ({label: x.displayName || x.categoryName, value: (x.categories || []).find(v => v.holdingDate === latest)?.percentage})), '%', true));
    const notes = card('Ownership detail', 'Inspect the underlying holding dates and category records.'); core.ownership.forEach(x => notes.append(details(x.categoryName || x.displayName, dataView(x.categories)))); if (!core.ownership.length) notes.append(empty());
    grid.append(c, notes); panel.append(grid); const historical = supplement('Ownership history', ['shareholding_pattern_quarterly', 'shareholding_pattern_yearly'], 'shareholding_pattern_quarterly'); historical.style.marginTop = '14px'; panel.append(historical);
  }
  function analysis() {
    const panel = $('panel-analysis'), grid = node('div', 'stock-grid');
    if (Array.isArray(core.technical) && core.technical.some(row => finite(row.nsePrice) || finite(row.bsePrice))) { const technical = card('Technical averages', 'Reported moving-average prices without trading interpretations.'); technical.append(table(['Period', 'NSE price', 'BSE price'], core.technical.filter(row => finite(row.nsePrice) || finite(row.bsePrice)).map(row => [finite(row.days) ? fmt(row.days) + ' days' : 'Reported period', finite(row.nsePrice) ? money(row.nsePrice) : '—', finite(row.bsePrice) ? money(row.bsePrice) : '—']))); grid.append(technical); }
    const risk = numericOnly(core.risk);
    if (has(risk)) { const volatility = card('Volatility statistics', 'Provider-reported numerical variability.'); volatility.append(dataView(risk)); grid.append(volatility); }
    if (grid.childElementCount) panel.append(grid);
    const stack = node('div', 'stock-stack'); if (grid.childElementCount) stack.style.marginTop = '14px';
    if (has(core.futures)) { const futures = card('Futures', 'Available contract expiries and reported futures overview.'); futures.append(dataView(core.futures)); stack.append(futures); }
    const snapshotKeys = ['marketCap','high','low','close','price','percentChange','price5DayPercentChange','priceYTDPricePercentChange','currentDividendYieldCommonStockPrimaryIssueLTM','totalDebtPerTotalEquityMostRecentQuarter','sectorPriceToEarningsValueRatio','yhigh','ylow','FiscalYear','NetIncome','interimNetIncome','mutualFundShareHolding','promoterShareHolding','date','time'];
    const snapshot = Object.fromEntries(snapshotKeys.filter(key => has(core.snapshot && core.snapshot[key])).map(key => [key, core.snapshot[key]]));
    if (has(snapshot)) { const market = card('Additional market details', 'Provider-reported market values and reporting periods.'); market.append(dataView(snapshot)); stack.append(market); }
    if (stack.childElementCount) panel.append(stack);
  }
  function actions() {
    const panel = $('panel-actions'), c = card('The company calendar', 'Dividends, capital changes and meetings. Ex-dates and record dates are shown separately.');
    Object.entries(core.actions || {}).forEach(([type, values]) => {
      const rows = Array.isArray(values) ? [...values].sort((a, b) => String(b.sortDate || b.xdDate || b.recordDate || '').localeCompare(String(a.sortDate || a.xdDate || a.recordDate || ''))) : values;
      const body = node('div');
      if (Array.isArray(rows) && rows.length && rows.some(x => x.remarks || x.recordDate || x.xdDate)) { body.append(table(['Event', 'Ex-date', 'Record date', 'Announced'], rows.map(row => [row.remarks || label(type), row.xdDate ? date(row.xdDate) : '—', row.recordDate ? date(row.recordDate) : '—', row.dateOfAnnouncement ? date(row.dateOfAnnouncement) : '—'])), details('All event fields', dataView(rows))); } else body.append(dataView(rows));
      c.append(details(label(type) + (Array.isArray(rows) ? ' · ' + rows.length : ''), body, type === 'dividend'));
    }); if (!Object.keys(core.actions).length) c.append(empty()); panel.append(c);
  }
  function news() {
    const panel = $('panel-news'); panel.append(node('p', 'stock-caption', core.news.length + ' stories returned by IndianAPI. Open a headline to read the original coverage.'));
    const grid = node('div', 'stock-news-grid'); core.news.forEach(story => { const c = node('article', 'stock-card stock-news-card'); const imageUrl = url(story.image); if (imageUrl) { const img = node('img'); img.src = imageUrl; img.alt = ''; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer'; img.onerror = () => img.remove(); c.append(img); }
      const body = node('div', 'stock-news-body'), sourceUrl = url(story.url); body.append(node('span', 'stock-news-meta', (story.source || (sourceUrl ? new URL(sourceUrl).hostname.replace('www.', '') : 'Company news')) + ' · ' + date(story.date)));
      const h = node('h2'); if (sourceUrl) { const a = node('a', '', story.headline); a.href = sourceUrl; a.target = '_blank'; a.rel = 'noopener noreferrer'; h.append(a); } else h.textContent = story.headline; body.append(h);
      if (story.summary) body.append(node('p', '', story.summary)); c.append(body); grid.append(c);
    }); panel.append(core.news.length ? grid : empty('No recent company stories are available.'));
  }
  const built = new Set(); const builders = {overview, 'ai-overview': aiOverview, financials, ownership, analysis, actions, news};
  function sectionAvailable(id) {
    if (id === 'financials') return has(core.health) || has(core.financials) || has(core.metrics) || has(core.additional_financials);
    if (id === 'ownership') return has(core.ownership);
    if (id === 'analysis') return has(core.technical) || has(numericOnly(core.risk)) || has(core.futures) || ['marketCap','high','low','close','price','percentChange','price5DayPercentChange','priceYTDPricePercentChange','currentDividendYieldCommonStockPrimaryIssueLTM','totalDebtPerTotalEquityMostRecentQuarter','sectorPriceToEarningsValueRatio','yhigh','ylow','FiscalYear','NetIncome','interimNetIncome','mutualFundShareHolding','promoterShareHolding'].some(key => has(core.snapshot && core.snapshot[key]));
    if (id === 'actions') return has(core.actions);
    if (id === 'news') return has(core.news);
    return true;
  }
  function syncAvailableSections() {
    document.querySelectorAll('[data-tab]').forEach(tab => { const available = sectionAvailable(tab.dataset.tab); tab.hidden = !available; $('panel-' + tab.dataset.tab).hidden = !available; });
  }
  function activate(id, focus) {
    if (!builders[id] || !sectionAvailable(id)) id = 'overview';
    document.querySelectorAll('[data-tab]').forEach(tab => { const selected = tab.dataset.tab === id; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; $('panel-' + tab.dataset.tab).hidden = !selected; });
    if (core && !built.has(id)) { builders[id](); built.add(id); }
    if (focus) { history.replaceState(null, '', '#' + id); $('tab-' + id).focus(); }
  }
  document.querySelectorAll('[data-tab]').forEach(tab => {
    tab.onclick = () => activate(tab.dataset.tab, true);
    tab.onkeydown = event => { const all = [...document.querySelectorAll('[data-tab]')].filter(item => !item.hidden), i = all.indexOf(tab); let next; if (event.key === 'ArrowRight') next = (i + 1) % all.length; if (event.key === 'ArrowLeft') next = (i + all.length - 1) % all.length; if (event.key === 'Home') next = 0; if (event.key === 'End') next = all.length - 1; if (next !== undefined) { event.preventDefault(); activate(all[next].dataset.tab, true); } };
  });
  window.addEventListener('hashchange', () => activate(location.hash.slice(1), false));
  const themeButton = $('theme-toggle');
  function themeLabel() { themeButton.setAttribute('aria-label', 'Switch to ' + (document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark') + ' mode'); }
  themeButton.onclick = () => { const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = theme; document.documentElement.style.colorScheme = theme; try { localStorage.setItem('daily-digest-theme', theme); } catch (e) {} themeLabel(); }; themeLabel();
  async function init() {
    if (!symbol) return;
    const status = $('stock-status'); status.hidden = false; status.classList.add('loading'); status.textContent = 'Loading your company overview…';
    try {
      const result = await request('core'); core = result.data;
      $('company-name').textContent = core.name; document.title = core.name + ' (' + symbol.replace('IN:', '') + ') — Tickr Digest';
      $('company-industry').textContent = core.industry || 'Indian equities';
      const identifiers = [symbol.replace('IN:', ''), core.profile.isInId, core.profile.exchangeCodeBse ? 'BSE ' + core.profile.exchangeCodeBse : ''].filter(Boolean); $('company-identifiers').replaceChildren(...identifiers.map(x => node('span', 'stock-tag', x)));
      const exchange = core.prices.NSE !== null ? 'NSE' : core.prices.BSE !== null ? 'BSE' : null;
      $('primary-exchange').textContent = exchange ? exchange + ' · Last traded price' : 'Price unavailable'; $('company-price').textContent = exchange ? money(core.prices[exchange]) : '—';
      const change = $('company-change'); change.textContent = pct(core.change_percent); change.classList.toggle('positive', core.change_percent > 0); change.classList.toggle('negative', core.change_percent < 0);
      $('secondary-price').textContent = exchange === 'NSE' && core.prices.BSE !== null ? 'BSE ' + money(core.prices.BSE) : '';
      $('source-time').textContent = core.source_time ? 'Provider timestamp · ' + core.source_time : 'Retrieved ' + stamp(result.fetched_at) + ' · Provider timestamp unavailable';
      syncAvailableSections(); status.hidden = true; $('stock-content').hidden = false; activate(location.hash.slice(1) || 'overview', false);
    } catch (error) {
      status.replaceChildren(node('p', '', error.message)); const retry = node('button', 'stock-retry', 'Try again'); retry.onclick = init; status.append(retry);
    } finally { status.classList.remove('loading'); }
  }
  init();
})();
