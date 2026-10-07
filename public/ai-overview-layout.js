// Resolve once per page so a late flag response cannot replace an open explanation.
(function () {
  'use strict';
  const flagKey = 'ai-overview-visual';
  let settled = false, finish;
  const layout = {flagKey, visual: true, ready: new Promise(resolve => { finish = resolve; })};
  window.tickrAIOverviewLayout = layout;
  function resolve(value) {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    layout.visual = value !== false;
    document.body.dataset.aiOverviewLayout = layout.visual ? 'visual' : 'legacy';
    finish(layout.visual);
  }
  const timer = setTimeout(() => resolve(undefined), 1500);
  function connect(posthog) {
    if (settled) return;
    if (!posthog || typeof posthog.onFeatureFlags !== 'function' || typeof posthog.getFeatureFlag !== 'function') {
      resolve(undefined); return;
    }
    try {
      posthog.onFeatureFlags((_flags, _variants, context) => {
        const errors = context?.errorsLoading;
        const failed = Array.isArray(errors) ? errors.length > 0 : Boolean(errors);
        try { resolve(failed ? undefined : posthog.getFeatureFlag(flagKey)); }
        catch (error) { resolve(undefined); }
      });
    } catch (error) { resolve(undefined); }
  }
  if (window.tickrAnalytics?.onReady) window.tickrAnalytics.onReady(connect);
  else connect(window.posthog);
})();
