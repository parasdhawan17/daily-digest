(function () {
  var root = document.documentElement;
  var themeButton = document.getElementById('theme-toggle');
  function syncThemeButton() {
    themeButton.setAttribute('aria-label', 'Switch to ' + (root.dataset.theme === 'dark' ? 'light' : 'dark') + ' mode');
  }
  syncThemeButton();
  themeButton.addEventListener('click', function () {
    var theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    try { localStorage.setItem('daily-digest-theme', theme); } catch (error) {}
    syncThemeButton();
  });

  // Keep keyboard focus inside signup and return it to the initiating control.
  var modal = document.getElementById('subscribe-modal');
  var returnFocus;
  var background = document.querySelectorAll('body > header, body > main, body > footer, .skip-link');
  new MutationObserver(function () {
    if (!modal.hidden) returnFocus = document.activeElement;
    background.forEach(function (element) { element.inert = !modal.hidden; });
    if (modal.hidden && returnFocus) returnFocus.focus();
  }).observe(modal, { attributes: true, attributeFilter: ['hidden'] });
  modal.addEventListener('keydown', function (event) {
    if (event.key !== 'Tab') return;
    var controls = Array.from(modal.querySelectorAll('button, input, a[href], [tabindex="0"]')).filter(function (element) {
      return !element.disabled && element.getClientRects().length;
    });
    var first = controls[0];
    var last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();
