(function () {
  'use strict';

  const {number, fmt, money, pct, direction} = window.tickrStockFormat;
  const tones = {positive: 'Encouraging', negative: 'Needs attention', caution: 'Mixed or uncertain', neutral: 'Context'};
  const categories = [['changes', 'Recent change'], ['attention', 'Needs attention'],
    ['encouraging', 'Encouraging evidence'], ['risks', 'Risk'], ['watch_next', 'Watch next'], ['catalysts', 'Potential catalyst']];
  const node = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  function svgNode(tag, attrs) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }
  function icon(kind) {
    const svg = svgNode('svg', {viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true'});
    const paths = {now: 'M3 17l5-5 4 3 9-10 M15 5h6v6', recent: 'M3 12a9 9 0 1 0 3-6 M3 3v6h6 M12 7v5l3 2', watch: 'M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5 M12 17h.01', event: 'M5 5h14v15H5z M8 3v4 M16 3v4 M5 10h14 M9 14h6'};
    if (kind === 'watch') svg.append(svgNode('circle', {cx: 12, cy: 12, r: 10}));
    svg.append(svgNode('path', {d: paths[kind] || paths.watch}));
    return svg;
  }
  function tone(item) { return Object.hasOwn(tones, item?.tone) ? item.tone : 'neutral'; }
  function badge(item) { return node('span', 'ai-story-tone ' + tone(item), tones[tone(item)]); }
  function disclosure(label, ...content) {
    const el = node('details', 'ai-story-disclosure');
    el.append(node('summary', '', label), ...content);
    return el;
  }
  function citations(ids, sources, href) {
    const box = node('span', 'ai-story-citations');
    (ids || []).forEach(id => {
      const source = sources.get(id);
      if (!source) return;
      const link = node('a', '', source.label);
      link.href = href(source);
      box.append(link);
    });
    return box;
  }
  function explanation(item, sources, href, core) {
    const body = node('div', 'ai-story-explanation');
    body.append(node('p', '', item.text), citations(item.evidence_ids, sources, href));
    if (core) {
      const trend = financialTrend(item, core, sources);
      if (trend) body.append(trend.figure, disclosure('View chart data', trend.table));
    }
    return body;
  }
  function facts(item) {
    const box = node('dl', 'ai-story-facts');
    (Array.isArray(item?.facts) ? item.facts : []).slice(0, 2).forEach(fact => {
      if (!fact?.label || !fact?.value) return;
      const pair = node('div');
      pair.append(node('dt', '', fact.label), node('dd', '', fact.value));
      box.append(pair);
    });
    return box;
  }
  function stage(label, kind, item) {
    const el = node('article', 'ai-story-stage ' + kind);
    el.dataset.tone = tone(item);
    const head = node('div', 'ai-story-stage-head');
    const mark = node('span', 'ai-story-marker'); mark.append(icon(kind));
    head.append(mark, node('h3', '', label));
    el.append(head);
    return el;
  }
  function companyFacts(core) {
    const snapshot = core.snapshot || {}, list = node('dl', 'ai-story-context-facts');
    const rows = [
      ['Market cap', snapshot.marketCap, '₹ cr', 'Provider-reported'],
      ['P/E ratio', snapshot.pPerEBasicExcludingExtraordinaryItemsTTM, '×', 'Trailing 12 months'],
      ['Sector P/E', snapshot.sectorPriceToEarningsValueRatio, '×', 'Provider-reported'],
      ['Year-to-date return', snapshot.priceYTDPricePercentChange, '%', 'Price return']
    ];
    const metrics = (core.health?.groups || []).flatMap(group => group.metrics || []);
    for (const pattern of [/^(revenue|sales|total income)$/i, /^(net (income|profit)|profit after tax)$/i]) {
      const metric = metrics.find(m => pattern.test(m.label || '') && number(m.value) !== null);
      if (metric) rows.push([metric.label, metric.value, metric.unit || '', metric.period || 'Reported actual']);
    }
    rows.forEach(([label, value, unit, period]) => {
      if (number(value) === null) return;
      const pair = node('div'), dd = node('dd', '', fmt(value) + (unit === '%' || unit === '×' ? unit : unit ? ' ' + unit : ''));
      dd.append(node('small', '', period)); pair.append(node('dt', '', label), dd); list.append(pair);
    });
    return list;
  }
  function hasNowData(core) {
    const low = number(core.year_low), high = number(core.year_high);
    return number(core.prices?.NSE) !== null || number(core.prices?.BSE) !== null
      || number(core.change_percent) !== null
      || (low !== null && high !== null && low >= 0 && high > low)
      || companyFacts(core).children.length > 0;
  }
  function renderNow(core, sources = new Map(), href = () => '#overview') {
    const el = stage('Now', 'now');
    const price = number(core.prices?.NSE) ?? number(core.prices?.BSE);
    const low = number(core.year_low), high = number(core.year_high);
    const hasRange = low !== null && high !== null && low >= 0 && high > low;
    const quote = node('div', 'ai-story-quote');
    quote.append(node('span', 'ai-story-caption', 'Latest available price'), node('strong', 'ai-story-price ' + direction(core.change_percent), price === null ? '—' : money(price)));
    const change = number(core.change_percent);
    if (change !== null) quote.append(node('span', 'ai-story-change ' + direction(change), pct(change) + ' · daily change'));
    else quote.append(node('span', 'ai-story-caption', 'Daily change unavailable'));
    el.append(quote);
    if (hasRange) {
      const range = node('figure', 'ai-story-range');
      range.append(node('figcaption', '', '52-week price range'));
      const track = node('div', 'ai-story-range-track'); track.setAttribute('aria-hidden', 'true');
      if (price !== null) {
        const marker = node('span', 'ai-story-range-marker');
        marker.style.left = Math.max(0, Math.min(100, (price - low) / (high - low) * 100)) + '%';
        track.append(marker);
      }
      const ends = node('div', 'ai-story-range-labels');
      const endpoint = (value, label) => { const span = node('span'); span.append(node('strong', '', money(value)), node('small', '', label)); return span; };
      ends.append(endpoint(low, '52-week low'), endpoint(high, '52-week high'));
      range.append(track, ends);
      if (price === null) range.append(node('p', 'ai-story-caption', 'Current price unavailable'));
      else if (price < low || price > high) range.append(node('p', 'ai-story-caption', price < low ? 'Latest quote is below the reported range.' : 'Latest quote is above the reported range.'));
      el.append(range);
    } else el.append(node('p', 'ai-story-unavailable', 'A comparable 52-week range is unavailable.'));
    const body = node('div', 'ai-story-explanation');
    let meaning;
    if (hasRange && price !== null) {
      const position = (price - low) / (high - low);
      const location = position < 0 ? 'below' : position > 1 ? 'above' : 'in the ' + (position < 1 / 3 ? 'lower' : position > 2 / 3 ? 'upper' : 'middle') + ' third of';
      meaning = 'The latest share price is ' + location + ' its reported 52-week range. This shows where the price stands compared with the past year. Understanding the company’s value also requires its earnings, cash flow, and valuation.';
    } else if (price !== null) {
      meaning = 'The quote is the latest available price of one share. Daily change compares that price with the previous close. The company’s reported earnings and cash flow help explain its business performance; a comparable 52-week range is unavailable here.';
    } else {
      meaning = hasRange ? 'The 52-week low and high show the reported price extremes over the past year. The latest quote is unavailable, so its current position within that range cannot be shown.' : 'The latest quote and a comparable 52-week range are unavailable. The reported financial figures below can still provide business context when available.';
    }
    body.append(node('p', '', meaning));
    if (core.source_time) body.append(node('p', 'ai-story-caption', 'Quote as of ' + core.source_time));
    const source = [...sources.values()].find(s => s.section === 'overview' && /price|valuation/i.test(s.label));
    if (source) body.append(citations([source.id], sources, href));
    const contextFacts = companyFacts(core);
    if (contextFacts.children.length) body.append(contextFacts);
    el.append(disclosure('Why this matters', body));
    return el;
  }
  const normalized = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  function financialTrend(item, core, sources) {
    if (!(item.evidence_ids || []).some(id => sources.get(id)?.section === 'financials')) return null;
    const labels = new Set((item.facts || []).map(fact => normalized(fact.label)));
    const metrics = (core.health?.groups || []).flatMap(group => group.metrics || []);
    // Match an explicit metric label or ID. Never parse an AI fact's value as chart data.
    for (const metric of metrics) {
      if (!labels.has(normalized(metric.label)) && !labels.has(normalized(metric.id))) continue;
      const points = [...new Map((metric.history || []).filter(p => number(p.value) !== null && Number.isFinite(Date.parse(p.period)))
        .map(p => [p.period, {period: p.period, value: number(p.value)}])).values()].sort((a, b) => Date.parse(a.period) - Date.parse(b.period));
      if (points.length < 2 || Date.parse(points[0].period) === Date.parse(points.at(-1).period)) continue;
      const fig = node('figure', 'ai-story-trend');
      fig.append(node('figcaption', '', metric.label + (metric.unit ? ' · ' + metric.unit : '')));
      const values = points.map(p => p.value), min = Math.min(...values), max = Math.max(...values);
      const first = Date.parse(points[0].period), last = Date.parse(points.at(-1).period);
      const x = p => 12 + (Date.parse(p.period) - first) / (last - first) * 376;
      const y = p => max === min ? 49 : 84 - (p.value - min) / (max - min) * 70;
      const chart = svgNode('svg', {viewBox: '0 0 400 98', role: 'img', 'aria-label': metric.label + ' (' + (metric.unit || 'reported units') + '): ' + points.map(p => p.period + ': ' + fmt(p.value)).join('; ')});
      [14, 49, 84].forEach(yy => chart.append(svgNode('line', {x1: 12, x2: 388, y1: yy, y2: yy, class: 'ai-story-gridline'})));
      chart.append(svgNode('polyline', {points: points.map(p => x(p).toFixed(2) + ',' + y(p).toFixed(2)).join(' '), fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5}));
      points.forEach(p => chart.append(svgNode('circle', {cx: x(p), cy: y(p), r: 3.5, fill: 'currentColor'})));
      const labelsRow = node('div', 'ai-story-trend-labels');
      const endpoint = p => { const span = node('span'); span.append(node('strong', '', fmt(p.value) + (metric.unit ? ' ' + metric.unit : '')), node('small', '', p.period)); return span; };
      labelsRow.append(endpoint(points[0]), endpoint(points.at(-1)));
      fig.append(chart, labelsRow, node('p', 'ai-story-caption', 'Reported actuals' + (metric.period ? ' · Latest period ' + metric.period : '')));
      const table = node('table', 'ai-story-data'), head = node('thead'), row = node('tr'), body = node('tbody');
      ['Reporting period', metric.label + (metric.unit ? ' (' + metric.unit + ')' : '')].forEach(label => { const th = node('th', '', label); th.scope = 'col'; row.append(th); }); head.append(row);
      points.forEach(p => { const tr = node('tr'); tr.append(node('td', '', p.period), node('td', '', fmt(p.value))); body.append(tr); }); table.append(head, body);
      return {figure: fig, table};
    }
    return null;
  }
  function select(data) {
    const key = item => normalized(item.heading) + '|' + String(item.text || '').trim();
    const used = new Set();
    const take = keys => {
      for (const category of keys) for (const item of Array.isArray(data[category]) ? data[category] : []) {
        if (!item?.heading || !item?.text || used.has(key(item))) continue;
        used.add(key(item)); return {item, category};
      }
      return null;
    };
    const recent = take(['changes', 'attention', 'encouraging', 'risks']);
    const watch = take(['watch_next', 'catalysts']);
    const remaining = [];
    categories.forEach(([category, label]) => (Array.isArray(data[category]) ? data[category] : []).forEach(item => {
      if (!item?.heading || !item?.text || used.has(key(item))) return;
      used.add(key(item)); remaining.push({item, label, category});
    }));
    return {recent, watch, remaining};
  }
  function aiRobotFace(tone, large = false) {
    const mood = Object.hasOwn(tones, tone) ? tone : 'neutral';
    const face = node('span', 'ai-robot ' + mood + (large ? ' is-large' : ''));
    face.setAttribute('aria-hidden', 'true'); face.dataset.tone = mood;
    face.style.setProperty('--ai-bot-idle-duration', (3.4 + Math.random() * 2.2).toFixed(2) + 's');
    face.style.setProperty('--ai-bot-idle-delay', (-Math.random() * 5.6).toFixed(2) + 's');
    face.style.setProperty('--ai-bot-blink-duration', (4.1 + Math.random() * 3.3).toFixed(2) + 's');
    face.style.setProperty('--ai-bot-blink-delay', (-Math.random() * 7.4).toFixed(2) + 's');
    const svg = svgNode('svg', {viewBox: '0 0 88 88', focusable: 'false'});
    svg.append(
      svgNode('path', {class: 'ai-robot-antenna', d: 'M44 18V9'}),
      svgNode('circle', {class: 'ai-robot-antenna-tip', cx: 44, cy: 7, r: 4}),
      svgNode('rect', {class: 'ai-robot-ear', x: 5, y: 39, width: 8, height: 16, rx: 4}),
      svgNode('rect', {class: 'ai-robot-ear', x: 75, y: 39, width: 8, height: 16, rx: 4}),
      svgNode('rect', {class: 'ai-robot-shell', x: 10, y: 18, width: 68, height: 60, rx: 21}),
      svgNode('rect', {class: 'ai-robot-screen', x: 16, y: 25, width: 56, height: 46, rx: 15}),
      svgNode('path', {class: 'ai-robot-brows', d: {positive: 'M26 35q6-4 12 0 M50 35q6-4 12 0', negative: 'M26 35l12 4 M50 39l12-4', caution: 'M26 39l12-6 M50 33l12 6', neutral: 'M27 36h10 M51 36h10'}[mood]}),
      svgNode('path', {class: 'ai-robot-eyes', d: {positive: 'M26 47q6-8 12 0 M50 47q6-8 12 0', negative: 'M29 47q3-2 6 0 M53 47q3-2 6 0', caution: 'M27 47q4-5 8 0 M55 43v6', neutral: 'M32 44v5 M56 44v5'}[mood]}),
      svgNode('path', {class: 'ai-robot-cheeks', d: 'M22 54h5 M61 54h5'}),
      svgNode('path', {class: 'ai-robot-mouth', d: {positive: 'M29 55q15 18 30 0', negative: 'M31 63q13-12 26 0', caution: 'M40 57q4-3 8 0v5q-4 3-8 0Z', neutral: 'M34 59q10 4 20 0'}[mood]})
    );
    face.append(svg); return face;
  }
  function render(response, core = {}, options = {}) {
    const data = response.data || {};
    if (!data.summary?.heading || !data.summary?.text) throw new Error('The AI overview could not be read.');
    const sources = new Map((data.sources || []).map(s => [s.id, s]));
    const href = options.sourceHref || (s => '#' + s.section);
    const selected = select(data), root = node('div', 'ai-story');
    if (options.signalLimit) {
      const timeline = node('div', 'ai-story-timeline');
      timeline.setAttribute('role', 'group'); timeline.setAttribute('aria-label', 'Available company signals');
      const signals = [selected.recent && {...selected.recent, label: 'Recent context'},
        selected.watch && {...selected.watch, label: 'What to watch'}, ...selected.remaining].filter(Boolean);
      signals.slice(0, options.signalLimit).forEach(({item, category, label}) => {
        const kind = ['watch_next', 'catalysts', 'risks'].includes(category) ? 'watch' : 'recent';
        const card = stage(label, kind, item);
        card.append(node('h4', '', item.heading), facts(item));
        const why = explanation(item, sources, href, core);
        card.append(disclosure('Why this matters', why));
        timeline.append(card);
      });
      if (timeline.children.length) root.append(timeline);
      return root;
    }
    if (!options.compact) {
      const lead = node('header', 'ai-story-lead');
      const robot = node('span', 'ai-story-robot');
      robot.append((options.robot || aiRobotFace)(tone(data.summary), true)); lead.append(robot);
      const copy = node('div', 'ai-story-lead-copy'), label = node('div', 'ai-story-lead-label');
      label.append(node('span', 'ai-story-eyebrow', 'The AI take'), badge(data.summary));
      copy.append(label, node('h2', '', data.summary.heading), disclosure('Read the AI take', explanation(data.summary, sources, href)));
      lead.append(copy); root.append(lead);
    }
    const timeline = node('div', 'ai-story-timeline'); timeline.setAttribute('role', 'group'); timeline.setAttribute('aria-label', 'Now, recent context, and what to watch');
    if (!options.hideEmpty || hasNowData(core)) timeline.append(renderNow(core, sources, href));
    const recent = stage('Recent context', 'recent', selected.recent?.item);
    if (selected.recent) {
      const {item, category} = selected.recent;
      recent.append(node('span', 'ai-story-caption', categories.find(c => c[0] === category)[1]), node('h4', '', item.heading), facts(item));
      const trend = financialTrend(item, core, sources);
      if (trend && !options.compactCharts) recent.append(trend.figure);
      else if (!trend) recent.append(node('div', 'ai-story-signal-mark', tones[tone(item)]));
      const why = explanation(item, sources, href);
      if (trend && options.compactCharts) why.append(trend.figure);
      if (trend) why.append(disclosure('View chart data', trend.table));
      recent.append(disclosure('Why this matters', why));
    } else recent.append(node('h4', '', 'Recent context is limited'), node('p', 'ai-story-unavailable', 'No supported change or company signal is available in this brief.'));
    if (!options.hideEmpty || selected.recent) timeline.append(recent);
    const watch = stage('What to watch', 'watch', selected.watch?.item);
    if (selected.watch) {
      const {item, category} = selected.watch;
      const mark = node('div', 'ai-story-checkpoint'); mark.append(icon(category === 'catalysts' ? 'event' : 'watch'));
      watch.append(mark, node('span', 'ai-story-caption', category === 'catalysts' ? 'Reported development' : 'Next question'), node('h4', '', item.heading), facts(item), disclosure('Why this matters', explanation(item, sources, href, core)));
    } else {
      const mark = node('div', 'ai-story-checkpoint'); mark.append(icon('watch'));
      watch.append(mark, node('h4', '', 'No supported checkpoint yet'), node('p', 'ai-story-unavailable', 'The available evidence does not identify a next watch question or catalyst.'));
    }
    if (!options.hideEmpty || selected.watch) timeline.append(watch);
    if (options.hideEmpty) timeline.setAttribute('aria-label', 'Available company signals');
    if (timeline.children.length) root.append(timeline);
    if (!options.compact && selected.remaining.length) {
      const rows = node('div', 'ai-story-more-rows');
      selected.remaining.forEach(({item, label, category}) => {
        const card = node('article', 'ai-story-more-card');
        card.dataset.tone = tone(item);
        const head = node('div', 'ai-story-more-head'), mark = node('span', 'ai-story-marker');
        mark.append(icon(category === 'catalysts' ? 'event' : category === 'watch_next' || category === 'risks' ? 'watch' : category === 'changes' ? 'recent' : 'now'));
        head.append(mark, node('span', 'ai-story-caption', label));
        card.append(head, node('h4', '', item.heading), badge(item), facts(item),
          disclosure('Why this matters', explanation(item, sources, href, core)));
        rows.append(card);
      });
      root.append(disclosure('Explore more signals (' + selected.remaining.length + ')', rows));
    }
    if (!options.compact) {
      const footer = node('footer', 'ai-story-footer');
      if (data.generated_at) footer.append(node('span', '', 'Generated ' + (options.stamp ? options.stamp(data.generated_at) : data.generated_at)));
      footer.append(node('span', '', 'AI-generated synthesis · Not investment advice'));
      root.append(footer);
    }
    return root;
  }
  // Company facts remain available while AI is loading or unavailable.
  function renderFacts(core, options = {}) {
    const root = node('div', 'ai-story ai-story-fallback');
    if (!options.hideEmpty || hasNowData(core)) root.append(renderNow(core));
    return root;
  }
  window.tickrAIStory = {render, renderFacts, contentVersion: 'meaning-v1'};
})();
