// Category layout preserved from the committed stock overview.
(function () {
  'use strict';
  function node(tag, className, value) { const el = document.createElement(tag); if (className) el.className = className; if (value !== undefined) el.textContent = value; return el; }
  function aiEvidence(ids, sources, sourceHref) {
    const links = node('span', 'stock-ai-evidence');
    (ids || []).forEach(id => {
      const source = sources.get(id); if (!source) return;
      const link = node('a', '', id); link.href = sourceHref(source);
      link.title = 'View source: ' + source.label;
      link.setAttribute('aria-label', id + ': ' + source.label);
      links.append(link);
    });
    return links;
  }
  const aiCategories = [['encouraging', 'What looks encouraging'], ['attention', 'What needs attention'],
    ['changes', 'What changed recently'], ['catalysts', 'Potential catalysts'], ['risks', 'Key risks'], ['watch_next', 'What to watch next']];
  const aiTones = {positive: 'Encouraging', negative: 'Concern', caution: 'Watch', neutral: 'Context'};
  function aiSignal(item, sources, options) {
    const tone = Object.hasOwn(aiTones, item.tone) ? item.tone : 'neutral';
    const signal = node('article', 'ai-signal ' + tone), head = node('span', 'ai-signal-head');
    head.append(node('span', 'ai-signal-title', item.heading || 'Company signal'), node('span', 'ai-tone', aiTones[tone]));
    const title = node('div', 'ai-signal-heading'); title.append(options.robot(tone), head);
    const facts = node('div', 'ai-signal-facts');
    (Array.isArray(item.facts) ? item.facts : []).forEach(fact => {
      if (!fact || !fact.label || !fact.value) return;
      const chip = node('span', 'ai-signal-fact');
      chip.append(node('span', 'ai-signal-fact-label', fact.label), node('strong', '', fact.value)); facts.append(chip);
    });
    const body = node('p', '', item.text || ''); body.append(aiEvidence(item.evidence_ids, sources, options.sourceHref));
    signal.append(title); if (facts.children.length) signal.append(facts); signal.append(body); return signal;
  }
  function render(response, _core, options) {
    const {robot: aiRobotFace, stamp} = options;
    const data = response.data || {};
    if (!data.summary || !data.summary.text) throw new Error('The AI overview could not be read.');
    const sources = new Map((data.sources || []).map(source => [source.id, source]));
    const explorer = node('div', 'ai-insight-explorer');
    const summary = node('article', 'ai-summary'), guide = node('aside', 'ai-robot-guide');
    guide.setAttribute('aria-label', 'Overall AI signal');
    const guideFace = node('div', 'ai-robot-guide-face'), summaryTone = Object.hasOwn(aiTones, data.summary.tone) ? data.summary.tone : 'neutral';
    guideFace.append(aiRobotFace(summaryTone, true));
    guide.dataset.tone = summaryTone;
    guide.append(guideFace, node('span', 'ai-robot-tone', ({positive: 'Encouraging evidence', negative: 'Needs attention', caution: 'Mixed or uncertain', neutral: 'Monitoring point'})[summaryTone]));
    const summaryBody = node('p', '', data.summary.text); summaryBody.append(aiEvidence(data.summary.evidence_ids, sources, options.sourceHref));
    const summaryCopy = node('div', 'ai-summary-copy');
    summaryCopy.append(node('span', 'ai-summary-label', '✦ The AI take'), node('h2', '', data.summary.heading || 'Company perspective'), summaryBody);
    summary.dataset.tone = summaryTone; summary.append(guide, summaryCopy);

    const insightBody = node('div', 'ai-insight-body'), meta = node('div', 'ai-insight-meta');
    meta.append(node('span', '', 'Generated ' + stamp(data.generated_at)));
    const count = node('p', 'ai-signal-count'), categories = node('div', 'ai-categories');
    categories.setAttribute('role', 'group'); categories.setAttribute('aria-label', 'AI signals');
    let total = 0, visibleAreas = 0;
    aiCategories.forEach(([key, title]) => {
      const items = Array.isArray(data[key]) ? data[key] : [];
      if (!items.length) return;
      total += items.length; visibleAreas++;
      const group = node('section', 'ai-category'), heading = node('h3', '', title);
      group.dataset.category = key;
      heading.append(node('span', 'ai-category-count', String(items.length))); group.append(heading);
      const list = node('ul'); items.forEach(item => { const row = node('li'); row.append(aiSignal(item, sources, options)); list.append(row); });
      group.append(list); categories.append(group);
    });
    count.textContent = visibleAreas ? total + ' supported ' + (total === 1 ? 'signal' : 'signals') + ' across ' + visibleAreas + ' ' + (visibleAreas === 1 ? 'area' : 'areas') : 'No supported signals in the available evidence.';
    categories.hidden = visibleAreas === 0; meta.append(count); insightBody.append(meta, categories); explorer.append(summary, insightBody); return explorer;
  }
  window.tickrAILegacy = {render};
})();
