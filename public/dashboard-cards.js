(function () {
  'use strict';
  var catalogPromise = fetch('/dashboard-catalog.json').then(function (r) { return r.json(); });
  var requests = new Map();
  var format = window.tickrStockFormat || {};
  function has(value) { return value !== null && value !== undefined && value !== '' && (typeof value !== 'object' || Object.keys(value).length); }
  function num(value) { var n = Number(String(value == null ? '' : value).replace(/,/g,'')); return Number.isFinite(n) ? n : null; }
  function fmt(value) { return format.fmt ? format.fmt(value) : (num(value) === null ? (value || '—') : num(value).toLocaleString('en-IN',{maximumFractionDigits:2})); }
  function money(value) { return num(value) === null ? '—' : '₹' + num(value).toLocaleString('en-IN',{maximumFractionDigits:2}); }
  function pct(value) { return num(value) === null ? '—' : (num(value) > 0 ? '+' : '') + num(value).toFixed(2) + '%'; }
  function text(value) { return String(value == null || value === '' ? '—' : value); }
  function label(key) { return String(key).replace(/([a-z\d])([A-Z])/g,'$1 $2').replace(/_/g,' ').replace(/^./,function(c){return c.toUpperCase();}); }
  function el(tag, cls, content) { var node=document.createElement(tag); if(cls)node.className=cls; if(content!==undefined)node.textContent=content; return node; }
  function api(symbol, section, params) {
    var query = new URLSearchParams(Object.assign({symbol:symbol,section:section},params||{})); var key=query.toString();
    if (!requests.has(key)) requests.set(key,fetch('/api/stock-data?'+key).then(function(r){return r.json();}).then(function(data){if(!data.ok)throw new Error(data.error||'Unavailable');return data.data;}));
    return requests.get(key);
  }
  function ai(symbol) {
    var key='ai:'+symbol;if(!requests.has(key))requests.set(key,fetch('/api/stock-ai?'+new URLSearchParams({symbol:symbol,schema:'2'})).then(function(r){return r.json();}).then(function(data){if(!data.ok)throw new Error(data.error||'AI unavailable');return data.data;}));return requests.get(key);
  }
  function card(meta, wide) { var node=el('article','dashboard-card'+(wide?' is-wide':''));node.dataset.card=meta.id;node.append(el('h3','',meta.title),el('p','dashboard-card-caption',meta.description));return node; }
  function state(node,message){node.append(el('p','dashboard-card-state',message||'Not available for this company.'));}
  function list(object, limit) {
    var dl=el('dl','dashboard-data-list'), entries=[];
    Object.entries(object||{}).forEach(function(pair){var value=pair[1];if(value===null||typeof value!=='object')entries.push(pair);});
    entries.slice(0,limit||10).forEach(function(pair){dl.append(el('dt','',label(pair[0])),el('dd','',fmt(pair[1])));}); return dl;
  }
  function simpleTable(rows) {
    rows=(rows||[]).filter(function(row){return row&&typeof row==='object';}).slice(0,8);if(!rows.length)return null;
    var keys=Object.keys(rows[0]).filter(function(key){return rows.every(function(row){return row[key]===null||typeof row[key]!=='object';});}).slice(0,5);
    var table=el('table','dashboard-mini-table'),thead=el('thead'),tr=el('tr'),tbody=el('tbody');keys.forEach(function(k){tr.append(el('th','',label(k)));});thead.append(tr);rows.forEach(function(row){var r=el('tr');keys.forEach(function(k){r.append(el('td','',fmt(row[k])));});tbody.append(r);});table.append(thead,tbody);return table;
  }
  function generic(node,value) {
    if(!has(value)){state(node);return;}if(Array.isArray(value)){var table=simpleTable(value);if(table)node.append(table);else state(node,text(value.slice(0,8).join(' · ')));return;}
    if(typeof value==='object'){node.append(list(value));var nested=Object.entries(value).filter(function(pair){return pair[1]&&typeof pair[1]==='object';}).slice(0,3);nested.forEach(function(pair){var details=el('details'),summary=el('summary','',label(pair[0]));details.append(summary);var table=Array.isArray(pair[1])?simpleTable(pair[1]):list(pair[1],8);if(table)details.append(table);node.append(details);});return;}node.append(el('strong','dashboard-card-value',fmt(value)));
  }
  function metric(node,value,note,formatter){if(num(value)===null){state(node);return;}node.append(el('strong','dashboard-card-value',(formatter||fmt)(value)));if(note)node.append(el('small','dashboard-card-note',note));}
  function healthGroup(node,core,title){var group=((core.health||{}).groups||[]).find(function(g){return g.title===title;});if(!group){state(node);return;}var values={};(group.metrics||[]).forEach(function(m){values[m.label]=fmt(m.value)+' '+(m.unit||'')+(m.change_label?' · '+m.change_label:'');});node.append(list(values,12));}
  function statement(node,core,key){var statement=(core.financials||[])[0],rows=statement&&statement.stockFinancialMap&&statement.stockFinancialMap[key];var table=simpleTable(rows);if(table)node.append(table);else state(node);}
  function action(node,core,key){var actions=core.actions||{}, value=actions[key];if(!value){var wanted=key.toLowerCase();Object.keys(actions).some(function(k){if(k.toLowerCase().indexOf(wanted)>=0){value=actions[k];return true;}return false;});}generic(node,value);}
  function renderCore(meta,node,core) {
    var s=core.snapshot||{}, p=core.profile||{}, id=meta.id;
    if(id==='overview_market_cap')return metric(node,s.marketCap,'₹ crore',function(v){return '₹'+fmt(v)+' cr';});
    if(id==='overview_pe_ratio')return metric(node,s.pPerEBasicExcludingExtraordinaryItemsTTM,'Trailing 12 months · ×');
    if(id==='overview_dividend_yield')return metric(node,s.currentDividendYieldCommonStockPrimaryIssueLTM,'Last 12 months',function(v){return fmt(v)+'%';});
    if(id==='overview_ytd_return')return metric(node,s.priceYTDPricePercentChange,'Price return',pct);
    if(id==='overview_price_landmarks')return node.append(list({'52-week low':money(core.year_low),'Current':money(core.prices.NSE!=null?core.prices.NSE:core.prices.BSE),'52-week high':money(core.year_high)},6));
    if(id==='overview_day_statistics')return node.append(list({'Day high':money(s.high),'Day low':money(s.low),'Previous close':money(s.close),'5-day return':pct(s.price5DayPercentChange),'Sector P/E':fmt(s.sectorPriceToEarningsValueRatio)},8));
    if(id==='overview_financial_pulse'){var metrics={};((core.health||{}).groups||[]).forEach(function(g){(g.metrics||[]).forEach(function(m){if(['revenue','net_profit','fcf','net_debt'].indexOf(m.id)>=0)metrics[m.label]=fmt(m.value)+' '+(m.unit||'');});});return generic(node,metrics);}
    if(id==='overview_company_description')return node.append(el('p','dashboard-ai-text',p.companyDescription||'Not available for this company.'));
    if(id==='overview_company_information'){var profile=Object.assign({},p);delete profile.companyDescription;delete profile.officers;return generic(node,profile);}
    if(id==='overview_leadership')return generic(node,p.officers&&p.officers.officer);
    if(id==='overview_peer_comparison')return generic(node,core.peers);
    if(id==='financial_health_growth')return healthGroup(node,core,'Growth');
    if(id==='financial_health_profitability')return healthGroup(node,core,'Profitability');
    if(id==='financial_health_balance_sheet')return healthGroup(node,core,'Balance sheet');
    if(id==='financial_health_cash_generation')return healthGroup(node,core,'Cash generation');
    if(id==='financial_statement_income')return statement(node,core,'INC');
    if(id==='financial_statement_balance_sheet')return statement(node,core,'BAL');
    if(id==='financial_statement_cash_flow')return statement(node,core,'CAS');
    if(id==='financial_provider_metrics')return generic(node,core.metrics);
    if(id==='financial_additional_data')return generic(node,core.additional_financials);
    if(id==='ownership_current_mix'){var values={};(core.ownership||[]).forEach(function(group){var rows=group.categories||[];var latest=rows[rows.length-1]||{};values[group.displayName||group.categoryName]=latest.percentage;});return generic(node,values);}
    if(id==='ownership_detail')return generic(node,core.ownership);
    if(id==='analysis_analyst_consensus')return generic(node,core.ratings);
    if(id==='analysis_rating_history')return generic(node,core.ratings);
    if(id==='analysis_recommendation_summary')return generic(node,core.recommendations);
    if(id==='analysis_technical_averages')return generic(node,core.technical);
    if(id==='analysis_risk_assessment')return generic(node,core.risk);
    if(id==='analysis_futures')return generic(node,core.futures);
    if(id==='analysis_market_snapshot')return generic(node,core.snapshot);
    if(id==='actions_dividends')return action(node,core,'dividend');
    if(id==='actions_bonus_issues')return action(node,core,'bonus');
    if(id==='actions_rights_issues')return action(node,core,'rights');
    if(id==='actions_stock_splits')return action(node,core,'splits');
    if(id==='actions_annual_general_meetings')return action(node,core,'annualGeneralMeeting');
    if(id==='actions_board_meetings')return action(node,core,'boardMeetings');
    if(id==='actions_other')return generic(node,core.actions);
    if(id==='news_company_coverage'){if(!(core.news||[]).length){state(node,'No recent company coverage is available.');return;}(core.news||[]).slice(0,8).forEach(function(story){var item=el('div','dashboard-story'),a=el('a','',story.headline||'Company news');if(story.url){a.href=story.url;a.target='_blank';a.rel='noopener noreferrer';}item.append(a);if(story.summary)item.append(el('p','',story.summary));node.append(item);});return;}
    state(node);
  }
  function historyCard(meta,node,symbol,series){api(symbol,'financials',{series:series}).then(function(data){generic(node,data);}).catch(function(e){state(node,e.message);});}
  function priceHistory(meta,node,symbol){api(symbol,'history',{period:'1yr'}).then(function(data){var dataset=(data.datasets||[])[0],rows=dataset&&dataset.values||[];var values=rows.map(function(r){return num(r[1]);}).filter(function(v){return v!==null;});if(values.length<2){state(node);return;}var lo=Math.min.apply(Math,values),hi=Math.max.apply(Math,values),points=values.map(function(v,i){return (i*100/(values.length-1)).toFixed(1)+','+(95-(v-lo)*85/((hi-lo)||1)).toFixed(1);}).join(' ');var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 100 100');svg.setAttribute('class','dashboard-sparkline');var line=document.createElementNS(svg.namespaceURI,'polyline');line.setAttribute('points',points);line.setAttribute('fill','none');line.setAttribute('stroke','currentColor');line.setAttribute('stroke-width','2');line.setAttribute('vector-effect','non-scaling-stroke');svg.append(line);node.append(svg);}).catch(function(e){state(node,e.message);});}
  function aiCard(meta,node,symbol){ai(symbol).then(function(data){var map={ai_company_summary:data.summary,ai_encouraging_signals:data.encouraging,ai_attention_signals:data.attention,ai_recent_changes:data.changes,ai_potential_catalysts:data.catalysts,ai_key_risks:data.risks,ai_watch_next:data.watch_next,ai_sources_freshness:data.sources};var value=map[meta.id];if(Array.isArray(value)){value.forEach(function(item){var box=el('div','dashboard-story');if(item.tone)box.append(el('span','dashboard-ai-tone',item.tone));box.append(el('p','dashboard-ai-text',item.text||item.label||item.heading||JSON.stringify(item)));node.append(box);});if(!value.length)state(node);return;}if(value&&typeof value==='object'){if(value.tone)node.append(el('span','dashboard-ai-tone',value.tone));node.append(el('p','dashboard-ai-text',value.text||value.heading||'No reliable summary is available.'));return;}generic(node,value);}).catch(function(e){state(node,e.message);});}
  function renderCard(meta,node,core,symbol){
    var id=meta.id;if(id==='ai_watchlist_briefing'){state(node,'Shown once above your stock list.');return;}
    if(id.indexOf('ai_')===0){aiCard(meta,node,symbol);return;}
    if(id==='overview_price_history'){priceHistory(meta,node,symbol);return;}
    var series={financial_quarterly_results:'quarter_results',financial_annual_results:'yoy_results',financial_balance_sheet_history:'balancesheet',financial_cash_flow_history:'cashflow',financial_ratios_history:'ratios',ownership_quarterly_history:'shareholding_pattern_quarterly',ownership_annual_history:'shareholding_pattern_yearly'}[id];
    if(series){historyCard(meta,node,symbol,series);return;}
    if(id==='analysis_price_target_summary'||id==='analysis_price_target_history'){api(symbol,'targets').then(function(data){generic(node,id.endsWith('summary')?data.priceTarget:data);}).catch(function(e){state(node,e.message);});return;}
    if(id==='analysis_eps_forecasts'){api(symbol,'forecasts').then(function(data){generic(node,data.periods);}).catch(function(e){state(node,e.message);});return;}
    renderCore(meta,node,core);
  }
  function setup(section) {
    var root=section&&section.querySelector('[data-indian-dashboard]');if(!root||root.dataset.ready)return;root.dataset.ready='true';var symbol=root.dataset.symbol;
    var container=document.getElementById('digest-sections'),selected=JSON.parse(container&&container.dataset.dashboardCards||'[]');
    Promise.all([catalogPromise,api(symbol,'core')]).then(function(values){var catalog=values[0],core=values[1],categories=catalog.categories.map(function(category){return {category:category,cards:category.cards.filter(function(card){return selected.indexOf(card.id)>=0&&card.id!=='ai_watchlist_briefing';})};}).filter(function(item){return item.cards.length;});
      root.replaceChildren();if(!categories.length){state(root,'No company cards selected. Customize your dashboard to add some.');return;}
      var tabs=el('div','dashboard-category-tabs');tabs.setAttribute('role','tablist');var panels=el('div');
      function activate(index){Array.from(tabs.children).forEach(function(tab,i){tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;});Array.from(panels.children).forEach(function(panel,i){panel.hidden=i!==index;if(i===index&&!panel.dataset.loaded){panel.dataset.loaded='true';var grid=el('div','dashboard-card-grid');categories[i].cards.forEach(function(meta){var node=card(meta,['overview_price_history','overview_peer_comparison','news_company_coverage','financial_provider_metrics','financial_additional_data'].indexOf(meta.id)>=0);grid.append(node);renderCard(meta,node,core,symbol);});panel.append(grid);}});}
      categories.forEach(function(item,index){var tab=el('button','dashboard-category-tab',item.category.title);tab.type='button';tab.setAttribute('role','tab');tab.onclick=function(){activate(index);};tab.onkeydown=function(event){var next=event.key==='ArrowRight'?(index+1)%categories.length:event.key==='ArrowLeft'?(index+categories.length-1)%categories.length:-1;if(next>=0){event.preventDefault();activate(next);tabs.children[next].focus();}};tabs.append(tab);var panel=el('section','dashboard-category-panel');panel.setAttribute('role','tabpanel');panels.append(panel);});root.append(tabs,panels);activate(0);
    }).catch(function(error){root.replaceChildren();state(root,error.message||'Could not load your selected cards.');});
  }
  window.setupIndianDashboard=setup;
  document.querySelectorAll('.ticker-section').forEach(setup);
})();
