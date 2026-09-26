(function () {
  'use strict';
  const icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>';
  document.querySelectorAll('[data-stock-search]').forEach(button => {
    button.classList.add('stock-search-button');
    const label = button.dataset.stockSearchLabel || 'Search a stock';
    button.innerHTML = icon;
    const text = document.createElement('span');
    text.textContent = label;
    button.append(text);
  });
  const dialog = document.createElement('dialog');
  dialog.className = 'stock-search-dialog';
  dialog.setAttribute('aria-labelledby', 'stock-search-title');
  dialog.innerHTML = '<div class="stock-search-heading"><h2 id="stock-search-title">Find your next perspective.</h2><button class="stock-search-close" aria-label="Close stock search" type="button">×</button></div><div class="stock-search-input-wrap"><input type="search" aria-label="Search Indian stocks by name or symbol" placeholder="Company or symbol, e.g. TCS" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="stock-search-results" autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false" maxlength="100"></div><p class="stock-search-status" role="status">Search companies listed in India.</p><ul id="stock-search-results" class="stock-search-results" role="listbox" aria-label="Indian stock search results"></ul>';
  document.body.append(dialog);
  const input = dialog.querySelector('input'), list = dialog.querySelector('ul'), status = dialog.querySelector('[role=status]');
  let timer, controller, generation = 0, items = [], active = -1, opener;
  function select(index) {
    active = index;
    Array.from(list.children).forEach((node, i) => node.setAttribute('aria-selected', String(i === index)));
    if (index >= 0) {
      input.setAttribute('aria-activedescendant', 'stock-result-' + index);
      list.children[index].scrollIntoView({block: 'nearest'});
    } else input.removeAttribute('aria-activedescendant');
  }
  function navigate(index) {
    if (items[index] && /^IN:[A-Z][A-Z0-9&-]{0,19}$/.test(items[index].symbol)) {
      window.location.assign('/stocks/' + encodeURIComponent(items[index].symbol).replace('%3A', ':'));
    }
  }
  function reset() {
    generation++; clearTimeout(timer); if (controller) controller.abort();
    items = []; list.replaceChildren(); select(-1); input.setAttribute('aria-expanded', 'false');
  }
  async function search(query, version) {
    controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch('/api/tickers/search?market=IN&q=' + encodeURIComponent(query), {signal: controller.signal});
      const data = await response.json();
      if (version !== generation || !dialog.open) return;
      if (!response.ok || !data.ok) throw new Error(data.error || 'Search is unavailable. Please try again.');
      items = (data.results || []).filter(x => x.market === 'IN');
      list.replaceChildren();
      items.forEach((item, index) => {
        const li = document.createElement('li'), body = document.createElement('span'), name = document.createElement('strong'), symbol = document.createElement('small'), badge = document.createElement('span');
        li.id = 'stock-result-' + index; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
        name.textContent = item.name; symbol.textContent = item.symbol.replace('IN:', ''); badge.textContent = 'India ↗';
        body.append(name, symbol); li.append(body, badge); list.append(li);
        li.addEventListener('click', () => navigate(index));
      });
      input.setAttribute('aria-expanded', String(items.length > 0));
      status.textContent = items.length ? items.length + (items.length === 1 ? ' company' : ' companies') + ' · Use ↑ ↓ and Enter to open' : 'No companies found. Try another name or symbol.';
    } catch (error) {
      if (error.name !== 'AbortError' && version === generation) status.textContent = error.message;
    } finally {
      clearTimeout(timeout);
    }
  }
  input.addEventListener('input', () => {
    reset(); const query = input.value.trim();
    status.textContent = query ? 'Searching Indian stocks…' : 'Search companies listed in India.';
    if (query) { const version = generation; timer = setTimeout(() => search(query, version), 300); }
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); if (items.length) select((active + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length);
    } else if (event.key === 'Enter') { event.preventDefault(); if (active >= 0) navigate(active); else if (items.length === 1) navigate(0); }
  });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
  dialog.addEventListener('close', () => { reset(); if (opener) opener.focus(); });
  function open(button, query) {
    opener = button || document.activeElement; reset(); input.value = query || '';
    status.textContent = 'Search companies listed in India.';
    dialog.showModal(); input.focus();
    if (query) { status.textContent = 'Searching Indian stocks…'; search(query, generation); }
  }
  document.addEventListener('click', event => { const button = event.target.closest('[data-stock-search]'); if (button) open(button); });
  async function openPeer(button, name) {
    const original = button.textContent;
    button.disabled = true; button.textContent = 'Finding company…';
    try {
      const response = await fetch('/api/tickers/search?market=IN&q=' + encodeURIComponent(name));
      const data = await response.json();
      const normalize = text => String(text).toLowerCase().replace(/\b(limited|ltd)\.?\b/g, '').replace(/[^a-z0-9]/g, '');
      const matches = (data.results || []).filter(x => x.market === 'IN' && normalize(x.name) === normalize(name));
      if (response.ok && data.ok && matches.length === 1 && /^IN:[A-Z][A-Z0-9&-]{0,19}$/.test(matches[0].symbol)) {
        window.location.assign('/stocks/' + encodeURIComponent(matches[0].symbol).replace('%3A', ':'));
      } else open(button, name);
    } catch (error) { open(button, name); }
    finally { button.disabled = false; button.textContent = original; }
  }
  window.tickrStockSearch = {open, openPeer};
})();
