/* Static landing-page preview flag. Subscriber rollout is configured server-side. */
(function () {
  var design = new URLSearchParams(window.location.search).get('design');
  var legacy = window.location.pathname.indexOf('/legacy/') === 0;
  if ((design === 'legacy' && !legacy) || (design === 'modern' && legacy)) {
    var target = new URL(window.location.href);
    target.pathname = design === 'legacy' ? '/legacy/index.html' : '/';
    window.location.replace(target.href);
  }
})();
