(function () {
  'use strict';
  var selectedTickers = [], selectedCards = new Set(), catalog, activeCategory = 'overview';
  var suggestions = [], activeSuggestion = -1, searchTimer, searchGeneration = 0;
  var $ = function (id) { return document.getElementById(id); };

  function notice(id, message) { var el = $(id); if (!el) return; el.textContent = message || ''; el.hidden = !message; }
  function csrf() { return window.tickrAuth ? window.tickrAuth.csrf() : ''; }
  function json(response) { return response.text().then(function (text) { try { return JSON.parse(text); } catch (e) { return {ok:false,error:'Unexpected server response.'}; } }); }
  function displaySymbol(symbol) { return String(symbol || '').split(':').pop(); }
  function market(symbol) { return String(symbol).indexOf('IN:') === 0 ? 'NSE' : 'US'; }
  function hasIndia() { return selectedTickers.some(function (ticker) { return ticker.indexOf('IN:') === 0; }); }

  function renderTickers() {
    $('ticker-chips').innerHTML = selectedTickers.map(function (symbol) {
      return '<span class="ticker-chip">' + displaySymbol(symbol) + ' · ' + market(symbol) + '<button type="button" data-remove="' + symbol + '" aria-label="Remove ' + displaySymbol(symbol) + '">×</button></span>';
    }).join('');
    $('ticker-chips').querySelectorAll('[data-remove]').forEach(function (button) {
      button.onclick = function () { selectedTickers = selectedTickers.filter(function (ticker) { return ticker !== button.dataset.remove; }); renderTickers(); };
    });
    $('step-one-next').textContent = hasIndia() ? 'Continue' : 'Save & open dashboard';
  }

  function addTicker(symbol) {
    symbol = String(symbol || '').trim().toUpperCase();
    if (!symbol || selectedTickers.indexOf(symbol) >= 0) { $('ticker-status').textContent = symbol ? displaySymbol(symbol) + ' is already in your watchlist.' : 'Choose a stock first.'; return; }
    selectedTickers.push(symbol); $('ticker-input').value = ''; hideSuggestions(); renderTickers();
    $('ticker-status').textContent = displaySymbol(symbol) + ' added. Add another or continue.';
  }

  function hideSuggestions() { suggestions = []; activeSuggestion = -1; $('ticker-suggestions').hidden = true; $('ticker-suggestions').innerHTML = ''; $('ticker-input').setAttribute('aria-expanded', 'false'); }
  function renderSuggestions(items) {
    suggestions = items; activeSuggestion = -1;
    $('ticker-suggestions').innerHTML = items.map(function (item, index) { return '<li role="option" data-index="' + index + '"><strong>' + displaySymbol(item.symbol) + '</strong> · ' + (item.market === 'IN' ? 'NSE' : 'US') + '<br><small>' + item.name + '</small></li>'; }).join('');
    $('ticker-suggestions').hidden = !items.length; $('ticker-input').setAttribute('aria-expanded', String(!!items.length));
  }
  function search() {
    var query = $('ticker-input').value.trim(); clearTimeout(searchTimer);
    if (!query) { hideSuggestions(); $('ticker-status').textContent = 'Search, choose a match, or press Enter to validate.'; return; }
    $('ticker-status').textContent = 'Searching…'; var generation = ++searchGeneration;
    searchTimer = setTimeout(function () {
      fetch('/api/tickers/search?q=' + encodeURIComponent(query)).then(json).then(function (data) {
        if (generation !== searchGeneration) return;
        if (!data.ok || !(data.results || []).length) { hideSuggestions(); $('ticker-status').textContent = data.error || 'No US or NSE listings found.'; return; }
        renderSuggestions(data.results); $('ticker-status').textContent = 'Choose a matching listing.';
      }).catch(function () { $('ticker-status').textContent = 'Search is unavailable. Try again.'; });
    }, 280);
  }
  function validateAndAdd() {
    var query = $('ticker-input').value.trim(); if (!query) return;
    if (activeSuggestion >= 0 && suggestions[activeSuggestion]) { addTicker(suggestions[activeSuggestion].symbol); return; }
    var exact = suggestions.find(function (item) { return item.symbol === query.toUpperCase() || displaySymbol(item.symbol) === query.toUpperCase(); });
    if (exact) { addTicker(exact.symbol); return; }
    $('ticker-add').disabled = true; $('ticker-status').textContent = 'Validating…';
    fetch('/api/tickers/validate?symbol=' + encodeURIComponent(query)).then(json).then(function (data) {
      if (!data.ok || !data.valid) { $('ticker-status').textContent = data.error || 'Could not validate that stock.'; return; }
      addTicker(data.symbol);
    }).catch(function () { $('ticker-status').textContent = 'Could not validate right now.'; }).finally(function () { $('ticker-add').disabled = false; });
  }

  var iconPaths = {
    overview:'<path d="M4 19V9m5 10V5m5 14v-7m5 7V3"/><path d="M3 19h18"/>',
    ai:'<path d="m12 3 1.25 3.75L17 8l-3.75 1.25L12 13l-1.25-3.75L7 8l3.75-1.25L12 3Z"/><path d="m5.5 13 .8 2.2 2.2.8-2.2.8L5.5 19l-.8-2.2-2.2-.8 2.2-.8.8-2.2Zm13-1 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z"/>',
    financials:'<path d="M4 20V10h4v10m4 0V4h4v16m4 0V7h-4"/><path d="M2 20h20"/>',
    ownership:'<path d="M16 20v-1.5a4.5 4.5 0 0 0-4.5-4.5h-3A4.5 4.5 0 0 0 4 18.5V20"/><circle cx="10" cy="7" r="4"/><path d="M17 10a3 3 0 1 0 0-6m1 10a4 4 0 0 1 4 4v2"/>',
    analysis:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
    actions:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18m-14 4h4m-4 3h7"/>',
    news:'<path d="M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h5v5H7zm8 0h2m-2 4h2M7 17h10"/>',
    company:'<path d="M4 21V7l8-4 8 4v14M8 10h2m4 0h2m-8 4h2m4 0h2m-6 7v-3h4v3"/>',
    history:'<path d="M3 17 8 12l4 3 8-9"/><path d="M16 6h4v4"/><path d="M3 21h18"/>',
    risk:'<path d="M12 3 3.5 7v5c0 5.2 3.6 8 8.5 9 4.9-1 8.5-3.8 8.5-9V7L12 3Z"/><path d="M12 8v5m0 3h.01"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 10h18"/>',
    document:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 13h6m-6 4h6"/>'
  };
  function icon(name, className) { return '<span class="' + (className || 'catalog-icon') + '" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (iconPaths[name] || iconPaths.overview) + '</svg></span>'; }
  function cardIcon(id, categoryId) {
    if (id.indexOf('company_') >= 0 || id.indexOf('leadership') >= 0 || id.indexOf('peer_') >= 0) return 'company';
    if (id.indexOf('history') >= 0 || id.indexOf('technical') >= 0 || id.indexOf('return') >= 0) return 'history';
    if (id.indexOf('risk') >= 0 || id.indexOf('attention') >= 0) return 'risk';
    if (categoryId === 'actions') return 'calendar';
    if (id.indexOf('statement') >= 0 || id.indexOf('results') >= 0 || id.indexOf('additional') >= 0) return 'document';
    return categoryId;
  }
  function previewKind(card, categoryId) {
    var id = card.id;
    if (categoryId === 'ai') return 'ai';
    if (categoryId === 'ownership') return 'donut';
    if (categoryId === 'actions') return 'timeline';
    if (categoryId === 'news') return 'news';
    if (id.indexOf('history') >= 0 || id.indexOf('results') >= 0 || id.indexOf('statement') >= 0 || id.indexOf('technical') >= 0 || id.indexOf('growth') >= 0 || id.indexOf('profitability') >= 0 || id.indexOf('cash_') >= 0) return 'chart';
    if (id.indexOf('company_') >= 0 || id.indexOf('leadership') >= 0 || id.indexOf('peer_') >= 0 || id.indexOf('detail') >= 0) return 'profile';
    return 'metric';
  }
  function metricSample(id) {
    if (id.indexOf('market_cap') >= 0) return ['₹18.4L Cr','Large cap'];
    if (id.indexOf('pe_ratio') >= 0) return ['24.6×','vs sector 27.1×'];
    if (id.indexOf('dividend') >= 0) return ['1.42%','₹10.00 / share'];
    if (id.indexOf('ytd') >= 0) return ['+12.8%','Year to date'];
    if (id.indexOf('landmark') >= 0) return ['₹2,846','72% of 52W range'];
    if (id.indexOf('day_') >= 0) return ['+1.7%','₹2,791 – ₹2,862'];
    return ['Healthy','Updated today'];
  }
  function cardVisual(card, categoryId, compact) {
    var kind = previewKind(card, categoryId), sample = metricSample(card.id), cls = compact ? ' card-visual--compact' : '';
    if (kind === 'chart') return '<div class="card-visual card-visual--chart' + cls + '"><div class="mini-chart-meta"><strong>₹2,846</strong><span>+12.8%</span></div><svg viewBox="0 0 180 48" preserveAspectRatio="none" aria-hidden="true"><path class="mini-chart-area" d="M0 43 C18 39 24 26 40 31 S68 40 82 24 106 30 122 15 148 22 180 5 V48 H0Z"/><path class="mini-chart-line" d="M0 43 C18 39 24 26 40 31 S68 40 82 24 106 30 122 15 148 22 180 5"/></svg><div class="mini-axis"><span>Apr</span><span>Sep</span></div></div>';
    if (kind === 'ai') return '<div class="card-visual card-visual--ai' + cls + '"><div class="ai-preview-head">' + icon('ai','mini-inline-icon') + '<span>AI insight</span><em>Fresh</em></div><div class="preview-copy-line is-long"></div><div class="preview-copy-line"></div><div class="ai-signal"><i></i><span>Evidence-linked signal</span></div></div>';
    if (kind === 'donut') return '<div class="card-visual card-visual--donut' + cls + '"><div class="mini-donut"><span>68%</span></div><div class="donut-legend"><span><i></i>Promoter <b>50.3%</b></span><span><i></i>Institutions <b>17.7%</b></span><span><i></i>Public <b>32.0%</b></span></div></div>';
    if (kind === 'timeline') return '<div class="card-visual card-visual--timeline' + cls + '"><div class="timeline-date"><strong>18</strong><span>SEP</span></div><div class="timeline-copy"><strong>Upcoming event</strong><span>Record date · Confirmed</span><div><i></i><i></i><i></i></div></div></div>';
    if (kind === 'news') return '<div class="card-visual card-visual--news' + cls + '"><div class="news-thumb">' + icon('news','mini-inline-icon') + '</div><div><span class="source-pill">REUTERS</span><div class="preview-copy-line is-long"></div><div class="preview-copy-line"></div><small>2h ago · 4 min read</small></div></div>';
    if (kind === 'profile') return '<div class="card-visual card-visual--profile' + cls + '"><div class="profile-mark">RC</div><div class="profile-lines"><strong>Reliance Industries</strong><span>Energy · Retail · Digital</span><div><i></i><i></i><i></i><i></i></div></div></div>';
    return '<div class="card-visual card-visual--metric' + cls + '"><div><strong>' + sample[0] + '</strong><span>' + sample[1] + '</span></div><svg viewBox="0 0 80 36" preserveAspectRatio="none" aria-hidden="true"><path d="M1 31 C14 27 15 18 27 22 S42 30 51 15 67 17 79 4"/></svg></div>';
  }

  // Keep the sample in the same card language as the stock page. Values here are illustrative.
  function dashboardSample(card, categoryId) {
    var id = card.id, kind = previewKind(card, categoryId), sample = metricSample(id);
    var titles = {ai_company_summary:'The 60-second view',ai_encouraging_signals:'What looks encouraging',overview_price_history:'The price story',overview_pe_history:'P/E valuation history',overview_price_landmarks:'Price context',overview_peer_comparison:'In good company',ownership_current_mix:'Who owns the company?'};
    var captions = {ai_company_summary:'A concise synthesis of the latest available company evidence.',overview_price_history:'Price, moving averages and trading volume.',overview_pe_history:'Historical price-to-earnings ratio with its median.',overview_price_landmarks:'Reported price landmarks · ₹',overview_peer_comparison:'Peers reported by IndianAPI · Prices in ₹ · Market cap in ₹ crore',ownership_current_mix:'Shareholding categories as reported by IndianAPI.'};
    var body;
    if (id === 'overview_price_landmarks') body = '<div class="dashboard-range"><i style="left:72%"></i></div><div class="dashboard-range-labels"><span>₹2,420<small>52-week low</small></span><span>₹3,012<small>52-week high</small></span></div>';
    else if (kind === 'chart') body = '<div class="stock-controls"><span class="sample-control is-active">1Y</span><span class="sample-control">3Y</span><span class="sample-control">5Y</span></div><p class="stock-chart-readout">Sep 2026 · ₹2,846</p><svg class="sample-stock-chart" viewBox="0 0 260 90" preserveAspectRatio="none" aria-hidden="true"><path class="sample-grid-line" d="M0 20H260M0 50H260M0 80H260"/><path class="sample-price-line" d="M0 74 C25 65 32 48 55 57 S88 72 110 44 142 58 163 34 194 43 214 22 242 30 260 12"/></svg><div class="stock-chart-legend"><span>Price</span><span class="stock-indicator positive">+12.8%</span></div>';
    else if (kind === 'ai') body = '<div class="dashboard-ai-insight signal-positive"><span class="dashboard-ai-tone">Sample insight</span><p class="dashboard-ai-text">Revenue and cash generation have remained steady in recent reports.</p></div>';
    else if (kind === 'donut') body = '<p class="dashboard-ownership-date">Illustrative ownership mix</p><div class="dashboard-stacked-bar"><span style="width:50%;background:#6f8aff"></span><span style="width:18%;background:#60b6b0"></span><span style="width:32%;background:#ce9c67"></span></div><dl class="dashboard-facts"><div class="dashboard-fact"><dt>Promoters</dt><dd>50.3%</dd></div><div class="dashboard-fact"><dt>Institutions</dt><dd>17.7%</dd></div></dl>';
    else if (kind === 'timeline') body = '<div class="dashboard-table-wrap"><table class="dashboard-mini-table"><thead><tr><th>Event</th><th>Record date</th></tr></thead><tbody><tr><td>Dividend</td><td>18 Sep 2026</td></tr></tbody></table></div>';
    else if (kind === 'news') body = '<div class="dashboard-news-grid"><div class="dashboard-news-card"><div class="dashboard-news-body"><span class="dashboard-news-meta">Sample company news · Today</span><h4><span>Company announces its latest quarterly update</span></h4></div></div></div>';
    else if (kind === 'profile') body = '<dl class="dashboard-facts"><div class="dashboard-fact"><dt>Company</dt><dd>Example Industries</dd></div><div class="dashboard-fact"><dt>Sector</dt><dd>Energy &amp; Retail</dd></div></dl>';
    else body = '<strong class="dashboard-card-value">' + sample[0] + '</strong><small class="dashboard-card-note">' + sample[1] + '</small>';
    var tone = id === 'ai_company_summary' ? ' dashboard-ai-summary' : id === 'ai_key_risks' ? ' dashboard-ai-negative' : id === 'ai_attention_signals' || id === 'ai_recent_changes' ? ' dashboard-ai-caution' : id === 'ai_encouraging_signals' || id === 'ai_potential_catalysts' ? ' dashboard-ai-positive' : '';
    return '<div class="dashboard-card sample-dashboard-card' + tone + '" data-card="' + id + '"><h3>' + (titles[id] || card.title) + '</h3><p class="dashboard-card-caption">' + (captions[id] || card.description) + '</p>' + body + '</div>';
  }

  function categoryById(id) { return catalog.categories.find(function (category) { return category.id === id; }); }
  function categorySelected(category) { return category.cards.filter(function (card) { return selectedCards.has(card.id); }); }
  function activateCategory(id) {
    var category = categoryById(id); if (!category) return;
    activeCategory = id; renderCustomizer();
    if (window.matchMedia('(max-width:720px)').matches) {
      var rail = document.querySelector('.onboarding-step[data-step="2"] .category-rail');
      var categoryList = $('category-rail');
      var activeButton = categoryList.querySelector('.category-button.is-active');
      var picker = document.querySelector('.onboarding-step[data-step="2"] .card-picker');
      var stickyTop = parseFloat(window.getComputedStyle(rail).top) || 0;
      var top = window.scrollY + picker.getBoundingClientRect().top - rail.getBoundingClientRect().height - stickyTop - 12;
      var behavior = window.matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth';
      categoryList.scrollTo({left:categoryList.scrollLeft + activeButton.getBoundingClientRect().left - categoryList.getBoundingClientRect().left,behavior:behavior});
      window.scrollTo({top:Math.max(0,top),behavior:behavior});
    }
  }
  function renderCustomizer() {
    var railScrollLeft = $('category-rail').scrollLeft;
    $('category-rail').innerHTML = catalog.categories.map(function (category) {
      var count = categorySelected(category).length;
      return '<button type="button" class="category-button tone-' + category.id + ' ' + (category.id === activeCategory ? 'is-active ' : '') + (count ? 'has-selection' : '') + '" data-category="' + category.id + '" aria-current="' + (category.id === activeCategory ? 'true' : 'false') + '">' + icon(category.id,'category-icon') + '<span class="category-button-copy"><strong>' + category.title + '</strong><small>' + category.description + '</small></span><span class="category-count">' + count + '<small>/' + category.cards.length + '</small></span></button>';
    }).join('');
    $('category-rail').scrollLeft = railScrollLeft;
    $('category-rail').querySelectorAll('[data-category]').forEach(function (button) { button.onclick = function () { activateCategory(button.dataset.category); }; });
    var category = categoryById(activeCategory) || catalog.categories[0];
    $('active-category-kicker').textContent = 'Choose cards'; $('active-category-title').textContent = category.title; $('active-category-description').textContent = category.description;
    $('category-selection-count').textContent = categorySelected(category).length + ' of ' + category.cards.length + ' selected in this section';
    $('card-grid').className = 'selection-grid tone-' + category.id;
    $('card-grid').innerHTML = category.cards.map(function (card) {
      var checked = selectedCards.has(card.id);
      return '<label class="selection-card ' + (checked ? 'is-selected' : '') + '"><input type="checkbox" value="' + card.id + '" ' + (checked ? 'checked' : '') + '><span class="selection-check" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="m3.5 8 3 3 6-6"/></svg></span>' + dashboardSample(card,category.id) + '</label>';
    }).join('');
    $('card-grid').querySelectorAll('input').forEach(function (input) { input.onchange = function () { if (input.checked) selectedCards.add(input.value); else selectedCards.delete(input.value); renderCustomizer(); }; });
    renderSelectionSummary();
  }
  function renderSelectionSummary() {
    var categoryCount = catalog.categories.filter(function (category) { return categorySelected(category).length; }).length;
    $('selection-count').textContent = categoryCount + ' categories · ' + selectedCards.size + ' cards selected';
  }
  function showStep(step) {
    document.querySelectorAll('[data-step]').forEach(function (node) { node.hidden = Number(node.dataset.step) !== step; });
    document.querySelectorAll('[data-step-indicator]').forEach(function (node) { var value = Number(node.dataset.stepIndicator); node.classList.toggle('is-active', value === step); node.classList.toggle('is-complete', value < step); });
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function save() {
    notice('step-one-error', ''); notice('step-two-error', '');
    if (!selectedTickers.length) { notice('step-one-error', 'Add at least one validated stock.'); showStep(1); return; }
    if (hasIndia() && !selectedCards.size) { notice('step-two-error', 'Select at least one card for your Indian dashboard.'); return; }
    var buttons = [$('save-dashboard'), $('step-one-next')];
    var labels = buttons.map(function (button) { return button.textContent; });
    function setSaving(saving) {
      buttons.forEach(function (button, index) {
        button.disabled = saving;
        button.classList.toggle('is-saving', saving);
        button.setAttribute('aria-busy', String(saving));
        button.textContent = saving ? 'Saving…' : labels[index];
      });
    }
    setSaving(true);
    fetch('/api/subscribe', {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf()},body:JSON.stringify({
      email:$('onboarding-email').value,tickers:selectedTickers,email_briefings:$('email-briefings').checked,
      in_dashboard_cards:hasIndia()?Array.from(selectedCards):undefined
    })}).then(json).then(function (data) {
      if (!data.ok) throw new Error(data.error || 'Could not save your dashboard.');
      if (data.warning) try { sessionStorage.setItem('tickr-welcome-warning', data.warning); } catch (e) {}
      location.assign('/digest');
    }).catch(function (error) { notice(hasIndia() ? 'step-two-error' : 'step-one-error', error.message); setSaving(false); });
  }

  function bind() {
    $('ticker-input').addEventListener('input', search); $('ticker-add').onclick = validateAndAdd;
    $('ticker-input').addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown' && suggestions.length) { event.preventDefault(); activeSuggestion = Math.min(activeSuggestion + 1, suggestions.length - 1); }
      else if (event.key === 'ArrowUp' && suggestions.length) { event.preventDefault(); activeSuggestion = Math.max(activeSuggestion - 1, 0); }
      else if (event.key === 'Enter') { event.preventDefault(); validateAndAdd(); return; }
      else if (event.key === 'Escape') { hideSuggestions(); return; }
      $('ticker-suggestions').querySelectorAll('li').forEach(function (li, index) { li.classList.toggle('is-active', index === activeSuggestion); li.setAttribute('aria-selected', String(index === activeSuggestion)); });
    });
    $('ticker-suggestions').onclick = function (event) { var item = event.target.closest('[data-index]'); if (item) addTicker(suggestions[Number(item.dataset.index)].symbol); };
    $('step-one-next').onclick = function () { if (!selectedTickers.length) { notice('step-one-error','Add at least one validated stock.'); return; } notice('step-one-error',''); if (hasIndia()) { showStep(2); renderCustomizer(); } else save(); };
    $('step-two-back').onclick = function () { showStep(1); };
    $('save-dashboard').onclick = save;
    $('select-recommended').onclick = function () { var category = categoryById(activeCategory); category.cards.forEach(function (card) { selectedCards.delete(card.id); }); category.recommended.forEach(function (id) { selectedCards.add(id); }); renderCustomizer(); };
    $('select-all').onclick = function () { categoryById(activeCategory).cards.forEach(function (card) { selectedCards.add(card.id); }); renderCustomizer(); };
    $('clear-category').onclick = function () { categoryById(activeCategory).cards.forEach(function (card) { selectedCards.delete(card.id); }); renderCustomizer(); };
    $('theme-toggle').onclick = function () { var theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = theme; document.documentElement.style.colorScheme = theme; try { localStorage.setItem('daily-digest-theme', theme); } catch(e) {} };
  }

  bind();
  Promise.all([fetch('/dashboard-catalog.json').then(json), window.tickrAuth.ready]).then(function (values) {
    catalog = values[0]; var state = values[1];
    if (!state.authenticated) { location.assign('/?signin=1'); return; }
    $('onboarding-email').value = state.email || ''; $('email-briefings').checked = !!state.email_briefings;
    selectedTickers = Array.isArray(state.tickers) ? state.tickers.slice() : [];
    var saved = Array.isArray(state.in_dashboard_cards) ? state.in_dashboard_cards : [];
    if (saved.length) saved.forEach(function (id) { selectedCards.add(id); });
    else catalog.categories.filter(function (category) { return category.default; }).forEach(function (category) { category.cards.forEach(function (card) { selectedCards.add(card.id); }); });
    renderTickers(); renderCustomizer();
  }).catch(function (error) { notice('auth-notice', error.message || 'Could not load setup.'); });
})();
