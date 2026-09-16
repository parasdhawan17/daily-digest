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
  var svgNS='http://www.w3.org/2000/svg';
  function svgEl(tag,attrs,content){var n=document.createElementNS(svgNS,tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content!==undefined)n.textContent=content;return n;}
  function chartDate(value){var d=new Date(value);return Number.isNaN(+d)?String(value):d.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});}
  function renderPriceChart(target,datasets){
    var series=(datasets||[]).filter(function(s){return Array.isArray(s.values);}).map(function(s){return {metric:s.metric,label:s.label||s.metric,values:s.values.filter(function(v){return Array.isArray(v)&&num(v[1])!==null&&Number.isFinite(Date.parse(v[0]));}).map(function(v){return [v[0],num(v[1])];}).sort(function(a,b){return Date.parse(a[0])-Date.parse(b[0]);})};}).filter(function(s){return s.values.length;});
    var price=series.find(function(s){return s.metric==='Price';})||series.find(function(s){return s.metric!=='Volume';});if(!price||price.values.length<2){state(target,'No history is available for this range.');return;}
    var rising=price.values[price.values.length-1][1]>=price.values[0][1],color=rising?'var(--pill-up-fg)':'var(--pill-down-fg)',W=720,H=245,left=58,right=12,top=18,bottom=171,plotW=W-left-right;
    var lines=series.filter(function(s){return s.metric!=='Volume';}),all=[];lines.forEach(function(s){s.values.forEach(function(v){all.push(v[1]);});});var low=Math.min.apply(Math,all),high=Math.max.apply(Math,all),pad=(high-low)*.08||Math.abs(high)*.05||1;low-=pad;high+=pad;
    var dates=[];series.forEach(function(s){s.values.forEach(function(v){dates.push(Date.parse(v[0]));});});var start=Math.min.apply(Math,dates),end=Math.max.apply(Math,dates),x=function(v){return left+(Date.parse(v)-start)/(end-start||1)*plotW;},y=function(v){return bottom-(v-low)/(high-low)*(bottom-top);};
    var svg=svgEl('svg',{viewBox:'0 0 '+W+' '+H,class:'stock-chart',tabindex:'0',role:'img','aria-label':'Price history. Use left and right arrows to explore values.'});svg.append(svgEl('title',{},'Price history'));
    for(var i=0;i<5;i++){var value=low+(high-low)*i/4,yy=y(value);svg.append(svgEl('line',{x1:left,y1:yy,x2:W-right,y2:yy,class:'grid-line'}),svgEl('text',{x:left-8,y:yy+3,'text-anchor':'end'},new Intl.NumberFormat('en-IN',{notation:'compact',maximumFractionDigits:1}).format(value)));}
    var volume=series.find(function(s){return s.metric==='Volume';});if(volume){var max=Math.max.apply(Math,volume.values.map(function(v){return v[1];}).concat([1]));volume.values.forEach(function(v){svg.append(svgEl('rect',{x:x(v[0]),y:215-v[1]/max*24,width:Math.max(.7,Math.min(6,plotW/volume.values.length*.7)),height:v[1]/max*24,class:'volume-bar'}));});}
    lines.forEach(function(s,index){svg.append(svgEl('path',{d:s.values.map(function(v,j){return (j?'L':'M')+x(v[0]).toFixed(2)+','+y(v[1]).toFixed(2);}).join(' '),fill:'none',stroke:s===price?color:'#6f8aff','stroke-width':s===price?2.5:1.3,'stroke-dasharray':s===price?'':'5 4'}));});[0,.5,1].forEach(function(t){svg.append(svgEl('text',{x:left+plotW*t,y:H-7,'text-anchor':t===0?'start':t===1?'end':'middle'},chartDate(new Date(start+(end-start)*t).toISOString())));});
    var cursor=svgEl('line',{x1:0,y1:top,x2:0,y2:217,stroke:'var(--text-muted)','stroke-dasharray':'3 3',visibility:'hidden'}),dot=svgEl('circle',{r:4,fill:color,visibility:'hidden'});svg.append(cursor,dot);var readout=el('p','stock-chart-readout'),active=price.values.length-1;
    function inspect(index){active=Math.max(0,Math.min(price.values.length-1,index));var point=price.values[active];cursor.setAttribute('x1',x(point[0]));cursor.setAttribute('x2',x(point[0]));cursor.setAttribute('visibility','visible');dot.setAttribute('cx',x(point[0]));dot.setAttribute('cy',y(point[1]));dot.setAttribute('visibility','visible');readout.textContent=chartDate(point[0])+' · '+price.label+' '+money(point[1]);}
    svg.addEventListener('pointermove',function(event){var rect=svg.getBoundingClientRect(),relative=(event.clientX-rect.left)/rect.width*W,best=0;price.values.forEach(function(v,i){if(Math.abs(x(v[0])-relative)<Math.abs(x(price.values[best][0])-relative))best=i;});inspect(best);});svg.addEventListener('keydown',function(event){if(['ArrowLeft','ArrowRight','Home','End'].indexOf(event.key)>=0){event.preventDefault();inspect(event.key==='Home'?0:event.key==='End'?price.values.length-1:active+(event.key==='ArrowLeft'?-1:1));}});
    var legend=el('div','stock-chart-legend');series.forEach(function(s){var item=el('span','',s.label);item.style.setProperty('--series-color',s.metric==='Volume'?'var(--link)':s===price?color:'#6f8aff');legend.append(item);});var change=(price.values[price.values.length-1][1]/price.values[0][1]-1)*100,indicator=el('span','stock-indicator '+(change>=0?'positive':'negative'),pct(change)+' over selected range');legend.append(indicator);target.append(readout,svg,legend);inspect(active);
  }
  function priceHistory(meta,node,symbol){var controls=el('div','stock-controls'),target=el('div');[['1m','1M'],['6m','6M'],['1yr','1Y'],['3yr','3Y'],['5yr','5Y'],['10yr','10Y'],['max','Max']].forEach(function(pair){var button=el('button','',pair[1]);button.type='button';button.setAttribute('aria-pressed',String(pair[0]==='1yr'));button.onclick=function(){Array.from(controls.children).forEach(function(b){b.setAttribute('aria-pressed',String(b===button));});target.replaceChildren(el('p','dashboard-card-state','Loading history…'));api(symbol,'history',{period:pair[0]}).then(function(data){target.replaceChildren();renderPriceChart(target,data.datasets);}).catch(function(e){target.replaceChildren();state(target,e.message);});};controls.append(button);});node.append(controls,target);controls.querySelector('[aria-pressed=true]').click();}
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
