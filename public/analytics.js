(function () {
  'use strict';

  var SCHEMA_VERSION = 1;
  var queue = [];
  var ready = false;
  var disabled = false;
  var readyCallbacks = [];
  var originalFetch = window.fetch && window.fetch.bind(window);
  var observedSections = new WeakSet();
  var seenSections = new Set();

  function pageType() {
    var path = location.pathname.replace(/\/+$/, '') || '/';
    if (path === '/') return 'home';
    if (path === '/digest') return 'digest';
    if (path === '/onboarding') return 'onboarding';
    if (path === '/welcome') return 'welcome';
    if (path.indexOf('/ai-overview/') === 0) return 'ai_overview';
    if (path.indexOf('/stocks/') === 0) return 'stock_details';
    return 'other';
  }

  function symbol() {
    var value = document.body && document.body.dataset ? document.body.dataset.symbol : '';
    return /^[A-Z]{2}:[A-Z0-9&-]{1,20}$/.test(value || '') ? value : undefined;
  }

  function clean(value, max) {
    if (value === undefined || value === null) return undefined;
    return String(value).replace(/[\r\n\t]+/g, ' ').trim().slice(0, max || 120);
  }

  function safeErrorText(value, max) {
    return clean(value, max)
      .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[redacted-email]')
      .replace(/([?&](?:t|token|credential|email|prompt)=)[^\s&#]+/gi, '$1[redacted]')
      .replace(/\b(?:eyJ|phc_)[A-Za-z0-9._-]{20,}\b/g, '[redacted-token]');
  }

  function baseProperties(properties) {
    return Object.assign({
      schema_version: SCHEMA_VERSION,
      page_type: pageType(),
      page_path: location.pathname,
      symbol: symbol(),
      viewport: window.innerWidth < 600 ? 'mobile' : window.innerWidth < 1024 ? 'tablet' : 'desktop'
    }, properties || {});
  }

  function send(event, properties) {
    if (!event || disabled) return;
    var item = [clean(event, 80), baseProperties(properties)];
    if (!ready || !window.posthog || typeof window.posthog.capture !== 'function') {
      queue.push(item);
      if (queue.length > 100) queue.shift();
      return;
    }
    window.posthog.capture(item[0], item[1]);
  }

  function identify(id, properties) {
    var safeId = clean(id, 160);
    if (!safeId) return;
    var apply = function () {
      if (window.posthog && typeof window.posthog.identify === 'function') {
        window.posthog.identify(safeId, properties || {});
      }
    };
    if (ready) apply();
    else queue.push(['__identify__', {apply: apply}]);
  }

  window.tickrAnalytics = {capture: send, identify: identify, pageType: pageType,
    onReady: function (callback) {
      if (ready) callback(window.posthog);
      else if (disabled) callback(null);
      else readyCallbacks.push(callback);
    }
  };

  function disableAnalytics() {
    disabled = true;
    queue.length = 0;
    readyCallbacks.splice(0).forEach(function (callback) {
      try { callback(null); } catch (error) { /* Keep the page usable without analytics. */ }
    });
  }

  function flush() {
    ready = true;
    queue.splice(0).forEach(function (item) {
      if (item[0] === '__identify__') item[1].apply();
      else window.posthog.capture(item[0], item[1]);
    });
    readyCallbacks.splice(0).forEach(function (callback) {
      try { callback(window.posthog); } catch (error) { /* Analytics must not block the page. */ }
    });
  }

  function loadPostHog(config) {
    var script = document.createElement('script');
    var assetHost = config.host
      .replace('://us.i.posthog.com', '://us-assets.i.posthog.com')
      .replace('://eu.i.posthog.com', '://eu-assets.i.posthog.com');
    script.async = true;
    script.src = assetHost + '/static/array.js';
    script.onload = function () {
      if (!window.posthog || typeof window.posthog.init !== 'function') {
        disableAnalytics();
        return;
      }
      window.posthog.init(config.project_key, {
        api_host: config.host,
        autocapture: false,
        capture_pageview: false,
        capture_pageleave: true,
        person_profiles: 'identified_only',
        persistence: 'localStorage+cookie',
        session_recording: {
          maskAllInputs: true,
          maskTextSelector: 'input, textarea, [contenteditable=true], [data-private]'
        },
        loaded: flush
      });
    };
    script.onerror = disableAnalytics;
    document.head.appendChild(script);
  }

  function apiPath(input) {
    try {
      var raw = typeof input === 'string' ? input : input && input.url;
      var url = new URL(raw, location.origin);
      return url.origin === location.origin ? url.pathname : '';
    } catch (error) { return ''; }
  }

  function aiFeature(path) {
    if (path === '/api/stock-ai') return 'stock_ai_overview';
    if (path === '/api/stock-section-ai') return 'dashboard_card_explainer';
    if (path === '/api/digest-ai') return 'digest_ai_summary';
    return '';
  }

  if (originalFetch) {
    window.fetch = function (input, options) {
      var path = apiPath(input);
      var started = Date.now();
      return originalFetch(input, options).then(function (response) {
        if (path.indexOf('/api/') === 0 && path !== '/api/analytics/config') {
          var properties = {
            endpoint: path,
            method: clean(options && options.method || 'GET', 10).toUpperCase(),
            status: response.status,
            status_group: Math.floor(response.status / 100) + 'xx',
            success: response.ok,
            duration_ms: Date.now() - started
          };
          send('api_request_completed', properties);
          var feature = aiFeature(path);
          if (feature) send('ai_request_completed', Object.assign({feature: feature}, properties));
        }
        return response;
      }).catch(function (error) {
        if (path.indexOf('/api/') === 0 && path !== '/api/analytics/config') {
          var properties = {
            endpoint: path,
            method: clean(options && options.method || 'GET', 10).toUpperCase(),
            success: false,
            network_error: true,
            duration_ms: Date.now() - started,
            error_type: clean(error && error.name || 'Error', 80)
          };
          send('api_request_completed', properties);
          var feature = aiFeature(path);
          if (feature) send('ai_request_completed', Object.assign({feature: feature}, properties));
        }
        throw error;
      });
    };
  }

  function sectionId(element) {
    if (!element) return '';
    var value = clean(
      element.dataset.analyticsSection || element.dataset.ticker || element.dataset.panel ||
      element.getAttribute('aria-label') || element.id,
      100
    );
    return value ? value.toLowerCase().replace(/[^a-z0-9:_-]+/g, '_') : '';
  }

  function watchSections(root) {
    if (!window.IntersectionObserver) return;
    var selectors = 'main > section, main section[id], [role=tabpanel], [data-ticker], [data-analytics-section]';
    var elements = [];
    if (root && root.matches && root.matches(selectors)) elements.push(root);
    if (root && root.querySelectorAll) elements = elements.concat(Array.from(root.querySelectorAll(selectors)));
    elements.forEach(function (element) {
      if (observedSections.has(element)) return;
      var id = sectionId(element);
      if (!id) return;
      observedSections.add(element);
      sectionObserver.observe(element);
    });
  }

  var sectionObserver = window.IntersectionObserver ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting || entry.intersectionRatio < 0.35 || entry.target.hidden) return;
      var id = sectionId(entry.target);
      var ticker = clean(entry.target.dataset && entry.target.dataset.ticker, 30);
      var key = pageType() + ':' + id + ':' + (ticker || '');
      if (seenSections.has(key)) return;
      seenSections.add(key);
      send('section_viewed', {section: id, section_ticker: ticker});
    });
  }, {threshold: [0.35], rootMargin: '0px 0px -10% 0px'}) : null;

  function interaction(event) {
    var target = event.target && event.target.closest ? event.target.closest('a, button, summary, [data-card], [data-ai-card-id]') : null;
    if (!target) return;
    var properties = {};
    var action = '';

    if (target.dataset.analyticsAction) {
      action = target.dataset.analyticsAction;
      properties.feature = clean(target.dataset.analyticsFeature, 80);
      properties.category = clean(target.dataset.category, 80);
      properties.section = clean(target.dataset.analyticsSection, 80);
    } else if (target.matches('[data-tab]')) {
      action = 'stock_tab_selected'; properties.section = clean(target.dataset.tab, 80);
    } else if (target.matches('[data-view]')) {
      action = 'digest_view_selected'; properties.section = clean(target.dataset.view, 80);
      properties.section_ticker = clean(target.closest('[data-ticker]') && target.closest('[data-ticker]').dataset.ticker, 30);
    } else if (target.matches('[data-watchlist-ticker]')) {
      action = 'watchlist_stock_selected'; properties.section_ticker = clean(target.dataset.watchlistTicker, 30);
    } else if (target.matches('[data-stock-search]')) {
      action = 'stock_search_opened';
    } else if (target.matches('[data-card], [data-ai-card-id]')) {
      action = 'dashboard_card_interacted';
      properties.card = clean(target.dataset.aiCardId || target.dataset.card, 100);
      properties.section = clean(target.dataset.aiSection, 80);
      properties.section_ticker = clean(target.dataset.aiSymbol, 30);
    } else if (target.matches('[data-category]')) {
      action = 'dashboard_category_selected'; properties.category = clean(target.dataset.category, 80);
    } else if (target.matches('[data-remove]')) {
      action = 'watchlist_stock_removed';
    } else if (target.id === 'ticker-add') {
      action = 'watchlist_stock_added';
    } else if (target.id === 'step-one-next') {
      action = 'onboarding_watchlist_completed';
    } else if (target.id === 'save-dashboard') {
      action = 'dashboard_preferences_saved';
    } else if (target.id === 'nav-stock-details' || target.id === 'footer-stock-details') {
      action = 'stock_details_opened';
    } else if (target.id === 'theme-toggle' || target.classList.contains('theme-toggle')) {
      action = 'theme_changed';
    } else if (target.tagName === 'SUMMARY') {
      action = 'details_toggled'; properties.section = sectionId(target.parentElement);
    } else if (target.matches('.story-headline a')) {
      action = 'news_article_opened';
      try { properties.destination_host = new URL(target.href).hostname; } catch (error) {}
      properties.section_ticker = clean(target.closest('[data-ticker]') && target.closest('[data-ticker]').dataset.ticker, 30);
    }

    if (action) send('feature_used', Object.assign({
      feature: properties.feature || action,
      action: action
    }, properties));
  }

  function reportError(error, source) {
    var value = error instanceof Error ? error : new Error(clean(error, 300) || 'Unknown error');
    var properties = {
      source: source,
      error_type: clean(value.name || 'Error', 80),
      error_message: safeErrorText(value.message || 'Unknown error', 300)
    };
    send('app_error', properties);
    if (ready && window.posthog && typeof window.posthog.captureException === 'function') {
      var scrubbed = new Error(properties.error_message);
      scrubbed.name = properties.error_type;
      if (value.stack) scrubbed.stack = safeErrorText(value.stack, 4000);
      window.posthog.captureException(scrubbed, baseProperties(properties));
    }
  }

  window.addEventListener('error', function (event) { reportError(event.error || event.message, 'window_error'); });
  window.addEventListener('unhandledrejection', function (event) { reportError(event.reason, 'unhandled_rejection'); });

  function start() {
    send('$pageview', {referrer_host: (function () {
      try { return document.referrer ? new URL(document.referrer).hostname : ''; } catch (error) { return ''; }
    })()});
    document.addEventListener('click', interaction, true);
    if (sectionObserver) {
      watchSections(document);
      new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
          Array.from(mutation.addedNodes || []).forEach(watchSections);
        });
      }).observe(document.body, {childList: true, subtree: true});
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();

  if (!originalFetch) { disableAnalytics(); return; }
  originalFetch('/api/analytics/config', {credentials: 'same-origin'})
    .then(function (response) { return response.ok ? response.json() : null; })
    .then(function (config) {
      if (!config || !config.enabled || !config.project_key || !/^https:\/\//.test(config.host || '')) {
        disableAnalytics(); return;
      }
      loadPostHog(config);
    })
    .catch(disableAnalytics);
})();
