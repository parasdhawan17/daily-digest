(function () {
  'use strict';
  const area = document.querySelector('.home-search-area');
  if (!area) return;

  const form = area.querySelector('form');
  const input = area.querySelector('input');
  const popover = area.querySelector('.home-search-popover');
  const list = area.querySelector('ul');
  const status = area.querySelector('[role="status"]');
  const preview = area.querySelector('.fx-typewriter');
  const validSymbol = /^IN:[A-Z][A-Z0-9&-]{0,19}$/;
  let timer;
  let controller;
  let requestId = 0;
  let items = [];
  let active = -1;

  if (preview) {
    const examples = ['TCS', 'RELIANCE', 'INFY', 'HDFCBANK'];
    let exampleIndex = 0;

    function showExample() {
      const example = examples[exampleIndex];
      preview.textContent = example;
      preview.style.setProperty('--characters', example.length);
      area.classList.add('has-search-preview');
    }

    preview.addEventListener('animationiteration', event => {
      if (event.animationName !== 'fx-type') return;
      exampleIndex = (exampleIndex + 1) % examples.length;
      showExample();
    });
    input.addEventListener('input', () => {
      area.classList.toggle('has-query', !!input.value);
    });
    area.classList.toggle('has-query', !!input.value);
    showExample();
  }

  function navigate(item) {
    if (item && validSymbol.test(item.symbol)) {
      window.location.assign('/stocks/' + encodeURIComponent(item.symbol).replace('%3A', ':'));
    }
  }

  function select(index) {
    active = index;
    Array.from(list.children).forEach((node, i) => {
      node.setAttribute('aria-selected', String(i === index));
    });
    if (index >= 0) {
      input.setAttribute('aria-activedescendant', list.children[index].id);
      list.children[index].scrollIntoView({block: 'nearest'});
    } else {
      input.removeAttribute('aria-activedescendant');
    }
  }

  function show(message) {
    status.textContent = message;
    popover.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function close() {
    popover.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    select(-1);
  }

  function reset() {
    requestId++;
    clearTimeout(timer);
    if (controller) controller.abort();
    controller = null;
    items = [];
    list.replaceChildren();
    close();
  }

  function render() {
    list.replaceChildren();
    items.forEach((item, index) => {
      const option = document.createElement('li');
      const identity = document.createElement('span');
      const name = document.createElement('strong');
      const symbol = document.createElement('small');
      const badge = document.createElement('span');
      option.id = 'home-stock-result-' + index;
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      name.textContent = item.name || item.symbol.slice(3);
      symbol.textContent = item.symbol.slice(3);
      badge.textContent = 'India ↗';
      identity.append(name, symbol);
      option.append(identity, badge);
      option.addEventListener('click', () => navigate(item));
      list.append(option);
    });
    select(-1);
  }

  async function search(query, id, openExactMatch) {
    const current = new AbortController();
    controller = current;
    const timeout = setTimeout(() => current.abort(), 10000);
    try {
      const response = await fetch('/api/tickers/search?market=IN&q=' + encodeURIComponent(query), {signal: current.signal});
      const data = await response.json();
      if (id !== requestId || input.value.trim() !== query) return;
      if (!response.ok || !data.ok) throw new Error(data.error || 'Search is unavailable. Please try again.');
      items = (data.results || []).filter(item => item.market === 'IN' && validSymbol.test(item.symbol));
      render();
      if (openExactMatch && items.length) {
        const exact = items.find(item => item.symbol.slice(3) === query.toUpperCase());
        if (exact || items.length === 1) {
          navigate(exact || items[0]);
          return;
        }
      }
      show(items.length
        ? items.length + (items.length === 1 ? ' company found' : ' companies found') + ' · Use ↑ ↓ and Enter to open'
        : 'No companies found. Try another name or ticker.');
      if (openExactMatch && items.length) select(0);
    } catch (error) {
      if (error.name !== 'AbortError' && id === requestId) {
        show(error.message || 'Search is unavailable. Please try again.');
      }
    } finally {
      clearTimeout(timeout);
      if (controller === current) controller = null;
    }
  }

  input.addEventListener('input', () => {
    reset();
    const query = input.value.trim();
    if (!query) return;
    show('Searching Indian stocks…');
    const id = requestId;
    timer = setTimeout(() => search(query, id, false), 250);
  });

  input.addEventListener('focus', () => {
    if (input.value.trim() && items.length) {
      popover.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }
  });

  input.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!items.length) return;
      event.preventDefault();
      popover.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      select((active + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length);
    } else if (event.key === 'Escape') {
      reset();
    }
  });

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (active >= 0) return navigate(items[active]);
    if (items.length) {
      const exact = items.find(item => item.symbol.slice(3) === input.value.trim().toUpperCase());
      return navigate(exact || items[0]);
    }
    const query = input.value.trim();
    if (!query) {
      input.focus();
      return;
    }
    reset();
    show('Searching Indian stocks…');
    search(query, requestId, true);
  });

  document.addEventListener('pointerdown', event => {
    if (!area.contains(event.target)) reset();
  });

  document.querySelectorAll('a[href="#home-stock-query"]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      input.focus();
    });
  });
})();
